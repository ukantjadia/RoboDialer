import asyncio
import pprint
import time
from typing import AsyncGenerator, Dict, Any
from urllib.parse import quote_plus
from playwright.async_api import Page, BrowserContext, Locator, TimeoutError
import sys
import os
import logging

# Ensure the config can be found when running this file directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from config.browser_config import PlaywrightManager

# --- Configuration ---
CONCURRENT_WORKERS = 3 # Number of parallel profile page scrapers
TIMEOUT = 35_000
logger = logging.getLogger("Hotfrog Canada")

async def _extract_profile_details(page: Page) -> Dict[str, str]:
    """Extracts details from a single company profile page."""
    details = {"Company": "NA", "Industry": "NA", "Phone": "NA", "Website": "NA", "Address": "NA"}
    try:
        company_loc = page.locator("strong.lead")
        if await company_loc.is_visible(timeout=5000):
            details["Company"] = (await company_loc.inner_text()).strip()

        p_loc = page.locator("p:has(strong.lead)")
        if await p_loc.is_visible():
            full_text = await p_loc.inner_text()
            if "Category:" in full_text:
                parts = full_text.split("Category:")
                if len(parts) > 1:
                    details["Industry"] = parts[1].strip()

        details_container = page.locator("section.hf-bdp-top")
        if await details_container.is_visible():
            phone_p_loc = details_container.locator("p:has-text('Phone:')").first
            if await phone_p_loc.is_visible():
                phone_text = await phone_p_loc.inner_text()
                details["Phone"] = phone_text.replace("Phone:", "").strip()

            website_loc = details_container.locator("a[data-click='website']")
            if await website_loc.is_visible():
                details["Website"] = await website_loc.get_attribute("href")

        street_loc = page.locator("span[data-address-line1]")
        street = await _get_locator_text(street_loc)

        street2_loc = page.locator("span[data-address-line2]")
        street2 = await _get_locator_text(street2_loc)
        if street2 :
            street += ", " + street2
        
        district_loc = page.locator("span[data-address-district]")
        
        town_loc = page.locator("span[data-address-town]")

        city = (await _get_locator_text(district_loc)) or (await _get_locator_text(town_loc))

        county_loc = page.locator("span[data-address-county]")
        province_loc = page.locator("span[data-address-province]")

        province = (await _get_locator_text(county_loc)) or (await _get_locator_text(province_loc))

        details["Address"] = ", ".join([street, city, province])


    except Exception as e:
        logger.error(f"Error extracting profile details: {e}")
    return details


async def _profile_page_worker(
    worker_id: int, 
    context: BrowserContext, 
    job_queue: asyncio.Queue, 
    results_queue: asyncio.Queue, 
    stop_flag: Dict[str, bool]
):
    """(Consumer) Takes jobs from the queue, scrapes profile pages, and puts final data on the results queue."""
    logger.info(f"[Worker-{worker_id}] Started.")
    page = await context.new_page()
    while not stop_flag.get("stop"):
        try:
            job = await asyncio.wait_for(job_queue.get(), timeout=1.0)
            if job is None: break
            
            profile_url = job.get("profile_url")
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=TIMEOUT)
            profile_details = await _extract_profile_details(page)

            final_record = {
                "Company": profile_details.get("Company"), 
                "Industry": profile_details.get("Industry"),
                "Address": profile_details.get("Address"), 
                "Business_phone": profile_details.get("Phone"),
                "Website": profile_details.get("Website"), "BBB_rating": "NA"
            }
            if final_record["Company"] != "NA":
                await results_queue.put(final_record)
            job_queue.task_done()
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger.error(f"[Worker-{worker_id}] Error processing job: {e}")
            if 'job' in locals(): job_queue.task_done()
    await page.close()
    logger.info(f"[Worker-{worker_id}] Shutting down.")


async def _search_page_producer(
    context: BrowserContext, 
    job_queue: asyncio.Queue,
    industry: str, 
    location: str, 
    max_pages: int,
    stop_flag: Dict[str, bool]
):
    """(Producer) Scrapes a SINGLE search result page and puts jobs into the queue."""
    if stop_flag.get("stop"): return

    loc_formatted = location.lower().replace(", ", "-").replace(" ", "-")
    ind_formatted = industry.lower().replace(" ", "-")
    
    page = await context.new_page()
    try:
        for page_num in range(1, max_pages + 1) :
            url = f"https://www.hotfrog.ca/search/{loc_formatted}/{ind_formatted}/{page_num}"
            logger.info(f"[Producer] Scraping search page: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)

            if not await page.locator("div.hf-serps-main").is_visible(timeout=7000):
                logger.warning(f"[Producer-{page_num}] No results found. Stopping this producer.")
                return

            result_cards = await page.locator("div.hf-box").all()
            for card in result_cards:
                link_loc = card.locator("h3.h6 > a")
                href = await link_loc.get_attribute("href") if await link_loc.is_visible() else None

                if href:
                    await job_queue.put({
                        "profile_url": "https://www.hotfrog.ca" + href,
                    })

            logger.info(f"Page {page_num} scraped successfully.")
    except Exception as e:
        logger.error(f"[Page-{page_num}] An error occurred: {e}")
    finally:
        await page.close()


# --- Main Function ---
async def scrape_hotfrog_ca(industry: str, location: str, page:Page = None, max_pages: int = 5, stop_flag: Dict[str, bool] = None) -> AsyncGenerator[Dict[str, Any], None]:
    if stop_flag is None: stop_flag = {"stop": False}

    context = None
    internal_browser = False
    if not page:
        manager = PlaywrightManager(headless=True)
        await manager.start_browser(stealth_on=True)
        context = manager.context
        internal_browser = True
    else:
        context = page.context

    job_queue = asyncio.Queue(maxsize=200)
    results_queue = asyncio.Queue()
    
    try:
        producer_task = asyncio.create_task(
            _search_page_producer(context, job_queue, industry, location, max_pages, stop_flag)
        ) 
        
        worker_tasks = [
            asyncio.create_task(
                _profile_page_worker(i + 1, context, job_queue, results_queue, stop_flag)
            ) for i in range(CONCURRENT_WORKERS)
        ]


        while True:
            try:
                result = await asyncio.wait_for(results_queue.get(), timeout=1.0)
                yield result
                results_queue.task_done()
            except asyncio.TimeoutError:
                if producer_task.done() and job_queue.empty() and results_queue.empty():
                    logger.info("All producers and queues are finished. Tearing down.")
                    break
        
        # Graceful shutdown
        await producer_task
        await job_queue.join()

        for _ in worker_tasks:
            await job_queue.put(None)
        
        await asyncio.gather(*worker_tasks)

    except Exception as e:
        logger.error(f"[Orchestrator] An error occurred: {e}")
    finally:
        logger.info("[Orchestrator] Shutting down.")
        if internal_browser:
            await manager.stop_browser()

async def _get_locator_text(locator: Locator):
    if await locator.is_visible():
        return await locator.inner_text()
    return ""

async def main_test():
    print("--- Running Hotfrog.ca Scraper in Test Mode ---")
    industry_to_test = "IT Consulting"
    location_to_test = "Toronto, ON"
    pages_to_scrape = 5
    
    start_time = time.time()
    scraped_results = []
    try:
        async for record in scrape_hotfrog_ca(
            industry=industry_to_test, 
            location=location_to_test, 
            max_pages=pages_to_scrape
        ):
            if record:
                print(f"  [+] Yielded: {record.get('Company')}")
                scraped_results.append(record)
    finally:
        end_time = time.time()
        print("\n--- Test Summary ---")
        print(f"Scraped a total of {len(scraped_results)} business listings.")
        print(f"Total execution time: {end_time - start_time:.2f} seconds")
        if scraped_results:
            print("\n--- Sample Results ---")
            pprint.pprint(scraped_results[-5:])


if __name__ == "__main__":
    asyncio.run(main_test())