import os
import asyncio
import csv
import time
from typing import List, Dict
import sys
from typing import AsyncGenerator
from urllib.parse import quote_plus
from playwright.async_api import Page
import logging

# Uncomment below lines if running this only this file for debugging
# sys.path.append(os.path.abspath("d:/Caprae Capital/Work/LeadGenAI/phase_1/backend"))
# sys.path.append(os.path.abspath("C:/Work/Internship/Web Scraper Caprae/LeadGenAI/phase_1/backend"))
# from config.browser_config import PlaywrightManager

# from backend.config.browser_config import PlaywrightManager

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config.browser_config import PlaywrightManager
from playwright.async_api import Locator

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

BASE_URL = "https://www.google.com/maps"
OUTPUT_DIR = "../data"

logger = logging.getLogger("Google Maps")

def save_to_csv(data: List[Dict[str, str]], file_path: str, fieldnames: List[str]):
    """Saves a list of dictionaries to a CSV file."""
    if not data:
        print("Error: No data provided to save.")
        return
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    try:
        with open(file_path, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            
            # Write the header
            writer.writeheader()
            
            # Write the data
            for row in data:
                writer.writerow(row)
        
        print(f"Data successfully saved to {file_path}")
    
    except Exception as e:
        print(f"Error saving file: {e}")


async def scrape_lead_details(container: Locator, location:str) -> Dict[str, str]:
    try:
        company_name = (
            await container.locator("div.qBF1Pd.fontHeadlineSmall").text_content()
        ).strip() if await container.locator("div.qBF1Pd.fontHeadlineSmall").count() > 0 else "NA"

        second_info_div = container.locator("div.W4Efsd").nth(2)
        info_spans = await second_info_div.locator("span").all()
        info_texts = [
            (await span.text_content()).strip()
            for span in info_spans
            if (await span.text_content()).strip() and (await span.text_content()).strip() != "·"
        ]
        category = info_texts[0] if len(info_texts) > 0 else "NA"
        address = info_texts[-1] if len(info_texts) > 2 else "NA"

        # --- UK state translation logic ---
        state_full = None
        city_part = None
        if location:
            location_parts = location.split(",")
            if len(location_parts) > 1:
                city_part = location_parts[0].strip().title()
                state_code = location_parts[1].strip().upper()
                uk_state_map = {
                    "ENG": "England",
                    "SCO": "Scotland",
                    "WAL": "Welsh",
                    "CYM": "Welsh",
                    "NIR": "N. Ireland"
                }
                if state_code in uk_state_map:
                    state_full = uk_state_map[state_code]
        # Compose address with UK state if applicable
        if state_full:
            # If address already contains city, avoid duplication
            if city_part and city_part not in address:
                address += f", {city_part}"
            address += f", {state_full}"
        else:
            # fallback to previous logic for non-UK
            location_parts = location.rsplit(',', maxsplit=2) if location else ""
            if len(location_parts) > 1:
                address += ", " + location_parts[0].strip().title()
                address += ", " + location_parts[1].strip().upper()
            elif len(location_parts) == 1:
                address += ", " + location_parts[0].strip().upper()

        # rating_element = container.locator("span[aria-label*='stars']")
        # rating = (
        #     (await rating_element.get_attribute("aria-label")).split(" stars")[0]
        #     if await rating_element.count() > 0 else "NA"
        # )

        phone_element = container.locator("span.UsdlK")
        phone = (
            (await phone_element.text_content()).strip()
            if await phone_element.count() > 0 else "NA"
        )

        website_element = container.locator("a[aria-label^='Visit']")
        website = (
            await website_element.get_attribute("href")
            if await website_element.count() > 0 else "NA"
        )
        if website != "NA" and website.startswith("/"):
            website = f"https://www.googleadservices.com{website}"

        return {
            "Company": company_name,
            "Industry": category,
            "Address": address,
            "Business_phone": phone,
            "Website": website
        }
    except Exception as e:
        logger.error(f"Error extracting data for a business: {e}")
        return {
            "Company": "NA",
            "Industry": "NA",
            "Address": "NA",
            "Business_phone": "NA",
            "Website": "NA"
        }


async def scrape_lead_by_industry(industry: str, location: str, page=None, stop_flag: Dict[str, bool] = None) -> AsyncGenerator[Dict[str, str], None]:
    """Scrape multiple leads by industry and location from Google Maps."""
    internal_browser = False
    manager = PlaywrightManager(headless=False)
    try:
        if stop_flag and stop_flag["stop"]:
            return
        
        if page == None:
            page = await manager.start_browser(stealth_on=False)
            internal_browser = True
            
        search_query = f"{industry} in {location}"
        url = f"https://www.google.com/maps/search/{quote_plus(search_query)}"
        await page.goto(url, timeout=60000)
        await page.wait_for_selector("div.ecceSd", timeout=10000)  # Wait for the scrollable container to load
        
        scrollable_container = page.locator("div.ecceSd").nth(1)

        processed_count = 0
        stale_scroll_count = 0

        while True:
            if stop_flag and stop_flag["stop"]:
                # print("🛑 Google Maps scraper stopped during scraping.")
                return           
            
            business_containers = page.locator("div.bfdHYd.Ppzolf.OFBs3e")
            current_count = await business_containers.count()

            # If new businesses have been loaded by the last scroll, process them
            if current_count > processed_count:
                stale_scroll_count = 0 
                
                for i in range(processed_count, current_count):
                    container = business_containers.nth(i)
                    lead_details = await scrape_lead_details(container, location)
                    if lead_details["Company"] != "NA":
                        yield lead_details
                  
                processed_count = current_count
            else:
                stale_scroll_count += 1

            end_of_list_locator = page.locator("p.fontBodyMedium > span > span:has-text('end of the list')")
            if await end_of_list_locator.is_visible():
                logger.info("Reached the end of the list.")
                break
            
            # If we scroll multiple times and no new results appear, assume we are done
            if stale_scroll_count >= 3:
                logger.info("No new results after multiple scrolls. Concluding scrape.")
                break

            # next scroll action
            await scrollable_container.evaluate("node => node.scrollBy(0, 5000)")
            await asyncio.sleep(2)

                
    except Exception as e:
        logger.error("An error occurred while scraping: ", e)
        raise RuntimeError(f"An error occurred while scraping: {e}")
        
    finally:
        if internal_browser:
            await manager.stop_browser()

async def main_test():
    print("--- Testing Google Maps Scraper ---")
    results = []
    start_time = time.time()
    
    async for record in scrape_lead_by_industry("dentists", "san diego, ca, usa"):
        if record:
            print(f"    [+] Yielded: {record.get('Company')}")
            results.append(record)

    end_time = time.time()
    print("\n--- Test Summary ---")
    print(f"Scraped a total of {len(results)} businesses.")
    print(f"Total execution time: {end_time - start_time:.2f} seconds.")
    if results:
        import pprint
        print("\n--- Sample Results ---")
        pprint.pprint(results[:10])

if __name__ == "__main__":
    asyncio.run(main_test())
