import asyncio
import os
import pprint
import time
from typing import Dict, List
import sys
from typing import AsyncGenerator
from urllib.parse import quote_plus
import logging

# sys.path.append(os.path.abspath("d:/Caprae Capital/Work/LeadGenAI/phase_1/backend"))
# from config.browser_config import PlaywrightManager

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from backend.config.browser_config import PlaywrightManager

logger = logging.getLogger("BBB")

# FIELDNAMES = ["Name", "Industry", "Address", "Business_phone", "BBB_rating"]
def get_country(location: str) -> str:
    try:
        # Expected format: "City, State/Province, Country_Code"
        country_code = location.split(',')[-1].strip().upper()
    except IndexError:
        country_code = ""

    return country_code

async def scrape_bbb(industry: str, location: str, page=None) -> AsyncGenerator[Dict[str, str], None]:  
    country_code = get_country(location)
    formatted_industry = quote_plus(industry)
    region = location.rsplit(",", 1)[0].strip()
    formatted_region = quote_plus(region)
    internal_browser = False
    page_num = 1
    try:
        if page == None:
            browser_manager = PlaywrightManager(headless=False)
            page = await browser_manager.start_browser(stealth_on=True)
            internal_browser = True
        
        while True:
            BASE_URL = f"https://www.bbb.org/search?find_country={country_code}&find_loc={formatted_region}&find_text={formatted_industry}&page={page_num}"
            try:
                await page.goto(BASE_URL)
                await page.wait_for_selector("div.stack.stack-space-20", timeout=15000)
                count = await page.locator("div.card.result-card").count()
            except:
                break
                       
            for i in range(3, count): # Skip the first 3 cards (ads)
                details = {}
                try:
                    card = page.locator("div.card.result-card").nth(i)
                    
                    business_name_selector = "h3.result-business-name a"
                    business_element = await card.locator(business_name_selector).count()
                    details['Company'] = await card.locator(business_name_selector).inner_text() if business_element > 0 else "NA"
                    details["Company"] = details["Company"].replace("advertisement:\n", "").strip()
                        
                    # Scrape industry
                    industry_selector = "p.bds-body.text-size-4.text-gray-70"
                    industry_element = await card.locator(industry_selector).count()
                    details['Industry'] = str(await card.locator(industry_selector).inner_text()).split(",")[0] if industry_element > 0 else "NA"

                    # Scrape phone number
                    phone_number_selector = "a.text-black[href^='tel:']"
                    phone_number_element = await card.locator(phone_number_selector).count()
                    details['Business_phone'] = await card.locator(phone_number_selector).inner_text() if phone_number_element > 0 else "NA"

                    # Scrape address
                    address_locator = card.locator("p.bds-body.text-size-5.text-gray-70")
                    address_element = await address_locator.count()
                    full_address = await address_locator.text_content() if address_element > 0 else ""
                    postal_code_locator = address_locator.locator("span[style='white-space:nowrap']")

                    if await postal_code_locator.count() > 0:
                        postal_code = await postal_code_locator.text_content()
                        cleaned_text = full_address.replace(postal_code, "").strip()
                        if cleaned_text.endswith(','):
                            cleaned_text = cleaned_text.rstrip(',').strip()
                        details['Address'] = cleaned_text
                    else:
                        details['Address'] =  full_address.strip()
                    
                    
                    # BBB rating
                    bbb_selector = "span.result-rating"
                    bbb_rating_element = await card.locator(bbb_selector).count()
                    if bbb_rating_element > 0:
                        rating_text = await card.locator(bbb_selector).inner_text()
                        details['BBB_rating'] = rating_text.split()[-1] 
                    else:
                        details['BBB_rating'] = "NA"
                    
                    details.update({
                        "Company": details['Company'],
                        "Industry": details['Industry'],
                        "Address": details['Address'],
                        "Business_phone": details['Business_phone'],
                        "BBB_rating": details['BBB_rating']
                    })
                    yield details
                    # lead_list.append(details)
                    
                except Exception as e:
                    logger.error(f"Error extracting data for card {i}: {e}")
                
            # Go to next page if available
            try:
                next_page_btn = page.locator('div.not-sidebar.stack > nav > a[rel="next"]', has_text="Next")
                if await next_page_btn.count() > 0:
                    page_num += 1               
                else:
                    break
                
            except Exception as e:
                logger.error(f"Error during pagination: {e}")
                break
                # return lead_list  # Return the leads collected so far
                
        # print(f"Found {len(lead_list)} leads in BBB")
        # return lead_list
        
    except Exception as e:
        logger.error(f"Error during search: {e}")
        yield None
        return
    
    finally:
        if internal_browser:
            await browser_manager.stop_browser()
    
async def testing():
    query = "dentist"
    location = "toronto, ON, CAN"
    result = []
    
    print(f"--- Testing BBB scraper for '{query}' in '{location}' ---")
    start_time = time.time()
    async for record in scrape_bbb(
        industry=query, 
        location=location,
    ):
        if record:
            print(f"  [+] Yielded: {record.get('Company')}")
            result.append(record)

    end_time = time.time()

    print(f"\nFound {len(result)} total leads.")
    print(f"Total execution time: {end_time - start_time:.2f} seconds.")

    if result:
        print("--- Sample Results ---")
        pprint.pprint(result[:3])

if __name__ == "__main__":
    asyncio.run(testing())