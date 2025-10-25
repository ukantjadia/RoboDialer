import sys
import os
import argparse
import urllib.parse
import re
from bs4 import BeautifulSoup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from backend.config.browser_config import PlaywrightManager
import asyncio
import logging
import time
from backend.config.logger_config import setup_logger

setup_logger()
logger = logging.getLogger("118000 FR")

async def scrape_118000_businesses(industry: str, city: str, page=None, max_timeout=10.0):
    """
    Scrape business listings from 118000.fr by industry and city.
    Yields each business as it is scraped.
    If page is not provided, a new browser tab will be created.
    """
    base_url = "https://www.118000.fr/search"
    industry_encoded = urllib.parse.quote(industry)
    
    # Extract city and state from location string, e.g. "Paris,France,FRA"
    city_parts = city.split(",")
    city_name = city_parts[0].strip()
    state_name = city_parts[1].strip() if len(city_parts) > 1 else "France"
    
    city_encoded = urllib.parse.quote(city_name)

    manager = None
    internal_page = False
    if page is None:
        manager = PlaywrightManager(headless=False)
        page = await manager.start_browser(stealth_on=True)
        internal_page = True

    page_num = 1
    visited_urls = set()

    try:
        while True:
            if page_num == 1:
                current_url = f"{base_url}?label={city_encoded}&who={industry_encoded}"
            else:
                current_url = f"{base_url}?label={city_encoded}&who={industry_encoded}&page={page_num}"

            logger.info(f"Scraping page {page_num}...")
            logger.info(f"URL: {current_url}")
            
            if current_url in visited_urls:
                logger.warning("Already visited this URL - avoiding infinite loop")
                break
            visited_urls.add(current_url)

            try:
                await page.goto(current_url, wait_until="domcontentloaded", timeout=60000)
                
                # Only timeout if content hasn't loaded in 10s, and terminate if so
                content = None
                content_start = time.time()
                while True:
                    content = await page.content()
                    if content and len(content) > 0:
                        break
                    if time.time() - content_start > 10:
                        logger.info("Timeout (10s) waiting for page content - terminating scraper")
                        return
                    await asyncio.sleep(0.2)
                if not content:
                    page_num += 1
                    continue

                soup = BeautifulSoup(content, "html.parser")

                # Check for no results
                page_text = soup.get_text()
                if "Aucun résultat" in page_text or "No results" in page_text:
                    logger.info("No more results found")
                    break

                # Find main container
                main_container = soup.find("article", class_="chgd padl0 cardlist")
                if not main_container:
                    logger.info("No main container found - end of results")
                    break

                # Find business cards
                business_cards = main_container.find_all("section", class_="card lnk")
                if not business_cards:
                    logger.info("No business cards found - end of results")
                    break

                logger.info(f"Found {len(business_cards)} businesses on page {page_num}")

                for i, card in enumerate(business_cards):
                    try:
                        # Extract business name
                        name_element = card.find("h2", class_="name title inbl")
                        if name_element:
                            name_link = name_element.find("a")
                            name = name_link.get_text(strip=True) if name_link else ""
                        else:
                            name = ""

                        if not name or len(name) < 2:
                            continue

                        # Extract industry
                        industry_element = card.find("h3", class_="ico mtreset iconlower")
                        if industry_element:
                            industry_text = industry_element.get_text(strip=True)
                            # Remove any extra whitespace
                            industry_text = re.sub(r'\s+', ' ', industry_text).strip()
                        else:
                            industry_text = industry.capitalize()

                        # Extract address
                        address_element = card.find("div", class_="h4 address mtreset")
                        street_address = "NA"
                        if address_element:
                            address_parts = []
                            # Get all text content, handling <br> tags as line breaks
                            for element in address_element.stripped_strings:
                                address_parts.append(element)
                            
                            if address_parts:
                                # Take the first meaningful part as street address
                                street_address = address_parts[0].strip()
                                # Clean up street address
                                street_address = re.sub(r'\s+', ' ', street_address).strip()
                                
                                # If there are multiple parts, check if we need the second part too
                                if len(address_parts) > 1:
                                    second_part = address_parts[1].strip()
                                    # If second part doesn't look like a city/postal code, include it
                                    if not re.match(r'^\d{5}', second_part) and second_part.lower() != city.lower():
                                        street_address += f" {second_part}"

                        # Extract phone number
                        phone_element = card.find("div", class_="phone h2")
                        if phone_element:
                            phone_link = phone_element.find("a", class_="clickable atel")
                            if phone_link:
                                phone = phone_link.get_text(strip=True)
                                # Clean phone number
                                phone = re.sub(r'\s+', ' ', phone).strip()
                            else:
                                phone = "NA"
                        else:
                            phone = "NA"

                        # Create full address format similar to other scrapers
                        if street_address and street_address != "NA":
                            # Combine street with city parameter, not from parsed address
                            full_address = f"{street_address}, {city_name.capitalize()}, {state_name}"
                        else:
                            full_address = f"{city_name.capitalize()}, {state_name}"

                        business_info = {
                            "Company": name,
                            "Industry": industry_text,
                            "Address": full_address,
                            "State": state_name,
                            "Business_phone": phone,
                            "Website": "NA",
                            "BBB_rating": "NA"
                        }

                        yield business_info

                    except Exception as e:
                        logger.error(f"Error processing business card: {e}")
                        continue

                page_num += 1
                if page_num > 100:
                    logger.warning("Reached maximum page limit")
                    break

            except Exception as e:
                logger.error(f"Error on page {page_num}: {e}")
                break

    finally:
        if internal_page and manager is not None:
            await manager.stop_browser()

async def main():
    parser = argparse.ArgumentParser(description="Scrape business listings from 118000.fr by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'Software'")
    parser.add_argument("city", help="City to search in, e.g. 'Paris'")
    args = parser.parse_args()

    city_name = args.city.split(",")[0].strip()
    logger.info(f"Searching for {args.industry} businesses in {city_name}...")
    count = 0
    async for biz in scrape_118000_businesses(args.industry, args.city, max_timeout=10.0):
        count += 1
        logger.info(f"{count}. {biz['Company']}")
        logger.info(f"   Industry: {biz['Industry']}")
        logger.info(f"   Address: {biz['Address']}")
        logger.info(f"   Phone: {biz['Business_phone']}")
        logger.info(f"   Website: {biz['Website']}")
        logger.info(f"   BBB Rating: {biz['BBB_rating']}")
        logger.info("-" * 40)
    logger.info(f"\nFound {count} businesses total:")
    # logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())