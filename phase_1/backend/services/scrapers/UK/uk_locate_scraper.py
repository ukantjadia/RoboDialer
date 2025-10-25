import pprint
import sys
import os
import argparse
import time
import urllib.parse
import re
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import Page, BrowserContext
from typing import Dict
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from backend.config.browser_config import PlaywrightManager
import logging
from backend.config.logger_config import setup_logger

setup_logger()
logger = logging.getLogger("UK Locate Scraper")

# --- Configuration ---
CONCURRENT_WORKERS = 3
TIMEOUT = 30_000

async def scrape_uk_locate_businesses(
    industry: str,
    location: str,
    page: Page = None,
    max_pages: int = 5,
    stop_flag: Dict[str, bool] = None
):
    """
    Scrape business listings from uk-locate.co.uk by industry and city.
    Yields each business as it is scraped.
    If page is not provided, a new browser tab will be created.
    """
    if stop_flag is None: stop_flag = {"stop": False}
    
    manager = None
    context = None
    internal_browser = False
    if page is None:
        manager = PlaywrightManager(headless=True)
        await manager.start_browser(stealth_on=True)
        context = manager.context
        internal_browser = True
    else:
        context = page.context

    job_queue = asyncio.Queue(maxsize=300)
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
                    break
        
        await producer_task
        await job_queue.join()
        for _ in worker_tasks:
            await job_queue.put(None)
        await asyncio.gather(*worker_tasks)

    except Exception as e:
        logger.error(f"[Orchestrator] A critical error occurred: {e}")
    finally:
        logger.info("[Orchestrator] Shutting down.")
        if internal_browser:
            await manager.stop_browser()


async def _profile_page_worker(
    worker_id: int,
    context: BrowserContext,
    job_queue: asyncio.Queue,
    results_queue: asyncio.Queue,
    stop_flag: Dict[str, bool]
):
    """Takes a job from the queue, scrapes the detail page, and puts the result on the results queue."""
    logger.info(f"[Worker-{worker_id}] Started.")
    page = await context.new_page()
    while not stop_flag.get("stop"):
        try:
            job = await asyncio.wait_for(job_queue.get(), timeout=1.0)
            if job is None: break

            detail_url = job.get("detail_url")
            city_name = job.get("city_name")
            state_full = job.get("state_full")

            business_info = await scrape_business_details(page, detail_url, city_name, state_full)
            if business_info:
                await results_queue.put(business_info)
            
            job_queue.task_done()
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            logger.error(f"[Worker-{worker_id}] Error processing job: {e}")
            if 'job' in locals() and job is not None:
                job_queue.task_done()
    await page.close()

async def _search_page_producer(
    context: BrowserContext,
    job_queue: asyncio.Queue,
    industry: str,
    location: str,
    max_pages: int,
    stop_flag: Dict[str, bool]
):
    """Finds all business detail URLs and puts them into the job queue."""
    logger.info("[Producer] Started.")
    page = await context.new_page()
    try:
        base_url = "https://uk-locate.co.uk/search/business.php"
        industry_encoded = urllib.parse.quote(industry.capitalize())
        location_parts = location.split(",")
        city_name = location_parts[0].strip()
        state_name = "NA"
        if len(location_parts) > 1:
            state_name = location_parts[1].strip()

        city_encoded = urllib.parse.quote(city_name)
        
        for page_num in range(1, max_pages + 1):
            if stop_flag.get("stop"): break
            
            url = f"{base_url}?q={industry_encoded}&w={city_encoded}&c=&p={page_num}"
            logger.info(f"[Producer] Scraping search page {page_num}: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)

            soup = BeautifulSoup(await page.content(), "html.parser")
            if "We did not find any results" in soup.get_text():
                logger.info("[Producer] No more results found. Stopping.")
                break

            business_links = soup.select("div.container > a:has(strong)")
            if not business_links:
                logger.info(f"[Producer] No business links on page {page_num}.")
                break
            
            for link in business_links:
                detail_url = "https://uk-locate.co.uk" + link.get("href", "")
                job = {
                    "detail_url": detail_url,
                    "city_name": city_name,
                    "state_full": state_name
                }
                await job_queue.put(job)

            if not soup.find("a", string="Next Page >>"):
                break
            

    except Exception as e:
        logger.error(f"[Producer] An error occurred: {e}", exc_info=True)
    finally:
        await page.close()
        logger.info("[Producer] Finished.")


def parse_uk_address(raw_address):
    """
    Parse UK address and format as <Street>, <City>
    """
    if not raw_address or raw_address == "NA":
        return "NA"
    
    # Clean up the address
    address = raw_address.strip()
    
    # Remove trailing periods
    address = address.rstrip('.')
    
    # Split by commas and clean each part
    parts = [part.strip() for part in address.split(",") if part.strip()]
    
    if not parts:
        return "NA"
    
    # Remove postcode from the end if present
    if parts and re.match(r'^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$', parts[-1].strip()):
        parts = parts[:-1]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_parts = []
    for part in parts:
        part_lower = part.lower()
        if part_lower not in seen:
            seen.add(part_lower)
            unique_parts.append(part)
    
    if not unique_parts:
        return "NA"
    
    # Common UK cities and regions
    uk_cities = {
        'london', 'greater london', 'birmingham', 'manchester', 'liverpool', 
        'bristol', 'sheffield', 'leeds', 'edinburgh', 'glasgow', 'cardiff',
        'belfast', 'newcastle', 'nottingham', 'coventry', 'leicester',
        'bradford', 'southampton', 'brighton', 'portsmouth', 'reading',
        'northampton', 'luton', 'wolverhampton', 'bolton', 'bournemouth',
        'norwich', 'swindon', 'swansea', 'southend', 'middlesbrough',
        'wiltshire', 'surrey', 'kent', 'essex', 'hertfordshire', 'buckinghamshire'
    }
    
    # Find the city (usually the last recognizable city name)
    city = None
    street_parts = []
    
    # Work backwards to find the city
    for i in range(len(unique_parts) - 1, -1, -1):
        part_lower = unique_parts[i].lower()
        if part_lower in uk_cities:
            city = unique_parts[i]
            street_parts = unique_parts[:i]
            break
    
    # If no city found, assume the last part is the city
    if not city and unique_parts:
        city = unique_parts[-1]
        street_parts = unique_parts[:-1]
    
    # Clean street parts
    cleaned_street_parts = []
    for part in street_parts:
        # Remove "United Kingdom" references
        cleaned_part = re.sub(r'\bUnited Kingdom\b', '', part, flags=re.IGNORECASE)
        cleaned_part = re.sub(r'\bUK\b', '', cleaned_part, flags=re.IGNORECASE)
        cleaned_part = cleaned_part.strip()
        
        if cleaned_part:
            cleaned_street_parts.append(cleaned_part)
    
    # Build the final address
    if cleaned_street_parts and city:
        street = " ".join(cleaned_street_parts)
        # Remove extra spaces and punctuation
        street = re.sub(r'\s+', ' ', street).strip()
        street = re.sub(r'[,\s]+$', '', street)  # Remove trailing commas/spaces
        return f"{street}, {city}"
    elif city:
        return city
    else:
        return " ".join(unique_parts)

async def scrape_business_details(page, detail_url, city_name, state_full):
    """
    Scrape business details from individual business page.
    """
    try:
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        
        soup = BeautifulSoup(await page.content(), "html.parser")
        
        # Extract name (first h1)
        name = "NA"
        h1_tag = soup.find("h1")
        if h1_tag:
            name = h1_tag.get_text(strip=True)
        
        # Extract industry (first h2, remove "in [city]" part)
        industry = "NA"
        h2_tag = soup.find("h2")
        if h2_tag:
            industry_text = h2_tag.get_text(strip=True)
            # Remove "in [city]" part
            industry = re.sub(r'\s+in\s+[^,]+$', '', industry_text, flags=re.IGNORECASE)
        
        # Extract address (p tag under h3 "Address")
        raw_address = "NA"
        address_h3 = soup.find("h3", string=re.compile(r"Address", re.IGNORECASE))
        if address_h3:
            # Find the next p tag after the Address h3
            next_p = address_h3.find_next_sibling("p")
            if next_p:
                raw_address = next_p.get_text(strip=True)
                # Clean up address formatting
                raw_address = re.sub(r'\s+', ' ', raw_address)
        
        # Parse and format the address
        address = parse_uk_address(raw_address)
        
        # Parse address into street and city
        if address and address != "NA":
            address_parts = address.split(", ")
            if len(address_parts) >= 2:
                street = address_parts[0]
                city = address_parts[1]
            else:
                street = address
                city = "Unknown City"
        else:
            street = "NA"
            city = "Unknown City"
        
        # Create combined address like other scrapers
        if street != "NA":
            full_address = f"{street}, {city}, {state_full}"
        else:
            full_address = f"{city}, {state_full}"
        
        # Extract phone (strong tag under h3 "Phone Number")
        phone = "NA"
        phone_h3 = soup.find("h3", string=re.compile(r"Phone Number", re.IGNORECASE))
        if phone_h3:
            # Find the next p tag after the Phone Number h3
            next_p = phone_h3.find_next_sibling("p")
            if next_p:
                strong_tag = next_p.find("strong")
                if strong_tag:
                    phone = strong_tag.get_text(strip=True)
        
        # Extract website (from strong tags with "Visit the ... website" text)
        website = "NA"
        strong_tags = soup.find_all("strong")
        for strong in strong_tags:
            strong_text = strong.get_text(strip=True)
            if "visit the" in strong_text.lower() and "website" in strong_text.lower():
                # Find the link within this strong tag
                link = strong.find("a")
                if link and link.get("href"):
                    website = link.get("href")
                    break
        
        return {
            "Company": name,
            "Industry": industry if industry != "NA" else "Unknown",
            "Address": full_address,
            "Business_phone": phone,
            "Website": website,
            "BBB_rating": "NA"
        }
        
    except Exception as e:
        logger.error(f"Error scraping business details from {detail_url}: {e}")
        return None

async def main():
    parser = argparse.ArgumentParser(description="Scrape business listings from UK-Locate by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'plumber'")
    parser.add_argument("city", help="City to search in, e.g. 'london'")
    parser.add_argument("--pages", type=int, default=3, help="Maximum number of pages to scrape")
    args = parser.parse_args()
    
    logger.info(f"Searching for {args.industry} businesses in {args.city}...")
    count = 0
    scraped_results = []
    start_time = time.time()
    async for biz in scrape_uk_locate_businesses(args.industry, args.city, max_pages=args.pages):
        count += 1
        logger.info(f"  [+] Yielded {count}: {biz['Company']}")
        scraped_results.append(biz)
    
    if scraped_results:
            print("\n--- Sample Results ---")
            pprint.pprint(scraped_results[:5])
    logger.info(f"\nFound {count} businesses total in {time.time() - start_time:.2f} seconds.")
if __name__ == "__main__":
    asyncio.run(main())
