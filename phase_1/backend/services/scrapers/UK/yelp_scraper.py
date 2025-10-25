import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
import argparse
import time
import urllib.parse
import re
from bs4 import BeautifulSoup
from backend.config.browser_config import PlaywrightManager
import asyncio
import logging
from backend.config.logger_config import setup_logger
from backend.services.helper.flaresolverr_cookies import get_solved_cookies

setup_logger()
logger = logging.getLogger("Yelp UK Scraper")

async def scrape_yelp_uk_businesses(industry: str, city: str, page=None):
    """
    Scrape business listings from Yelp UK by industry and city.
    If page is not provided, a new browser tab will be created.
    """
    base_url = "https://www.yelp.co.uk/search"
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
    industry_encoded = urllib.parse.quote(industry)
    city_encoded = urllib.parse.quote(city_name)

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
    start = 0
    page_num = 1

    try:
        # Get solved cookie
        initial_search_url_for_fs = f"https://www.yelp.co.uk/search?find_desc=it%20consulting&find_loc=london%2C%20england%2C%20UK"
        cookies = get_solved_cookies(initial_search_url_for_fs) 

        if cookies:
            logger.info(f"Successfully obtained {len(cookies)} cookies from FlareSolverr.")
            logger.info(f"Cookies: {cookies}")
            await page.context.add_cookies(cookies)
        else:
            logger.warning("FlareSolverr failed to return cookies. Proceeding without them, likely to be blocked.")
            if internal_page: await manager.stop_browser()

        while True:
            url = f"{base_url}?find_desc={industry_encoded}&find_loc={city_encoded}&start={start}"
            logger.info(f"Scraping page {page_num}...")
            logger.info(f"URL: {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                soup = BeautifulSoup(await page.content(), "html.parser")

                # Check for "no more results" message
                error_msg = soup.find("h3", class_="y-css-n2l5h3")
                if error_msg and "sorry, the page of results you requested is unavailable" in error_msg.get_text().lower():
                    logger.info("No more results available")
                    break

                # Find the main container
                main_container = soup.find("ul", class_="list__09f24__ynIEd")
                if not main_container:
                    logger.info("Could not find main container")
                    break

                # Find business cards
                business_cards = main_container.find_all("li", class_="y-css-mhg9c5")

                if not business_cards:
                    logger.info("No business cards found")
                    break

                valid_cards = []
                for card in business_cards:
                    # Skip empty cards
                    if not card.get_text(strip=True):
                        continue

                    # Find the link to business details
                    detail_link = card.find("a", class_="y-css-o72qzn")
                    if detail_link and detail_link.get("href"):
                        valid_cards.append(card)

                if not valid_cards:
                    logger.info("No valid business cards found")
                    break

                logger.info(f"Found {len(valid_cards)} businesses on page {page_num}")

                # Process each business card
                for i, card in enumerate(valid_cards):
                    try:
                        # Get detail page URL
                        detail_link = card.find("a", class_="y-css-o72qzn")
                        if not detail_link or not detail_link.get("href"):
                            continue

                        detail_url = detail_link.get("href")
                        if detail_url.startswith("/"):
                            detail_url = "https://www.yelp.co.uk" + detail_url

                        # Scrape detailed information from business page
                        name, industry_val, address, phone, website = await scrape_business_details(page, detail_url)

                        if name == "NA":
                            continue

                        # Add state to address if not already present
                        if address and address != "NA":
                            if state_full not in address:
                                address = f"{address}, {state_full}"
                        else:
                            address = f"{city_name}, {state_full}"

                        business_info = {
                            "name": name,
                            "industry": industry_val,
                            "address": address,
                            "state": state_full,
                            "phone": phone,
                            "website": website,
                            "bbb_rating": "NA"
                        }
                        yield business_info

                    except Exception as e:
                        logger.error(f"Error processing card {i+1}: {str(e)}")
                        continue

                # Move to next page
                start += 10
                page_num += 1

                # Safety limit
                if page_num > 100:
                    logger.warning("Reached maximum page limit")
                    break

            except Exception as e:
                logger.error(f"Error on page {page_num}: {str(e)}")
                break
    finally:
        if internal_page and page is not None:
            await manager.stop_browser()

def extract_phone_number(soup):
    """Extract phone number from the page"""
    phone = "NA"
    
    try:
        # Look in the contact container for ALL paragraphs (not just specific class)
        contact_container = soup.find("div", class_="y-css-8x4us")
        if contact_container:
            # Get ALL paragraphs in the contact container
            all_paragraphs = contact_container.find_all("p")
            
            for p in all_paragraphs:
                p_text = p.get_text(strip=True)
                
                # Just check if this looks like a phone number
                if re.search(r'\d{3,}', p_text) and (
                    re.search(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', p_text) or
                    re.search(r'\b\d{11}\b', p_text) or
                    re.search(r'\+44', p_text) or
                    len(re.findall(r'\d', p_text)) >= 10
                ):
                    phone = p_text
                    break
        
        # Fallback: search the entire page
        if phone == "NA":
            phone_patterns = [
                r'\b\d{11}\b',
                r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
                r'\+44[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
            ]
            page_text = soup.get_text()
            for pattern in phone_patterns:
                match = re.search(pattern, page_text)
                if match:
                    phone = match.group()
                    break
    except Exception:
        pass
    
    return phone
    
def extract_website(soup):
    """Extract website from the page"""
    website = "NA"
    
    try:
        # Look in the contact container for website links
        contact_container = soup.find("div", class_="y-css-8x4us")
        if contact_container:
            # Look for ANY anchor tag with the website class
            website_link = contact_container.find("a", class_="y-css-14ckas3")
            if website_link:
                website_text = website_link.get_text(strip=True)
                # If it's just "Business website", get the href
                if website_text.lower() == "business website":
                    website = website_link.get("href", "NA")
                else:
                    website = website_text
        
        # Fallback: search for any external links
        if website == "NA":
            website_links = soup.find_all("a", href=re.compile(r"^https?://"))
            for link in website_links:
                href = link.get("href")
                if href and "yelp" not in href.lower():
                    website = href
                    break
    except Exception:
        pass
    
    return website

async def scrape_business_details(page, detail_url):
    """
    Scrape detailed information from business detail page.
    """
    name = "NA"
    industry_val = "NA"
    address = "NA"
    phone = "NA"
    website = "NA"
    
    try:
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
        
        soup = BeautifulSoup(await page.content(), "html.parser")
        
        # Remove style blocks that might interfere with parsing
        for style in soup.find_all("style"):
            style.decompose()
        
        # Extract name
        try:
            name_elem = soup.find("h1", class_="y-css-olzveb")
            if name_elem:
                name = name_elem.get_text(strip=True)
        except Exception:
            pass
        
        # Extract industry - Look for spans with BizHeaderCategory data-testid
        try:
            industries = []
            
            # Method 1: Look for spans with specific data-testid
            category_spans = soup.find_all("span", attrs={"data-testid": "BizHeaderCategory"})
            for span in category_spans:
                # Find the anchor tags inside
                category_links = span.find_all("a", class_="y-css-1x1e1r2")
                for link in category_links:
                    category_text = link.get_text(strip=True)
                    if category_text and category_text not in industries:
                        industries.append(category_text)
            
            # Method 2: If no results, try broader search
            if not industries:
                # Look for all anchor tags with the industry class
                category_links = soup.find_all("a", class_="y-css-1x1e1r2")
                for link in category_links:
                    category_text = link.get_text(strip=True)
                    if category_text and category_text not in industries:
                        industries.append(category_text)
            
            if industries:
                industry_val = ", ".join(industries)
        except Exception:
            pass
        
        # Extract website and phone using separate functions
        phone = extract_phone_number(soup)
        website = extract_website(soup)
        
        # Extract address - Look inside div with class "y-css-13akgjv" 
        # Based on your images, address seems to be in a different container
        try:
            # Try the original selector first
            address_container = soup.find("div", class_="y-css-13akgjv")
            if address_container:
                address_p = address_container.find("p", class_="y-css-p0gpmm")
                if address_p:
                    address = address_p.get_text(strip=True)
            
            # If not found, try alternative selectors based on the images
            if address == "NA":
                # From your images, it looks like address might be in a paragraph with font-weight semibold
                address_candidates = soup.find_all("p", attrs={"data-font-weight": "semibold"})
                for candidate in address_candidates:
                    candidate_text = candidate.get_text(strip=True)
                    # Check if this looks like an address (contains common address indicators)
                    if any(indicator in candidate_text.lower() for indicator in 
                           ['street', 'road', 'avenue', 'lane', 'drive', 'way', 'close', 'place', 'square', 'london', 'birmingham', 'manchester', 'glasgow', 'edinburgh']):
                        address = candidate_text
                        break
                
            # Alternative approach: look for address in the same container as phone/website
            if address == "NA":
                contact_container = soup.find("div", class_="y-css-8x4us")
                if contact_container:
                    # Look for paragraphs that might contain address
                    all_paragraphs = contact_container.find_all("p")
                    for p in all_paragraphs:
                        p_text = p.get_text(strip=True)
                        # Skip if it's a phone number or website
                        if (not re.search(r'\d{10,}', p_text) and 
                            not re.search(r'website', p_text.lower()) and
                            not p.find("a") and
                            len(p_text) > 10):  # Address should be reasonably long
                            # Check if this looks like an address
                            if any(indicator in p_text.lower() for indicator in 
                                   ['street', 'road', 'avenue', 'lane', 'drive', 'way', 'close', 'place', 'square', 'london', 'birmingham', 'manchester', 'glasgow', 'edinburgh', 'uk', 'england', 'scotland', 'wales']):
                                address = p_text
                                break
        except Exception:
            pass
        
        # Fallback attempts if primary selectors fail
        if name == "NA":
            try:
                # Try alternative name selectors
                name_elem = soup.find("h1") or soup.find("h2")
                if name_elem:
                    name = name_elem.get_text(strip=True)
            except Exception:
                pass
        
    except Exception as e:
        logger.error(f"Error scraping details from {detail_url}: {str(e)}")
    
    return name, industry_val, address, phone, website

async def main():
    parser = argparse.ArgumentParser(description="Scrape business listings from Yelp UK by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'Hardware'")
    parser.add_argument("city", help="City to search in, e.g. 'London'")
    args = parser.parse_args()
    
    logger.info(f"Searching for {args.industry} businesses in {args.city}...")
    count = 0
    async for biz in scrape_yelp_uk_businesses(args.industry, args.city):
        count += 1
        logger.info(f"{count}. {biz['name']}")
        logger.info(f"   Industry: {biz['industry']}")
        logger.info(f"   Address: {biz['address']}")
        logger.info(f"   Phone: {biz['phone']}")
        logger.info(f"   Website: {biz['website']}")
        logger.info(f"   BBB Rating: {biz['bbb_rating']}")
        logger.info("-" * 40)
    logger.info(f"\nFound {count} businesses total:")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
