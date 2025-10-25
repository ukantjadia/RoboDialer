import sys
import os
import argparse
import urllib.parse
import re
from bs4 import BeautifulSoup
import asyncio
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from backend.config.browser_config import PlaywrightManager
import logging
from backend.config.logger_config import setup_logger

setup_logger()
logger = logging.getLogger("TradeFinder UK")

def parse_uk_address(raw_address):
    """
    Parse UK address to format: Street, City
    Handles complex address formats from tradefinder.co.uk
    """
    if not raw_address or raw_address == "NA":
        return "NA"
    
    # Remove extra whitespace and normalize
    address = re.sub(r'\s+', ' ', raw_address).strip()
    
    # Split by comma to get segments
    segments = [seg.strip() for seg in address.split(',')]
    
    if len(segments) < 2:
        return address
    
    # First segment is typically the street address (may contain dashes)
    street = segments[0]
    
    # Remove location/postcode patterns from street
    street = re.sub(r'-\s*[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}$', '', street)  # Remove postcodes
    street = re.sub(r'-\s*London-?\s*London', '', street)  # Remove duplicate London
    street = re.sub(r'-\s*[A-Z][a-z]+\s*-\s*[A-Z][a-z]+$', '', street)  # Remove area-county patterns
    street = re.sub(r'-\s*County\s+[A-Z][a-z]+', '', street)  # Remove County patterns
    street = re.sub(r'-\s*[A-Z]{2,}\s*-?$', '', street)  # Remove trailing area codes
    street = re.sub(r'-+$', '', street).strip()  # Remove trailing dashes
    
    # Replace remaining dashes with spaces in street
    street = re.sub(r'-', ' ', street)
    street = re.sub(r'\s+', ' ', street).strip()
    
    # Find city - prefer known UK city patterns
    city = "Unknown City"
    
    # Look for Greater London, City of London, or other major cities
    for segment in segments[1:]:
        segment_clean = segment.strip()
        # Skip postcodes
        if re.match(r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}$', segment_clean):
            continue
        # Prefer Greater London, City of London
        if 'Greater London' in segment_clean:
            city = 'Greater London'
            break
        elif 'City of London' in segment_clean:
            city = 'City of London'
            break
        # Look for other city names (avoiding postcodes and short codes)
        elif len(segment_clean) > 3 and not re.match(r'^[A-Z]{1,3}\s*\d', segment_clean):
            # Remove common area descriptors
            potential_city = re.sub(r'\s*Greater London.*', '', segment_clean)
            potential_city = re.sub(r'\s*[A-Z]{2,3}\s*\d.*', '', potential_city)
            if len(potential_city.strip()) > 3:
                city = potential_city.strip()
                break
    
    # If no good city found, use the second segment cleaned up
    if city == "Unknown City" and len(segments) > 1:
        city = re.sub(r'\s*[A-Z]{1,2}\d.*', '', segments[1]).strip()
        if not city or len(city) <= 2:
            city = "Greater London"  # Default for London area
    
    return f"{street}, {city}"

async def scrape_thetradefinder_businesses(industry: str, city: str, page=None):
    """
    Scrape business listings from thetradefinder.co.uk by industry and city.
    """
    base_url = "https://thetradefinder.co.uk/listing-search"
    industry_encoded = urllib.parse.quote(industry.lower())
    # Parse city argument by commas, and only pass the first part as City
    city_parts = city.split(",")
    city_name = city_parts[0].strip()
    state_code = city_parts[1].strip().upper() if len(city_parts) > 1 else ""
    state_map = {
        "ENG": "England",
        "SCO": "Scotland",
        "WAL": "Welsh",
        "CYM": "Welsh",
        "NIR": "N. Ireland"
    }
    state_full = state_map.get(state_code, "NA")
    city_encoded = urllib.parse.quote(city_name.lower())
    
    manager = PlaywrightManager(headless=True)
    page = await manager.start_browser(stealth_on=True)
        
    try:
        page_num = 1
        visited_urls = set()
        
        while True:
            if page_num == 1:
                current_url = f"{base_url}?searchtext={industry_encoded}&location={city_encoded}"
            else:
                current_url = f"{base_url}?searchtext={industry_encoded}&location={city_encoded}&page={page_num}"
            
            logger.info(f"Scraping: {current_url}")
            
            if current_url in visited_urls:
                break
            visited_urls.add(current_url)
            
            try:
                await page.goto(current_url, wait_until="networkidle", timeout=60000)
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                business_cards = []
                main_container = soup.find("div", class_="listi_body row")
                if main_container:
                    business_cards = main_container.find_all("div", class_=lambda x: x and "lis_block" in x)
                if not business_cards:
                    business_cards = soup.find_all("div", class_=lambda x: x and "lis_block" in x)
                if not business_cards:
                    business_cards = soup.find_all("div", class_="te_block")
                
                if not business_cards:
                    page_text = soup.get_text().lower()
                    no_results_indicators = [
                        "No results found", "no results", "0 results", "Sorry, no listings found"
                    ]
                    if any(indicator in page_text for indicator in no_results_indicators):
                        break
                    page_num += 1
                    if page_num > 5:
                        break
                    continue
                
                for card in business_cards:
                    try:
                        name = "NA"
                        for selector in ["h3.title", "h3.title.d-flex.align-items-center", ".title", "h3", ".business-name"]:
                            name_elem = card.select_one(selector)
                            if name_elem:
                                name = name_elem.get_text(strip=True)
                                break
                        
                        industry_val = "NA"
                        for selector in ["h5.sub_t", ".sub_t", "h5", ".industry"]:
                            industry_elem = card.select_one(selector)
                            if industry_elem:
                                industry_val = industry_elem.get_text(strip=True)
                                break
                        
                        phone = "NA"
                        phone_links = card.find_all("a", href=lambda x: x and x.startswith("tel:"))
                        if phone_links:
                            phone = phone_links[0].get("href", "").replace("tel:", "").strip()
                        else:
                            phone_links = card.find_all("a", class_="butt")
                            for link in phone_links:
                                href = link.get("href", "")
                                if href.startswith("tel:"):
                                    phone = href.replace("tel:", "").strip()
                                    break
                        
                        address = "NA"
                        for selector in ["p.addrs", ".addrs", ".address", "p"]:
                            address_elem = card.select_one(selector)
                            if address_elem:
                                location_icon = address_elem.find("i", class_=lambda x: x and "location" in str(x))
                                if location_icon and location_icon.next_sibling:
                                    raw_address = str(location_icon.next_sibling).strip()
                                    raw_address = re.sub(r'\s+', ' ', raw_address).strip()
                                    address = parse_uk_address(raw_address)
                                    break
                                else:
                                    addr_text = address_elem.get("textContent", "").strip()
                                    if addr_text and len(addr_text) > 5:
                                        address = parse_uk_address(addr_text)
                                        break
                        
                        website = "NA"
                        website_links = card.find_all("a", href=True)
                        for link in website_links:
                            href = link.get("href", "")
                            if href and not href.startswith(("tel:", "sms:", "mailto:")) and href.startswith(("http", "www")):
                                # Exclude tradefinder internal links
                                if "thetradefinder.co.uk/listing/" in href:
                                    website = "NA"
                                else:
                                    website = href
                                break
                        
                        name = re.sub(r'\s+', ' ', name).strip()
                        industry_val = re.sub(r'\s+', ' ', industry_val).strip()
                        
                        if not name or name == "NA" or len(name) < 2:
                            continue
                        
                        # Create combined address with state like MisterWhat format
                        if address and address != "NA":
                            full_address = f"{address}, {state_full}"
                        else:
                            full_address = f"{city_name.capitalize()}, {state_full}"

                        business_info = {
                            "Company": name,
                            "Industry": industry_val if industry_val != "NA" else industry.capitalize(),
                            "Address": full_address,  # Combined address like MisterWhat
                            "State": state_full,
                            "Business_phone": phone,
                            "Website": website,
                            "BBB_rating": "NA"
                        }
                        
                        yield business_info
                    
                    except Exception:
                        continue
                
                if len(business_cards) == 0:
                    break
                
                page_num += 1
                if page_num > 99:
                    break
                    
            except Exception:
                break
                
    finally:
        await manager.stop_browser()

async def main():
    parser = argparse.ArgumentParser(description="Scrape business listings from thetradefinder.co.uk by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'software'")
    parser.add_argument("city", help="City to search in, e.g. 'london'")
    args = parser.parse_args()
    
    logger.info(f"Searching for {args.industry} businesses in {args.city}...")
    count = 0
    async for biz in scrape_thetradefinder_businesses(args.industry, args.city):
        count += 1
        logger.info(f"{count}. {biz['Company']}")
        logger.info(f"   Industry: {biz['Industry']}")
        logger.info(f"   Address: {biz['Address']}")
        logger.info(f"   Phone: {biz['Business_phone']}")
        logger.info(f"   Website: {biz['Website']}")
        logger.info(f"   BBB Rating: {biz['BBB_rating']}")
        logger.info("-" * 40)
    logger.info(f"\nFound {count} businesses total:")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
