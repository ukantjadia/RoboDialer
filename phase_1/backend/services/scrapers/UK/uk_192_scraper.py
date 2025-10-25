import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
import argparse
import time
import urllib.parse
import asyncio
from bs4 import BeautifulSoup
from backend.config.browser_config import PlaywrightManager
import random
import logging
from backend.config.logger_config import setup_logger

setup_logger()
logger = logging.getLogger("UK 192 Scraper")

async def scrape_192_businesses(industry: str, location: str, page=None):
    """
    Scrape business listings from 192.com search results page by industry and city.
    Updated to handle multiple business card types and exclude closed businesses.
    If page is not provided, a new browser tab will be created.
    """
    base_url = "https://www.192.com/businesses"

    manager = None
    internal_page = False
    if page is None:
        manager = PlaywrightManager(headless=True)
        page = await manager.start_browser(stealth_on=True)
        internal_page = True
    try:
        logger.info(f"Navigating to 192.com businesses page...")
        await page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(random.randint(100, 500)) 

        # logger.info(f"Page title: {await page.title()}")
        # logger.info(f"Current URL: {page.url}")

        logger.info(f"Searching for '{industry}' in '{location}'...")

        # Use new selectors for business and location
        business_input = page.locator("#businessesLookingFor")
        location_input = page.locator("#businessesLocation")

        if await business_input.count() > 0:
            await business_input.fill(industry)
            await page.wait_for_timeout(random.randint(500, 1500))
            # logger.info(f"Filled business field with: {industry}")
        else:
            logger.error("Error: Could not find business name input field")
            # await page.screenshot(path="debug_192_no_business_input.png")

        if await location_input.count() > 0:
            await location_input.fill(location.split(",")[0].strip())  # Use only the city part
            await page.wait_for_timeout(random.randint(500, 1500))
            # logger.info(f"Filled location field with: {location}")
        else:
            logger.error("Error: Could not find location input field")
            # await page.screenshot(path="debug_192_no_location_input.png")

        # Use new selector for search button
        submit_button = page.locator("input.ont-btn-main.ont-fr")
        if await submit_button.count() > 0:
            # logger.info("Found submit button, clicking...")
            await submit_button.first.click()
        else:
            logger.info("No submit button found, pressing Enter...")
            await page.keyboard.press("Enter")

        await page.wait_for_timeout(5000)  # Wait for results to load

        # Parse results with debugging
        logger.info(f"Current URL after search: {page.url}")
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        # Find all business cards using the new function
        businesses = scrape_business_cards(soup)
        for business in businesses:
            yield business

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        # await page.screenshot(path="debug_192_error.png")
    finally:
        if internal_page and page is not None:
            await manager.stop_browser()

def scrape_business_cards(soup):
    """
    Scrape business cards from the HTML soup, handling multiple card types
    and excluding closed businesses.
    """
    businesses = []
    
    # First, find the closed businesses div and get its contents
    closed_div = soup.find("div", id="closed")
    closed_business_ids = set()
    
    if closed_div:
        # logger.info("Found closed businesses section")
        # Extract IDs or unique identifiers of closed businesses
        closed_cards = closed_div.find_all("li", class_=lambda x: x and "js-ont-gmap-record" in str(x))
        for card in closed_cards:
            # Use data-syndication-id as unique identifier
            business_id = card.get("data-syndication-id")
            if business_id:
                closed_business_ids.add(business_id)
        logger.info(f"Found {len(closed_business_ids)} closed businesses to exclude")
    
    # Find all business cards - both types
    # Type 1: Original long class name
    type1_cards = soup.find_all("li", class_=lambda x: x and "js-ont-gmap-record" in str(x) and "js-ont-business-results-for-yext" in str(x))
    
    # Type 2: Shorter class name (as seen in your images)
    type2_cards = soup.find_all("li", class_=lambda x: x and "js-ont-gmap-record" in str(x) and "js-ont-business-results-for-yext" not in str(x))
    
    all_cards = type1_cards + type2_cards
    logger.info(f"Found {len(type1_cards)} type 1 cards and {len(type2_cards)} type 2 cards")
    
    for card in all_cards:
        # Skip closed businesses
        business_id = card.get("data-syndication-id")
        if business_id and business_id in closed_business_ids:
            logger.info(f"Skipping closed business with ID: {business_id}")
            continue
            
        # Also check if the card is within the closed div
        if closed_div and card in closed_div.find_all("li"):
            logger.info("Skipping business in closed section")
            continue
            
        business_info = extract_business_info_from_card(card)
        if business_info:
            businesses.append(business_info)
    
    return businesses

def extract_business_info_from_card(card):
    """
    Extract business information from a business card element.
    Handles both original format and the new format shown in images.
    """
    try:
        # Extract business name
        name = "NA"
        
        # Try different selectors for business name
        name_selectors = [
            "h3.name a",  # Type 1 format
            "h3 a",       # General h3 link
            "h2 a",       # Alternative header
            "h1 a",       # Alternative header
            ".name a",    # Direct name class
            "a[title*='View Details']",  # Title-based selection
            "a[href*='/business/']",     # URL-based selection
        ]
        
        for selector in name_selectors:
            name_element = card.select_one(selector)
            if name_element:
                name = name_element.get_text(strip=True)
                # Clean up the name
                if name.startswith("View Details of"):
                    name = name.replace("View Details of", "").strip()
                if name:  # Only use if we got a non-empty name
                    break
        
        # Extract industry/category
        industry = "NA"
        industry_selectors = [
            ".ont-text-decrease.ont-bold.test-ont-business-result-market-sector",  # Specific class from image
            "div[class*='market-sector']",
            ".market-sector",
            "div[class*='category']",
            ".category",
            ".business-type",
            ".industry",
        ]
        
        for selector in industry_selectors:
            industry_element = card.select_one(selector)
            if industry_element:
                industry = industry_element.get_text(strip=True)
                if industry:
                    break
        
        # Extract address
        address = "NA"
        address_selectors = [
            ".ont-text-decrease.test-ont-business-result-address",  # Specific class from image
            "div[class*='address']",
            ".address",
            ".location",
            "div[class*='location']",
            ".business-address",
        ]
        
        for selector in address_selectors:
            address_element = card.select_one(selector)
            if address_element:
                address = address_element.get_text(strip=True)
                if address:
                    break
        
        # Extract phone number (optional)
        phone = "NA"
        phone_selectors = [
            ".telephone",  # From the phoneCol div
            "div[class*='telephone']",
            ".phone",
            "div[class*='phone']",
            "a[href^='tel:']",
            ".contact-phone",
        ]
        
        for selector in phone_selectors:
            phone_element = card.select_one(selector)
            if phone_element:
                if selector == "a[href^='tel:']":
                    phone = phone_element.get("href", "").replace("tel:", "")
                else:
                    phone = phone_element.get_text(strip=True)
                if phone:
                    break
        
        # Website is typically not available in search results
        website = "Not Available"
        
        # Only return if we have at least a name
        if name != "NA":
            return {
                "name": name,
                "industry": industry,
                "address": address,
                "phone": phone,
                "website": website,
            }
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error extracting business info from card: {e}")
        return None

def main():
    """
    Main function to handle command line arguments and run the scraper.
    """
    parser = argparse.ArgumentParser(description="Scrape business listings from 192.com search results by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'software'")
    parser.add_argument("city", help="City to search in, e.g. 'London'")
    args = parser.parse_args()

    
    logger.info(f"Searching for {args.industry} businesses in {args.city}...")

    
    # Run the async scraper
    async def run():
        count = 0
        async for biz in scrape_192_businesses(args.industry, args.city):
            count += 1
        #     logger.info(f"{count}. {biz['name']}")
        #     logger.info(f"   Industry: {biz['industry']}")
        #     logger.info(f"   Address: {biz['address']}")
        #     logger.info(f"   Phone: {biz['phone']}")
        #     logger.info(f"   Website: {biz['website']}")
        #     logger.info("-" * 40)
        logger.info(f"\nFound {count} businesses total:")
        # logger.info("=" * 60)
    asyncio.run(run())

if __name__ == "__main__":
    main()
