import asyncio
import pprint
import time
from typing import AsyncGenerator, Dict, Any, List
from urllib.parse import quote_plus
from playwright.async_api import Page, BrowserContext, Locator
import sys
import os
import logging
import re

# --- Setup Paths and Logger ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from config.browser_config import PlaywrightManager
logger = logging.getLogger("B2BStars")

# --- Configuration ---
CONCURRENT_WORKERS = 3
TIMEOUT = 45_000
# B2BStars uses employee ranges for pagination
EMPLOYEE_RANGES = ["10-49", "50-99", "100-249"]
# There are other ranges "500-999", "5000+"

async def _extract_profile_details(page: Page) -> Dict[str, str]:
    """Extracts details from a single company profile page."""
    details = {"Company": "NA", "Industry": "NA", "Website": "NA", "Address": "NA"}
    
    cookie_button = page.locator("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowallSelection")
    if await cookie_button.is_visible(timeout=3000):
        logger.info("[Profile] 'Allow selection' button clicked.")
        await cookie_button.click()

    try:
        # Wait for a key element to ensure the page is loaded
        await page.wait_for_selector("h5.capitalize.css-15fiav2", timeout=5000)

        name_loc = page.locator("h5.capitalize.css-15fiav2")
        if await name_loc.is_visible():
            details["Company"] = (await name_loc.inner_text()).title()

        website_loc = page.locator("div[data-track='website'] > div")
        if await website_loc.is_visible():
            details["Website"] = await website_loc.inner_text()
        
        category_loc = page.locator("span.ant-tag").first
        if await category_loc.is_visible():
            details["Industry"] = await category_loc.inner_text()
            
        address_parts = await page.locator("span.capitalize.css-15fiav2").all()
        if len(address_parts) >= 2:
            street = await address_parts[0].inner_text()
            city = await address_parts[1].inner_text()
            details["Address"] = f"{street}, {city},"

    except Exception as e:
        logger.error(f"Error extracting profile details from {page.url}: {e}")
    return details

async def _profile_page_worker(
    worker_id: int, 
    context: BrowserContext, 
    job_queue: asyncio.Queue, 
    results_queue: asyncio.Queue, 
    stop_flag: Dict[str, bool]
):
    """(Consumer) Takes jobs, scrapes profile pages, and puts final data on the results queue."""
    logger.info(f"[Worker-{worker_id}] Started.")
    page = await context.new_page()
    
    while not stop_flag.get("stop"):
        try:
            job = await asyncio.wait_for(job_queue.get(), timeout=2.0)
            if job is None: break
            
            profile_url = job.get("profile_url")
            
            # Navigate to the final profile URL
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=TIMEOUT)
            
            # Scrape the details from the profile page
            profile_details = await _extract_profile_details(page)

            final_record = {
                "Company": profile_details.get("Company"), 
                "Industry": profile_details.get("Industry"),
                "Address": profile_details.get("Address"), 
                "Business_phone": "NA",
                "Website": profile_details.get("Website"), 
                "BBB_rating": "NA"
            }
            if final_record["Company"] != "NA":
                await results_queue.put(final_record)
            job_queue.task_done()
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger.error(f"[Worker-{worker_id}] Error processing job: {e}")
            if 'job' in locals(): job_queue.task_done()

    logger.info(f"[Worker-{worker_id}] Shutting down.")


async def _search_page_producer(
    context: BrowserContext,
    job_queue: asyncio.Queue,
    industry: str, 
    location: str, 
    stop_flag: Dict[str, bool]
):
    """
    (Producer) Iterates through employee filters, finds company names,
    constructs profile URLs, and puts them into the job queue.
    """
    if stop_flag.get("stop"): return
    logger.info("[Producer] Started.")
    page = await context.new_page()
    try:
        country_code = location.split(',')[-1].strip().upper()[:2]
        if country_code == "UK": country_code = "GB"
        city_name = location.split(',')[0].strip().upper()

        for employee_range in EMPLOYEE_RANGES:
            if stop_flag.get("stop"): break

            params = {
                "q": industry, 
                "countries": country_code,
                "employeesRange": employee_range, 
                "city": city_name
            }
            query_string = "&".join([f"{k}={quote_plus(v)}" for k, v in params.items()])
            url = f"https://www.b2bstars.com/en-us/company?{query_string}"
            
            logger.info(f"[Producer] Scraping search page for range {employee_range}: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)

            # Handle cookie dialog on the first visit
            try:
                cookie_button = page.locator("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowallSelection")
                await cookie_button.click(timeout=5000)
                logger.info("[Producer] Cookie consent dialog handled.")
                await page.wait_for_timeout(1000)
            except Exception:
                logger.info("[Producer] Cookie consent dialog not found or already handled.")

            if not await page.locator("div.ant-list-vertical").is_visible(timeout=10000):
                logger.warning(f"[Producer] No results found for range {employee_range}.")
                continue

            # Get all company cards from the search results
            company_names = await page.locator("h1[data-sentry-element='Title'][data-sentry-source-file='SearchCompaniesCard.tsx']").all()
            logger.info(f"[Producer] Found {len(company_names)} listings for range {employee_range}.")
            
            for name_loc in company_names:
                company_name = await name_loc.inner_text() if await name_loc.count() > 0 else None
                if company_name:
                    company_slug = _slugify(company_name)
                    profile_url = f"https://www.b2bstars.com/en-us/company/{company_slug}"
                    await job_queue.put({"profile_url": profile_url})

            await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"[Producer] An error occurred: {e}", exc_info=True)
    finally:
        await page.close()
        logger.info("[Producer] Finished finding jobs.")

# --- Main Orchestrator Function ---
async def scrape_b2bstars(industry: str, location: str, page: Page = None, stop_flag: Dict[str, bool] = None) -> AsyncGenerator[Dict[str, Any], None]:
    if stop_flag is None: stop_flag = {"stop": False}

    context = None
    manager = None
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
            _search_page_producer(context, job_queue, industry, location, stop_flag)
        ) 
        
        worker_tasks = [
            asyncio.create_task(
                _profile_page_worker(i + 1, context, job_queue, results_queue, stop_flag)
            ) for i in range(CONCURRENT_WORKERS)
        ]

        while True:
            try:
                result = await asyncio.wait_for(results_queue.get(), timeout=2.0)
                yield result
                results_queue.task_done()
            except asyncio.TimeoutError:
                if producer_task.done() and job_queue.empty() and results_queue.empty():
                    logger.info("All producers and queues are finished. Tearing down.")
                    break
        
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

def _slugify(text: str) -> str:
    """Converts a string into a URL-friendly slug."""
    if not text:
        return ""
    text = text.lower().replace('&', '')
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'[^a-z0-9-]', '', text)
    return text.strip('-')

# --- Standalone Test Function ---
async def main_test():
    logging.basicConfig(level=logging.INFO)
    print("--- Running B2BStars Scraper in Test Mode ---")
    industry_to_test = "Retail"
    location_to_test = "Paris, Ilye bla, FRA"
    
    start_time = time.time()
    scraped_results = []
    try:
        async for record in scrape_b2bstars(
            industry=industry_to_test, 
            location=location_to_test
        ):
            if record:
                print(f"   [+] Yielded: {record.get('Company')}")
                scraped_results.append(record)
    finally:
        end_time = time.time()
        print("\n--- Test Summary ---")
        print(f"Scraped a total of {len(scraped_results)} business listings.")
        print(f"Total execution time: {end_time - start_time:.2f} seconds")
        if scraped_results:
            print("\n--- Sample Results ---")
            pprint.pprint(scraped_results[:5])


if __name__ == "__main__":
    asyncio.run(main_test())