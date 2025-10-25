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
logger = logging.getLogger("Tel.fr")

async def scrape_tel_businesses(industry: str, city: str, page=None, max_timeout=10.0):
    """
    Scrape business listings from Tel.fr by industry and location.
    Yields each business as it is scraped.
    If page is not provided, a new browser tab will be created.
    """
    base_url = "https://www.tel.fr/pro/search"
    industry_encoded = urllib.parse.quote(industry)
    
    # Extract location parts, e.g. "Paris,France,FRA"
    location_parts = city.split(",")
    city_name = location_parts[0].strip()
    state_name = location_parts[1].strip() if len(location_parts) > 1 else "NA"
    country_code = location_parts[2].strip() if len(location_parts) > 2 else "NA"
    
    city_encoded = urllib.parse.quote(city_name)

    manager = None
    internal_page = False
    if page is None:
        manager = PlaywrightManager(headless=False)
        page = await manager.start_browser(stealth_on=True)
        internal_page = True

    page_num = 1
    visited_urls = set()
    max_pages = None

    try:
        while True:
            if page_num == 1:
                current_url = f"{base_url}?q={industry_encoded}&w={city_encoded}"
            else:
                current_url = f"{base_url}?q={industry_encoded}&w={city_encoded}&p={page_num}"

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

                # Check pagination to get max pages (only on first page)
                if page_num == 1 and max_pages is None:
                    pagination = soup.find("ul", class_="pagination")
                    if pagination:
                        page_links = pagination.find_all("li")
                        page_numbers = []
                        for li in page_links:
                            link = li.find("a")
                            if link and link.get_text(strip=True).isdigit():
                                page_numbers.append(int(link.get_text(strip=True)))
                        if page_numbers:
                            max_pages = max(page_numbers)
                            logger.info(f"Found maximum {max_pages} pages")

                # Find main results container
                results_container = soup.find("ul", class_="list-unstyled list-result searchList")
                if not results_container:
                    logger.info("No results container found - end of results")
                    break

                business_cards = results_container.find_all("li", class_="place_box")
                if not business_cards:
                    logger.info("No business cards found - end of results")
                    break

                logger.info(f"Found {len(business_cards)} businesses on page {page_num}")

                for i, card in enumerate(business_cards):
                    try:
                        # Extract business name from first col-xs-12 col-sm-6 div
                        first_col_div = card.find("div", class_="col-xs-12 col-sm-6")
                        if not first_col_div:
                            continue

                        # Find h2 with data-place-name
                        h2_element = first_col_div.find("h2")
                        if not h2_element:
                            continue

                        # Get business name from <a> inside h2
                        name_link = h2_element.find("a")
                        if not name_link:
                            continue

                        name = name_link.get_text(strip=True)
                        if not name or len(name) < 2:
                            continue

                        # Get industry from h3 after h2
                        h3_element = h2_element.find_next_sibling("h3")
                        if h3_element:
                            industry_text = h3_element.get_text(strip=True)
                        else:
                            industry_text = industry.capitalize()

                        # Extract address from <address> tag
                        address_element = card.find("address")
                        if address_element:
                            # Get the first text node only (before any <br> or other tags)
                            first_text_node = None
                            for content in address_element.contents:
                                if hasattr(content, 'strip') and content.strip():
                                    first_text_node = content.strip()
                                    break
                            
                            if first_text_node:
                                street_address = first_text_node
                            else:
                                # Fallback: get all text and take first line
                                address_text = address_element.get_text(strip=True)
                                street_address = address_text.split('\n')[0].strip()
                            
                            # Clean up any extra whitespace
                            street_address = re.sub(r'\s+', ' ', street_address).strip()
                        else:
                            street_address = "NA"

                        # Extract phone number from colBtn div
                        phone_div = card.find("div", class_="col-xs-12 col-sm-6 colBtn")
                        phone = "NA"
                        if phone_div:
                            # Look for tel attribute in any element
                            tel_elements = phone_div.find_all(attrs={"tel": True})
                            if tel_elements:
                                phone = tel_elements[0].get("tel", "NA")
                            else:
                                # Alternative: look for phone pattern in text
                                phone_pattern = r'(\d{2}\s\d{2}\s\d{2}\s\d{2}\s\d{2}|\+33\s?\d{1,2}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2})'
                                phone_text = phone_div.get_text()
                                phone_match = re.search(phone_pattern, phone_text)
                                if phone_match:
                                    phone = phone_match.group(1).strip()

                        # Build full address in consistent format
                        if street_address and street_address != "NA":
                            full_address = f"{street_address}, {city_name}, {state_name}"
                        else:
                            full_address = f"{city_name}, {state_name}"

                        # Skip businesses with no useful contact info
                        if (street_address == "NA" and phone == "NA"):
                            continue

                        name = re.sub(r'\s+', ' ', name).strip()

                        business_info = {
                            "Company": name,
                            "Industry": industry_text,
                            "Address": full_address,
                            "Street": street_address,
                            "City": city_name,
                            "State": state_name,
                            "Business_phone": phone,
                            "Website": "NA",
                            "BBB_rating": "NA"
                        }
                        yield business_info

                    except Exception as e:
                        continue

                # Check if we should continue to next page
                if max_pages and page_num >= max_pages:
                    logger.info(f"Reached maximum pages ({max_pages})")
                    break

                page_num += 1
                if page_num > 100:
                    logger.warning("Reached safety limit of 100 pages")
                    break

            except Exception as e:
                logger.error(f"Error on page {page_num}: {e}")
                break

    finally:
        if internal_page and manager is not None:
            try:
                await manager.stop_browser()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
                try:
                    if page:
                        await page.close()
                except:
                    pass

async def main():
    parser = argparse.ArgumentParser(description="Scrape business listings from Tel.fr by industry and location.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'Web'")
    parser.add_argument("location", help="Location to search in, e.g. 'Paris,France,FRA'")
    args = parser.parse_args()

    location_parts = args.location.split(",")
    city = location_parts[0].strip()
    logger.info(f"{city}")
    logger.info(f"Searching for {args.industry} businesses in {city}...")
    count = 0
    async for biz in scrape_tel_businesses(args.industry, args.location, max_timeout=10.0):
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