import asyncio
import pprint
import random
import time
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from playwright.async_api import Page, TimeoutError, ElementHandle
from typing import AsyncGenerator, Dict, Any
import sys
import os
import logging

# if run this file directly then need to add the backend/ path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from config.browser_config import PlaywrightManager

TIMEOUT = 30_000
logger = logging.getLogger("YellowPages Canada")

async def scrape_yellowpages_ca(industry: str, location: str, page: Page = None, max_pages: int = 5, stop_flag: Dict[str, bool] = None) -> AsyncGenerator[Dict[str, str], None]:
    if stop_flag is None:
        stop_flag = {"stop": False}

    manager = None
    # If no page object is provided, create and manage a browser instance internally.
    if page is None:
        manager = PlaywrightManager(headless=True)
        page = await manager.start_browser(stealth_on=True)

    try:
        for page_num in range(1, max_pages + 1):
            if stop_flag.get("stop"):
                logger.warning("Stop signal received, terminating scrape.")
                break

            term_encoded = quote_plus(industry)
            loc_encoded = quote_plus(location)
            url = f"https://www.yellowpages.ca/search/si/{page_num}/{term_encoded}/{loc_encoded}"
            logger.info(f"Scraping page {page_num}: {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
            except TimeoutError:
                logger.warning(f"Timeout error loading {url}")
                continue

            listings = await page.query_selector_all("div.listing__content")
            if not listings:
                logger.warning(f"No listings found on page {page_num}. Ending scrape for this source.")
                break

            for el in listings:
                if stop_flag.get("stop"):
                    break
                
                try:
                    company_name_el = await el.query_selector("a.listing__name--link")
                    company_name = await company_name_el.text_content() if company_name_el else "NA"

                    industry_text = industry.title() # Default to the search term
                    industry_el = await el.query_selector("div.listing__headings > a")
                    if industry_el:
                        scraped_industry = await industry_el.text_content()
                        if scraped_industry:
                            industry_text = scraped_industry.strip()

                    phone_el = await el.query_selector("li.mlr__item--phone a")
                    phone_number = await phone_el.get_attribute("data-phone") if phone_el else "NA"
                    
                    website_el = await el.query_selector("li.mlr__item--website a")
                    href_string = await website_el.get_attribute("href") if website_el else ""
                    website = None
                    if href_string:
                        parsed_href = urlparse(href_string)
                        # parsed_href.query will be: 'redirect=https%3A%2F%2Ftheupsstore.ca%2F'

                        # Parse the query string component into a dictionary.
                        query_params = parse_qs(parsed_href.query)
                        # query_params will be: {'redirect': ['https%3A%2F%2Ftheupsstore.ca%2F']}

                        # Safely get the value of the 'redirect' parameter.
                        encoded_url = query_params.get('redirect', [None])[0]
                        
                        final_url = unquote(encoded_url)
                        website = final_url
                        

                    street = await _get_element_text(el, "span[itemprop='streetAddress']")
                    city = await _get_element_text(el, "span[itemprop='addressLocality']")
                    province = await _get_element_text(el, "span[itemprop='addressRegion']")
                    
                    
                    full_address = ', '.join([street, city, province]) 

                    record = {
                        "Company": (company_name or "NA").strip(),
                        "Industry": industry_text,
                        "Address": full_address,
                        "Business_phone": (phone_number or "NA").strip(),
                        "Website": (website or "NA").strip(),
                        "BBB_rating": "NA"
                    }
                    
                    if record["Company"] != "NA":
                        yield record

                except Exception as e:
                    logger.error(f"Error processing a listing: {e}")
            
            
            await asyncio.sleep(2)
    finally:
        # If a browser manager was created internally, ensure the browser is closed.
        if manager:
            await manager.stop_browser()


async def main_test():

    print("--- 🇨🇦 Running YellowPages.ca Scraper in Test Mode ---")
    industry_to_test = "Printing"
    location_to_test = "Toronto, ON"
    pages_to_scrape = 1
    
    
    start_time = time.time()
    scraped_results = []

    print(f"\nSearching for '{industry_to_test}' in '{location_to_test}' for up to {pages_to_scrape} pages...")

    try:
        async for record in scrape_yellowpages_ca(
            industry=industry_to_test,
            location=location_to_test,
            max_pages=pages_to_scrape
        ):
            if record:
                scraped_results.append(record)

    except Exception as e:
        print(f"\n--- An error occurred during the test ---")
        print(e)

    finally:
        end_time = time.time()
        execution_time = end_time - start_time

        print("\n---Test Summary ---")
        print(f"Scraped a total of {len(scraped_results)} business listings.")
        print(f"Total execution time: {execution_time:.2f} seconds")

        if scraped_results:
            print("\n--- Sample Results ---")
            # random.shuffle(scraped_results)
            pprint.pprint(scraped_results[:3])

async def _get_element_text(element: ElementHandle, selector:str):
    element_selected = await element.query_selector(selector)
    if element_selected:
        return await element_selected.text_content()
    return ""

if __name__ == "__main__":
    asyncio.run(main_test())