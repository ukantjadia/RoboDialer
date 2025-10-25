import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
import argparse
import time
import urllib.parse
import re
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import random
import json
from urllib.parse import urljoin, urlparse
import asyncio  
from backend.config.browser_config import PlaywrightManager
import logging
from backend.config.logger_config import setup_logger

setup_logger()
logger = logging.getLogger("UK Directory Scraper")

async def scrape_uksmallbusiness_directory(industry: str, city: str, max_pages: int = 1, page=None):
    """
    Scrape business listings from UK Small Business Directory by industry and city.
    If page is not provided, a new browser tab will be created.
    """
    base_url = "https://www.uksmallbusinessdirectory.co.uk/int"
    industry_encoded = urllib.parse.quote(industry.lower())
    
    # Extract state code from city string, e.g. "London, ENG, UK"
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

    manager = None
    internal_page = False
    if page is None:
        manager = PlaywrightManager(headless=False)
        page = await manager.start_browser(stealth_on=True)
        internal_page = True
    
    # Hide automation
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
    """)
    
    try:
        for page_num in range(1, max_pages + 1):
            try:
                if page_num == 1:
                    url = f"{base_url}/{industry_encoded}-in-{city_encoded}/"
                else:
                    url = f"{base_url}/{industry_encoded}-in-{city_encoded}/{page_num}/"

                logger.info(f"Scraping page {page_num}: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                soup = BeautifulSoup(await page.content(), "html.parser")

                # Extract business listings from current page
                async for biz in extract_business_listings(page, soup, industry, city_name, state_full):
                    yield biz

                if page_num < max_pages:
                    pass
            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {str(e)}")
                continue
    finally:
        if internal_page and page is not None:
            await page.close()

async def extract_business_listings(page, soup, industry, city, state_full):
    """
    Extract business listings from the current page.
    """
    # Find tiered listings with "See Full Details" buttons
    tiered_listings = []
    see_full_details_buttons = soup.find_all("button", string="See Full Details")
    
    for button in see_full_details_buttons:
        parent_link = button.find_parent("a")
        if parent_link and parent_link.get("href"):
            tiered_listings.append(parent_link.get("href"))
    
    # Find regular business cards in txtcontainer divs
    business_cards = soup.find_all("div", class_="txtcontainer")
    
    # Skip the first txtcontainer div as it's usually navigation
    if business_cards:
        business_cards = business_cards[1:]
    
    total_businesses = len(tiered_listings) + len(business_cards)
    
    if total_businesses == 0:
        logger.info("No business listings found on this page")
        return
    
    logger.info(f"Found {len(tiered_listings)} tiered listings and {len(business_cards)} regular businesses")
    
    business_count = 0
    
    # Process tiered listings first
    for detail_url in tiered_listings:
        try:
            business_count += 1
            full_url = normalize_url(detail_url)
            
            business_info = await scrape_business_details(page, full_url, industry, city, state_full, is_tiered=True)
            
            if business_info:
                # logger.info(f"{business_count}. {business_info['Company']} (Tiered Listing)")
                # logger.info(f"   Industry: {business_info['Industry']}")
                # logger.info(f"   Street: {business_info['Street']}")
                # logger.info(f"   City: {business_info['City']}")
                # logger.info(f"   Phone: {business_info['Business_phone']}")
                # logger.info(f"   Website: {business_info['Website']}")
                # logger.info("-" * 40)
                
                yield business_info
        except Exception as e:
            logger.error(f"Error processing tiered listing {business_count}: {str(e)}")
            continue
    
    # Process regular business cards
    for card in business_cards:
        try:
            business_count += 1
            first_link = card.find("a")
            if not first_link or not first_link.get("href"):
                continue
            
            detail_url = first_link.get("href")
            full_url = normalize_url(detail_url)
            
            business_info = await scrape_business_details(page, full_url, industry, city, state_full, is_tiered=False)
            
            if business_info:
                # logger.info(f"{business_count}. {business_info['Company']} (Regular Listing)")
                # logger.info(f"   Industry: {business_info['Industry']}")
                # logger.info(f"   Street: {business_info['Street']}")
                # logger.info(f"   City: {business_info['City']}")
                # logger.info(f"   Phone: {business_info['Business_phone']}")
                # logger.info(f"   Website: {business_info['Website']}")
                # logger.info("-" * 40)
                
                yield business_info
        except Exception as e:
            logger.error(f"Error processing regular business card {business_count}: {str(e)}")
            continue

def normalize_url(url):
    """
    Normalize URL to ensure it's absolute and properly formatted.
    """
    if url.startswith("/"):
        return "https://www.uksmallbusinessdirectory.co.uk" + url
    elif not url.startswith("http"):
        return "https://www.uksmallbusinessdirectory.co.uk/" + url
    return url

async def scrape_business_details(page, detail_url, industry, city, state_full, is_tiered=False):
    """
    Scrape business details from the detail page.
    """
    try:
        logger.info(f"Scraping details from: {detail_url}")
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
        
        soup = BeautifulSoup(await page.content(), "html.parser")
        
        if is_tiered:
            return extract_tiered_listing_details(soup, industry, city, state_full)
        else:
            return extract_regular_listing_details(soup, industry, city, state_full)
            
    except Exception as e:
        logger.error(f"Error scraping business details from {detail_url}: {str(e)}")
        return None

def parse_uk_address(address_parts, fallback_city):
    """
    Parse UK address parts and format as Street, City
    Returns tuple of (street, city)
    """
    if not address_parts:
        return "NA", fallback_city.title()
    
    # Join all parts and clean up
    full_address = ", ".join(address_parts)
    
    # Split by commas and clean each part
    parts = [part.strip() for part in full_address.split(",") if part.strip()]
    
    if not parts:
        return "NA", fallback_city.title()
    
    # Remove postcode from the end if present
    if parts and re.match(r'^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$', parts[-1].strip()):
        parts = parts[:-1]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_parts = []
    for part in parts:
        part_lower = part.lower()
        if part_lower not in seen:
            seen.add(part_lower)
            unique_parts.append(part)
    
    if not unique_parts:
        return "NA", fallback_city.title()
    
    # Common UK cities and regions
    uk_cities = {
        'london', 'greater london', 'birmingham', 'manchester', 'liverpool', 
        'bristol', 'sheffield', 'leeds', 'edinburgh', 'glasgow', 'cardiff',
        'belfast', 'newcastle', 'nottingham', 'coventry', 'leicester',
        'bradford', 'southampton', 'brighton', 'portsmouth', 'reading',
        'northampton', 'luton', 'wolverhampton', 'bolton', 'bournemouth',
        'norwich', 'swindon', 'swansea', 'southend', 'middlesbrough',
        'wiltshire', 'surrey', 'kent', 'essex', 'hertfordshire', 'buckinghamshire'
    }
    
    # Find the city (usually the last recognizable city name)
    city = None
    street_parts = []
    
    # Work backwards to find the city
    for i in range(len(unique_parts) - 1, -1, -1):
        part_lower = unique_parts[i].lower()
        if part_lower in uk_cities:
            city = unique_parts[i]
            street_parts = unique_parts[:i]
            break
    
    # If no city found, use fallback city and all parts as street
    if not city:
        city = fallback_city.title()
        street_parts = unique_parts
    
    # Clean street parts - remove business names that might be at the start
    cleaned_street_parts = []
    for part in street_parts:
        # Remove common business suffixes/prefixes
        cleaned_part = re.sub(r'\b(Ltd|Limited|Inc|Corp|Corporation|Co|Company|LLP|plc)\b', '', part, flags=re.IGNORECASE)
        cleaned_part = re.sub(r'\bUnited Kingdom\b', '', cleaned_part, flags=re.IGNORECASE)
        cleaned_part = re.sub(r'\bUK\b', '', cleaned_part, flags=re.IGNORECASE)
        cleaned_part = cleaned_part.strip()
        
        if cleaned_part:
            cleaned_street_parts.append(cleaned_part)
    
    # Build the final street
    if cleaned_street_parts:
        street = ", ".join(cleaned_street_parts)
        # Remove extra spaces and punctuation
        street = re.sub(r'\s+', ' ', street).strip()
        street = re.sub(r'[,\s]+$', '', street)  # Remove trailing commas/spaces
    else:
        street = "NA"
    
    return street, city

def extract_tiered_listing_details(soup, industry, fallback_city, state_full):
    """
    Extract details from a tiered listing page.
    """
    # Find the main content container (txtcontainer)
    txtcontainer = soup.find("div", class_="txtcontainer")
    if not txtcontainer:
        return None
    
    # Find business name (h1 tag)
    name_tag = txtcontainer.find("h1")
    if not name_tag:
        return None
    
    name = name_tag.get_text(strip=True)
    
    # Skip if name is empty or too short
    if not name or len(name) < 2:
        return None
    
    # Get the HTML content after the h1 tag
    html_content = str(txtcontainer)
    
    # Split by <br> tags to get structured content
    parts = re.split(r'<br\s*/?>', html_content)
    
    # Clean up the parts and extract meaningful content
    clean_parts = []
    for part in parts:
        # Remove HTML tags and clean up
        clean_part = BeautifulSoup(part, "html.parser").get_text(strip=True)
        if clean_part and clean_part != name:
            clean_parts.append(clean_part)
    
    # Initialize variables
    address_parts = []
    phone = "NA"
    website = "NA"
    
    # Skip the first part if it's a long description (> 100 chars)
    start_index = 0
    if clean_parts and len(clean_parts[0]) > 100:
        start_index = 1
    
    # Process the remaining parts
    for i in range(start_index, len(clean_parts)):
        part = clean_parts[i]
        
        # Check if it's a phone number
        if is_phone_number(part):
            phone = part
            break
        
        # Check if it's a website
        if part.startswith('http'):
            continue
        
        # Check if it contains keywords that indicate end of address
        if any(keyword in part.lower() for keyword in ['competitive', 'intelligence', 'software', 'marketing', 'market', 'facebook', 'twitter']):
            break
        
        # If it's reasonable length and looks like address info
        if len(part) < 100 and part:
            address_parts.append(part)
    
    # Extract website from links
    website_links = txtcontainer.find_all("a", href=True)
    for link in website_links:
        href = link.get("href", "")
        if href and is_valid_website_url(href):
            website = href
            break
    
    # Parse address into street and city
    street, city = parse_uk_address(address_parts, fallback_city)
    
    # Create combined address for compatibility
    if street != "NA":
        full_address = f"{street}, {city}, {state_full}"
    else:
        full_address = f"{city}, {state_full}"
    
    return {
        "Company": name,
        "Industry": industry.capitalize(),
        "Street": street,
        "City": city,
        "Address": full_address,
        "State": state_full,
        "Business_phone": phone,
        "Website": website,
        "BBB_rating": "NA"
    }

def extract_regular_listing_details(soup, industry, fallback_city, state_full):
    """
    Extract details from a regular listing page.
    """
    # Find the h1 tag for business name
    name_tag = soup.find("h1")
    if not name_tag:
        return None

    name = name_tag.get_text(strip=True)
    
    # Skip if name is empty or too short
    if not name or len(name) < 2:
        return None

    # Get all content after the h1 tag
    container = name_tag.parent
    if not container:
        return None

    html_content = str(container)
    parts = re.split(r'<br\s*/?>', html_content)

    clean_parts = []
    for part in parts:
        clean_part = BeautifulSoup(part, "html.parser").get_text(strip=True)
        if clean_part and clean_part != name:
            clean_parts.append(clean_part)

    # Remove business name from address parts if present
    address_parts = []
    phone = "NA"
    website = "NA"
    collecting_address = True

    for i, part in enumerate(clean_parts):
        if not part:
            continue

        # Remove business name from address part if it appears at the start
        if collecting_address and i == 0 and part.startswith(name):
            part = part[len(name):].strip()

        if is_phone_number(part):
            phone = part
            collecting_address = False
            continue

        if "Website links are now only displayed on upgraded listings" in part:
            collecting_address = False
            continue

        if len(part) > 100 and collecting_address == False:
            break

        if collecting_address and len(part) < 100:
            address_parts.append(part)

    website_links = container.find_all("a", href=True)
    for link in website_links:
        href = link.get("href", "")
        if href and is_valid_website_url(href):
            website = href
            break

    # Parse address into street and city
    street, city = parse_uk_address(address_parts, fallback_city)
    
    # Create combined address for compatibility
    if street != "NA":
        full_address = f"{street}, {city}, {state_full}"
    else:
        full_address = f"{city}, {state_full}"

    return {
        "Company": name,
        "Industry": industry.capitalize(),
        "Street": street,
        "City": city,
        "Address": full_address,
        "State": state_full,
        "Business_phone": phone,
        "Website": website,
        "BBB_rating": "NA"
    }

def is_phone_number(text):
    """
    Check if text looks like a phone number.
    """
    # Remove spaces and common phone characters
    cleaned = re.sub(r'[\s\-\(\)\+]', '', text)
    
    # Check if it's mostly digits and has reasonable length
    if re.match(r'^\d{10,15}$', cleaned):
        return True
    
    # Check for UK phone format
    if re.match(r'^0\d{2,3}\s?\d{3,4}\s?\d{4}$', text):
        return True
    
    return False

def is_valid_website_url(url):
    """
    Check if URL is a valid website (not internal, email, or social media).
    """
    skip_domains = ['uksmallbusinessdirectory.co.uk', 'facebook.com', 'twitter.com', 
                    'instagram.com', 'linkedin.com', 'youtube.com']
    
    if url.startswith("mailto:"):
        return False
    
    if url.startswith("/listing-admin/"):
        return False
    
    if url.startswith("/"):
        return False
    
    parsed = urlparse(url)
    if parsed.netloc:
        for domain in skip_domains:
            if domain in parsed.netlookup:
                return False
    
    return True

def save_results_to_json(results, filename):
    """
    Save results to JSON file.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to {filename}")

def print_summary(businesses):
    """
    Print a summary of scraped businesses.
    """
    logger.info(f"\nFound {len(businesses)} businesses total:")
    logger.info("=" * 60)
    
    for i, biz in enumerate(businesses, 1):
        logger.info(f"{i}. {biz['Company']}")
        # logger.info(f"   Industry: {biz['Industry']}")
        # logger.info(f"   Street: {biz['Street']}")
        # logger.info(f"   City: {biz['City']}")
        # logger.info(f"   Phone: {biz['Business_phone']}")
        # logger.info(f"   Website: {biz['Website']}")
        # logger.info("-" * 40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape business listings from UK Small Business Directory by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'software'")
    parser.add_argument("city", help="City to search in, e.g. 'london'")
    parser.add_argument("--max-pages", type=int, default=1, help="Maximum number of pages to scrape (default: 1)")
    parser.add_argument("--output", help="Output JSON file name (optional)")
    
    args = parser.parse_args()
    
    logger.info(f"Searching for {args.industry} businesses in {args.city}...")
    if args.max_pages > 1:
        logger.info(f"Scraping up to {args.max_pages} pages...")
    
    async def run():
        results = []
        async for biz in scrape_uksmallbusiness_directory(args.industry, args.city, args.max_pages):
            results.append(biz)
        print_summary(results)
        if args.output:
            save_results_to_json(results, args.output)
    
    asyncio.run(run())