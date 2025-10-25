import sys
import os
import argparse
import asyncio
import urllib.parse
import re
from bs4 import BeautifulSoup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from backend.config.browser_config import PlaywrightManager
import logging
from backend.config.logger_config import setup_logger

setup_logger()
logger = logging.getLogger("Scoot UK")

def parse_uk_address(raw_address: str, city: str) -> tuple:
    """
    Parse UK address to return tuple of (street, city)
    Takes only first and second part separated by comma
    """
    if not raw_address or raw_address == "NA":
        return "NA", city.title()
    
    # Split by comma and take only first two parts
    address_parts = raw_address.split(',')
    
    if len(address_parts) >= 2:
        # Take first part as street, second part as city
        street = address_parts[0].strip()
        parsed_city = address_parts[1].strip()
        
        # Clean up street - remove any remaining commas
        street = street.replace(',', '').strip()
        
        # Use parsed city if it's meaningful, otherwise fall back to parameter city
        if parsed_city and len(parsed_city) > 1 and not re.match(r'^[A-Z0-9\s]+$', parsed_city):
            final_city = parsed_city.title()
        else:
            final_city = city.title()
            
    elif len(address_parts) == 1:
        # Only one part, use it as street
        street = address_parts[0].strip().replace(',', '')
        final_city = city.title()
    else:
        street = "No Street"
        final_city = city.title()
    
    # Clean up extra spaces
    street = ' '.join(street.split())
    final_city = ' '.join(final_city.split())
    
    return street, final_city

async def scrape_scoot_businesses(industry: str, location: str):
    """
    Scrape business listings from Scoot.co.uk by industry and city.
    Yields each business as it is scraped.
    """
    base_url = "https://www.scoot.co.uk/find"
    industry_encoded = urllib.parse.quote(industry.capitalize())
    
    # Extract state code from location string, e.g. "London, ENG, UK"
    location_parts = location.split(",")
    city_name = location_parts[0].strip()
    state_code = location_parts[1].strip().upper() if len(location_parts) > 1 else ""
    state_map = {
        "ENG": "England",
        "SCO": "Scotland",
        "WAL": "Welsh",
        "CYM": "Welsh",
        "NIR": "N. Ireland"
    }
    state_full = state_map.get(state_code, "NA")
    
    city_encoded = urllib.parse.quote(city_name)
    url = f"{base_url}/{industry_encoded}-in-{city_encoded}/"
    
    manager = None
    internal_page = False
    # Fix: Define page variable properly
    page = None
    if page is None:
        manager = PlaywrightManager(headless=True)
        page = await manager.start_browser(stealth_on=True)
        internal_page = True

    try:
        current_url = url
        page_num = 1
        visited_urls = set()
        
        while True:
            logger.info(f"Scraping page {page_num}...")
            # logger.info(f"URL: {current_url}")
            
            # Avoid infinite loops
            if current_url in visited_urls:
                logger.warning("Already visited this URL - avoiding infinite loop")
                break
            visited_urls.add(current_url)
            
            try:
                await page.goto(current_url, wait_until="domcontentloaded", timeout=60000)
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Find results container
                results_container = soup.find("div", class_="results")
                if not results_container:
                    logger.info("No results container found")
                    break
                
                # Find business cards
                business_cards = results_container.find_all("div", class_="result relative")
                
                if not business_cards:
                    logger.info("No business cards found")
                    break
                
                if len(business_cards) == 1:
                    logger.info("No business cards found on this page")
                    break

                logger.info(f"Found {len(business_cards)} businesses on page {page_num}")
                
                # Process each business card
                for i, card in enumerate(business_cards):
                    try:
                        # Extract business name
                        name_element = card.find("h2", class_="result-title")
                        if name_element:
                            name_link = name_element.find("a")
                            name = name_link.get_text(strip=True) if name_link else ""
                        else:
                            name = ""
                        
                        # Skip this card if no business name found
                        if not name or name == "NA" or len(name.strip()) < 2:
                            continue
                        
                        # Extract industry
                        industry_element = card.find("p", class_="result-category")
                        if industry_element:
                            industry_text = industry_element.get_text(strip=True)
                            # Remove the "in [City]" part
                            industry_val = re.sub(r'\s+in\s+\w+.*$', '', industry_text, flags=re.IGNORECASE)
                        else:
                            industry_val = industry.capitalize()
                        
                        # Extract and parse address
                        address_element = card.find("p", class_="result-address")
                        if address_element:
                            raw_address = address_element.get_text(strip=True)
                            # Parse the address using the updated UK address parser
                            street, parsed_city = parse_uk_address(raw_address, location.split(",")[0].strip())
                        else:
                            street = "NA"
                            parsed_city = location.split(",")[0].strip().title()
                        
                        # Extract phone number
                        phone = await extract_phone_number(page, card)
                        
                        # Create combined address like MisterWhat format
                        if street and street != "NA":
                            full_address = f"{street}, {city_name.title()}, {state_full}"
                        else:
                            full_address = f"{city_name.title()}, {state_full}"
                        
                        # Fixed: Use the correct field names that match MisterWhat and frontend expectations
                        business_info = {
                            "Company": name,
                            "Industry": industry_val if industry_val else industry.capitalize(),
                            "Address": full_address,  # Combined address like MisterWhat
                            "State": state_full,
                            "Business_phone": phone,
                            "Website": "NA",
                            "BBB_rating": "NA"
                        }
                        
                        yield business_info
                        
                    except Exception as e:
                        logger.error(f"Error processing business card {i+1}: {e}")
                        continue
                
                # Check for next page
                next_url = get_next_page_url(current_url, page_num)
                
                # Test if next page exists by checking if URL changes when accessed
                test_page = await manager.new_page()
                try:
                    await test_page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
                    final_url = test_page.url
                    await test_page.close()
                    
                    # If URL redirects back to base URL, we've reached the end
                    if final_url == url or final_url.rstrip('/') == url.rstrip('/'):
                        logger.info("Reached end of results")
                        break
                    
                    current_url = next_url
                    page_num += 1
                    
                    # Safety limit
                    if page_num > 50:
                        logger.warning("Reached maximum page limit")
                        break
                        
                except Exception:
                    logger.error("Error accessing next page - ending scraping")
                    await test_page.close()
                    break
                    
            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {e}")
                break
                
    finally:
        if internal_page and manager is not None:
            await manager.stop_browser()

async def extract_phone_number(page, card_soup):
    """
    Extract phone number from business card, handling the show button if present.
    """
    try:
        # First, look for already visible phone numbers
        phone_elements = card_soup.find_all("p", class_="result-number")
        for phone_element in phone_elements:
            # Look for visible phone number
            phone_text = phone_element.get_text(strip=True)
            if phone_text and re.match(r'^[\d\s\-\(\)\+]+$', phone_text.replace(' ', '')):
                return phone_text
            
            # Look for clickable phone reveal button
            reveal_button = phone_element.find("a", class_="js-click-reveal")
            if reveal_button:
                # Get the data attributes that might contain the phone number
                data_link_number = reveal_button.get("data-link-number")
                if data_link_number:
                    return data_link_number
                
                # Try to click the reveal button using Playwright
                try:
                    # Find the button on the actual page
                    button_selector = f"a[data-link-number='{data_link_number}']" if data_link_number else "a.js-click-reveal"
                    button = page.locator(button_selector).first
                    if await button.count() > 0:
                        await button.click()
                        await page.wait_for_timeout(1000)  # Wait for reveal
                        
                        # Get updated content and extract phone
                        updated_content = await page.content()
                        updated_soup = BeautifulSoup(updated_content, "html.parser")
                        updated_phone_element = updated_soup.find("p", class_="result-number")
                        if updated_phone_element:
                            revealed_phone = updated_phone_element.get_text(strip=True)
                            if revealed_phone and re.match(r'^[\d\s\-\(\)\+]+$', revealed_phone.replace(' ', '')):
                                return revealed_phone
                except Exception:
                    pass
        
        return "NA"
        
    except Exception:
        return "NA"

def get_next_page_url(current_url, current_page_num):
    """
    Generate the URL for the next page.
    """
    next_page_num = current_page_num + 1
    
    if "?page=" in current_url:
        # Replace existing page parameter
        next_url = re.sub(r'page=\d+', f'page={next_page_num}', current_url)
    else:
        # Add page parameter
        next_url = current_url + f"?page={next_page_num}"
    
    return next_url

async def main():
    parser = argparse.ArgumentParser(description="Scrape business listings from Scoot.co.uk by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'restaurant'")
    parser.add_argument("city", help="City to search in, e.g. 'london'")
    args = parser.parse_args()
    
    logger.info(f"Searching for {args.industry} businesses in {args.city}...")
    count = 0
    async for biz in scrape_scoot_businesses(args.industry, args.city):
        count += 1
        # logger.info(f"{count}. {biz['name']}")
        # logger.info(f"   Industry: {biz['industry']}")
        # logger.info(f"   Address: {biz['address']}")
        # logger.info(f"   Phone: {biz['phone']}")
        # logger.info(f"   Website: {biz['website']}")
        # logger.info(f"   BBB Rating: {biz['bbb_rating']}")
        # logger.info("-" * 40)
    logger.info(f"\nFound {count} businesses total:")
    # logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
    # logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
