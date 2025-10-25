import asyncio
import os
from typing import Dict, List
import random
import sys

# sys.path.append(os.path.abspath("d:/Caprae Capital/Work/LeadGenAI/phase_1/backend"))
# from config.browser_config import PlaywrightManager

from backend.config.browser_config import PlaywrightManager

# def setup_browser(playwright):
#     """Set up and return a configured Playwright browser instance."""
#     # Random user agent
#     user_agents = [
#         'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
#         'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
#         'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0',
#     ]
    
#     # Launch browser with specific options
#     browser = playwright.chromium.launch(
#         headless=False,  # Set to False for debugging
#         args=[
#             '--no-sandbox',
#             '--disable-dev-shm-usage',
#             f'--user-agent={random.choice(user_agents)}',
#         ]
#     )
    
#     # Create a context with specific options
#     context = browser.new_context(
#         viewport={'width': 1920, 'height': 1080},
#         user_agent=random.choice(user_agents),
#         has_touch=False,
#         java_script_enabled=True,
#         locale='en-US',
#         timezone_id='America/New_York',
#         # Bypass WebDriver detection
#         bypass_csp=True,
#     )
    
#     # Emulate a real browser by setting specific properties
#     page = context.new_page()
#     page.add_init_script("""
#     Object.defineProperty(navigator, 'webdriver', {
#         get: () => false
#     });
#     """)
    
    # return browser, context, page
# ----------------------------------------------------------------------------------------

async def scrape_yellowpages(industry: str, location: str, max_pages: int = 1) -> List[Dict[str, str]]:
    """
    Scrapes Yellow Pages using PlaywrightManager.

    Args:
        search_term (str): The type of business to search for.
        location (str): City, state, or zip code.
        max_pages (int): Maximum number of pages to scrape.

    Returns:
        List[Dict[str, str]]: List of dictionaries containing business information.
    """
    businesses = []
    manager = PlaywrightManager(headless=True)

    try:
        page = await manager.start_browser(stealth_on=True)
        
        # Construct the URL for the current page
        url = f"https://www.yellowpages.com/search?search_terms={industry}&geo_location_terms={location}"
        await page.goto(url)

        for page_num in range(1, max_pages + 1):
            # print(f"Scraping page {page_num}...")
            
            # Add random wait time to simulate human behavior
            wait_time = random.uniform(3, 5)
            # print(f"Waiting {wait_time:.2f} seconds for page to load...")
            await asyncio.sleep(wait_time)

            # Wait for the business listings to load
            try:
                await page.wait_for_selector(".scrollable-pane", timeout=3000)
            except Exception as e:
                print(f"Could not find business listings with .result: {e}")
                continue

            # Parse all business listings
            listings = await page.locator(".result").all()
            if not listings:
                print(f"No business listings found on page {page_num}.")
                continue

            # print(f"Found {len(listings)} leads on yellowpage.")

            for listing in listings:
                business_info = {}

                # Extract business name
                try:
                    name_element = listing.locator(".business-name")
                    business_info["Name"] = await name_element.inner_text() if await name_element.count() > 0 else "NA"
                except:
                    business_info["Name"] = "NA"

                # Extract industry/category
                try:
                    category_elements = listing.locator(".categories a")
                    if await category_elements.count() > 0:
                        categories = [await category.inner_text() for category in await category_elements.all()]
                        business_info["Industry"] = " ".join(categories)
                    else:
                        business_info["Industry"] = "NA"
                except:
                    business_info["Industry"] = "NA"

                # Extract address
                address_parts = []
                try:
                    street_address = listing.locator(".street-address")
                    if await street_address.count() > 0:
                        address_parts.append(await street_address.inner_text())
                except:
                    pass

                try:
                    locality = listing.locator(".locality")
                    if await locality.count() > 0:
                        address_parts.append(await locality.inner_text())
                except:
                    pass

                business_info["Address"] = ", ".join(address_parts) if address_parts else "NA"

                # Extract phone number
                try:
                    phone_element = listing.locator(".phones")
                    business_info["Business_phone"] = await phone_element.inner_text() if await phone_element.count() > 0 else "NA"
                except:
                    business_info["Business_phone"] = "NA"

                # Extract website
                try:
                    website_element = listing.locator(".track-visit-website")
                    business_info["Website"] = await website_element.get_attribute("href") if await website_element.count() > 0 else "NA"
                except:
                    business_info["Website"] = "NA"

                businesses.append(business_info)
                # print(f"Added business: {business_info['Industry']}")

            # Random delay between pages
            try:
                next_button = page.locator("a.next.ajax-page")
                if await next_button.count() > 0:
                    # print(f"Clicking 'Next' button to go to page {page_num + 1}...")
                    await next_button.click()
                    await asyncio.sleep(2)  # Add a short delay to allow the page to load
                else:
                    print("No 'Next' button found. Stopping pagination.")
                    break
            except Exception as e:
                print(f"Error clicking 'Next' button: {e}")
                break
            
        return businesses

    except Exception as e:
        print(f"Error during scraping: {e}")
        return []

    finally:
        await manager.stop_browser()
        

# if __name__ == "__main__":
#     businesses = [
#         ("Plumbing services", "glendale, az"),
#         ("HVAC", "Glendale, AZ"),
#         ("Pool contractors", "Glendale, AZ"),
#         ("Senior relocation service", "Chicago, IL"),
#     ]
#     for idx, (name,loc) in enumerate(businesses):
#         asyncio.run(scrape_yellowpages(name, loc))