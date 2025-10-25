import os
import asyncio
import csv
from typing import List, Dict
import sys
from typing import AsyncGenerator

# Uncomment below lines if running this only this file for debugging
# sys.path.append(os.path.abspath("d:/Caprae Capital/Work/LeadGenAI/phase_1/backend"))
# sys.path.append(os.path.abspath("C:/Work/Internship/Web Scraper Caprae/LeadGenAI/phase_1/backend"))
# from config.browser_config import PlaywrightManager

# from backend.config.browser_config import PlaywrightManager

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.browser_config import PlaywrightManager
from playwright.async_api import Locator

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

BASE_URL = "https://www.google.com/maps"
OUTPUT_DIR = "../data"

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


async def scrape_lead_details(container: Locator) -> Dict[str, str]:
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
        address = "[G]" + info_texts[-1] if len(info_texts) > 2 else "NA"

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
        print(f"Error extracting data for a business: {e}")
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
    manager = PlaywrightManager(headless=True)
    try:
        if stop_flag and stop_flag["stop"]:
            # print("GMaps scraper stopped before starting.")
            return
        
        if page == None:
            page = await manager.start_browser(stealth_on=False)
            internal_browser = True
            
        await page.goto(BASE_URL)
        await asyncio.sleep(2)
        
        # Search for the query and location
        search_query = f"{industry} in {location}"
        await page.fill("input[name='q']", search_query)
        await page.keyboard.press("Enter")
        await page.wait_for_selector("div.ecceSd", timeout=10000)  # Wait for the scrollable container to load
        
        scrollable_container = page.locator("div.ecceSd").nth(1)

        while True:
            if stop_flag and stop_flag["stop"]:
                # print("🛑 Google Maps scraper stopped during scraping.")
                return           
            
            # Scroll to the bottom of the container
            await page.evaluate(
            """(container) => {
                container.scrollBy({ top: 500, behavior: 'smooth' });
            }""",
            await scrollable_container.element_handle()
            )
            await asyncio.sleep(1)
            if await page.locator("div.eKbjU").count() > 0:
                # print("Bottom reached")
                break

        # Count the number of loaded business containers
        business_containers = page.locator("div.bfdHYd.Ppzolf.OFBs3e")
        current_count = await business_containers.count()

        if current_count == 0:
            print("No businesses found on google maps")
            yield None
            return
        else:
            # print(f"Found {current_count} leads for {industry}, {location} on google maps")
            business_list = []
                
            for i in range(current_count):
                container = business_containers.nth(i)
                result = await scrape_lead_details(container)
                # business_list.append(result)
                yield result
                
    except Exception as e:
        raise RuntimeError(f"An error occurred while scraping: {e}")
        
    finally:
        if internal_browser:
            await manager.stop_browser()

# if __name__ == "__main__":
#     print(asyncio.run(scrape_lead_by_industry("dentists", "san diego, ca")))
