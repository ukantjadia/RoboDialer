import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
import argparse
import time
import urllib.parse
import re
from bs4 import BeautifulSoup
from backend.config.browser_config import PlaywrightManager
import random
import asyncio
import logging
from backend.config.logger_config import setup_logger

setup_logger()
logger = logging.getLogger("ShowMeLocal UK")

async def scrape_showmelocal_businesses(industry: str, city: str, page=None):
    """
    Scrape business listings from ShowMeLocal UK by industry and city.
    If page is not provided, a new browser tab will be created.
    """
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

    # Extract state code from city string, e.g. "London, ENG, UK"
    city_parts = city.split(",")
    city_name = city_parts[0].strip().capitalize()
    state_code = city_parts[1].strip().upper() if len(city_parts) > 1 else ""
    state_map = {
        "ENG": "England",
        "SCO": "Scotland",
        "WAL": "Welsh",
        "CYM": "Welsh",
        "NIR": "N. Ireland"
    }
    state_full = state_map.get(state_code, "NA")

    try:
        logger.info("Navigating to ShowMeLocal UK...")
        await page.goto("https://uk.showmelocal.com/", wait_until="domcontentloaded", timeout=60000)

        # Fill search form with correct selectors
        logger.info(f"Searching for {industry} in {city_name}...")
        await page.fill('#ctl04_txtWhat', industry)
        await page.fill('#ctl04_txtWhere', city_name)

        # Click search button
        await page.click('#ctl04_cmdSearch')
        await page.wait_for_load_state("domcontentloaded")

        page_num = 1

        while True:
            logger.info(f"Scraping page {page_num}...")

            # Wait for the business table to load
            try:
                await page.wait_for_selector('#dgBusinesses', timeout=10000)
            except:
                logger.info("No business table found - may be end of results")
                break

            soup = BeautifulSoup(await page.content(), "html.parser")

            business_table = soup.find("table", {"id": "dgBusinesses"})
            if not business_table:
                logger.info("No business table found")
                break

            business_cards = business_table.find_all("div", class_="bg-white rounded mb-2 mt-0 p-3")

            if not business_cards:
                logger.info("No business cards found on this page")
                break

            logger.info(f"Found {len(business_cards)} businesses on page {page_num}")

            for i, card in enumerate(business_cards):
                try:
                    name = "NA"
                    name_link = card.find("a", href=lambda x: x and "profile.aspx" in str(x))
                    if name_link:
                        name = name_link.get_text(strip=True)

                    address = "NA"
                    address_div = card.find("address")
                    if address_div:
                        address = parse_and_format_address(address_div, city_name)

                    industry_val = extract_industry_from_card(card, city_name, name)

                    phone, website = await extract_phone_and_website_hybrid(page, card, i)

                    if not name or name == "NA" or len(name) < 2:
                        continue

                    # Format address to match working scrapers pattern: "Street, City, State"
                    if address and address != "NA":
                        # Replace trailing ", NA" with ", {state_full}" if present
                        if address.endswith(", NA"):
                            formatted_address = address[:-5] + f", {state_full}"
                        else:
                            formatted_address = f"{address}, {state_full}"
                    else:
                        formatted_address = f"{city_name}, {state_full}"

                    business_info = {
                        "Company": name,
                        "Industry": industry_val if industry_val != "NA" else industry.capitalize(),
                        "Address": formatted_address,
                        "State": state_full,
                        "Business_phone": phone,
                        "Website": website,
                        "BBB_rating": "NA"
                    }

                    yield business_info

                except Exception as e:
                    logger.error(f"Error processing business card {i+1}: {e}")
                    continue

            try:
                next_button = page.locator('#ctl00_hlNext')
                if await next_button.count() > 0 and await next_button.is_visible():
                    logger.info("Navigating to next page...")
                    await next_button.click()
                    await page.wait_for_load_state("domcontentloaded")
                    page_num += 1

                    if page_num > 50:
                        logger.warning("Reached maximum page limit")
                        break
                else:
                    logger.info("No next page button found - end of results")
                    break
            except Exception as e:
                logger.error(f"Error navigating to next page: {e}")
                break

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
    finally:
        if internal_page and page is not None:
            await page.close()

async def extract_phone_and_website_hybrid(page, card_soup, business_index):
    """
    Extract phone by clicking the business name link to access detail page.
    """
    phone = "NA"
    website = "NA"

    try:
        business_cards = page.locator('#dgBusinesses .bg-white.rounded.mb-2.mt-0.p-3')
        current_card = business_cards.nth(business_index)

        profile_link = current_card.locator('a[href*="profile.aspx"]').first
        if await profile_link.count() == 0:
            return phone, website

        await profile_link.click()
        await page.wait_for_load_state("domcontentloaded")

        try:
            phone_elements = await page.locator('[onclick*="logMaskedCall"]').all()
            for element in phone_elements:
                onclick_attr = await element.get_attribute('onclick')
                if onclick_attr:
                    phone_match = re.search(r"logMaskedCall\s*\([^,]+,\s*['\"]([^'\"]+)['\"]", onclick_attr)
                    if phone_match:
                        phone = phone_match.group(1).strip()
                        break
        except Exception as e:
            pass

        try:
            external_links = await page.locator('a[href^="http"]').all()
            reject_domains = ['showmelocal', 'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com', 'google.com']

            for link in external_links:
                href = await link.get_attribute('href')
                if href and not any(reject in href.lower() for reject in reject_domains):
                    website = href
                    break
        except Exception as e:
            pass

        await page.go_back()
        await page.wait_for_load_state("domcontentloaded")

    except Exception as e:
        try:
            await page.go_back()
            await page.wait_for_load_state("domcontentloaded")
        except:
            pass

    return phone, website

def extract_phone_from_soup(card_soup):
    """
    Extract phone number from BeautifulSoup card HTML using the onclick patterns
    shown in the images.
    """
    phone = "NA"
    
    try:
        phone_elements = card_soup.find_all(lambda tag: tag.name == 'a' and 
                                          tag.get('onclick') and 
                                          'logMaskedCall' in tag.get('onclick'))
        
        for element in phone_elements:
            onclick_attr = element.get('onclick')
            
            if onclick_attr:
                phone_patterns = [
                    r"logMaskedCall\s*\(\s*\$\(this\)\s*,\s*['\"]([^'\"]+)['\"]",
                    r"['\"](\d{3}\s+\d{4}\s+\d{4})['\"]",
                    r"['\"](\d{4}\s+\d{6})['\"]",
                    r"['\"](\d{5}\s+\d{6})['\"]",
                    r"['\"](\d{2}\s+\d{4}\s+\d{6})['\"]",
                    r"['\"]([+]?\d[\d\s\-]{8,14}\d)['\"]",
                ]
                
                for pattern in phone_patterns:
                    match = re.search(pattern, onclick_attr)
                    if match:
                        extracted_phone = match.group(1).strip()
                        if re.match(r'^[+]?\d[\d\s\-]{8,14}\d$', extracted_phone):
                            phone = extracted_phone
                            return phone
        
        if phone == "NA":
            all_onclick_elements = card_soup.find_all(lambda tag: tag.get('onclick'))
            for element in all_onclick_elements:
                onclick = element.get('onclick')
                if onclick and any(keyword in onclick.lower() for keyword in ['phone', 'call', 'tel']):
                    phone_match = re.search(r"['\"]([+]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{4,6})['\"]", onclick)
                    if phone_match:
                        phone = phone_match.group(1).strip()
                        break
                        
    except Exception as e:
        logger.error(f"Error extracting phone: {e}")
    
    return phone

def extract_website_from_soup(card_soup):
    """
    Extract website from BeautifulSoup card HTML.
    """
    website = "NA"
    
    try:
        external_links = card_soup.find_all("a", href=lambda x: x and x.startswith("http"))
        reject_domains = [
            'showmelocal', 'facebook.com', 'twitter.com', 'linkedin.com', 
            'instagram.com', 'google.com', 'bing.com', 'yahoo.com', 'mailto:',
            'leafletjs.com', 'openstreetmap.org', '.aspx', 'javascript:', 'tel:'
        ]
        
        for link in external_links:
            href = link.get('href')
            if href and not any(reject in href.lower() for reject in reject_domains):
                website = href
                break
                
    except Exception as e:
        logger.error(f"Error extracting website from soup: {e}")
    
    return website

async def extract_phone_and_website_with_playwright(page, business_index):
    """
    Fallback method using Playwright selectors for the specific business card.
    """
    phone = "NA"
    website = "NA"
    
    try:
        business_cards = page.locator('#dgBusinesses .bg-white.rounded.mb-2.mt-0.p-3')
        
        if await business_cards.count() > business_index:
            current_card = business_cards.nth(business_index)
            
            phone_button = current_card.locator('a[onclick*="logMaskedCall"]').first
            if await phone_button.count() > 0:
                onclick_attr = await phone_button.get_attribute('onclick')
                if onclick_attr:
                    phone_patterns = [
                        r"logMaskedCall\s*\(\s*\$\(this\)\s*,\s*['\"]([^'\"]+)['\"]",
                        r"['\"](\d{3}\s+\d{4}\s+\d{4})['\"]",
                        r"['\"](\d{4}\s+\d{6})['\"]",
                        r"['\"](\d{5}\s+\d{6})['\"]",
                        r"['\"](\d{2}\s+\d{4}\s+\d{6})['\"]",
                        r"['\"]([+]?\d[\d\s\-]{8,14}\d)['\"]",
                    ]
                    
                    for pattern in phone_patterns:
                        match = re.search(pattern, onclick_attr)
                        if match:
                            extracted_phone = match.group(1).strip()
                            if re.match(r'^[+]?\d[\d\s\-]{8,14}\d$', extracted_phone):
                                phone = extracted_phone
                                break

            external_links = current_card.locator('a[href^="http"]')
            reject_domains = [
                'showmelocal', 'facebook.com', 'twitter.com', 'linkedin.com', 
                'instagram.com', 'google.com', 'bing.com', 'yahoo.com', 'mailto:',
                'leafletjs.com', 'openstreetmap.org', '.aspx', 'javascript:', 'tel:'
            ]
            
            for i in range(await external_links.count()):
                link = external_links.nth(i)
                href = await link.get_attribute('href')
                if href and not any(reject in href.lower() for reject in reject_domains):
                    website = href
                    break
            
    except Exception as e:
        logger.error(f"Playwright extraction error: {e}")
    
    return phone, website

def extract_industry_from_card(card_soup, city, name):
    """
    Enhanced industry extraction based on the HTML structure shown in images.
    """
    industry = "NA"
    
    try:
        category_links = card_soup.find_all("a", href=lambda x: x and ("local_search.aspx" in str(x) or "construction-companies" in str(x)))
        
        for link in category_links:
            link_text = link.get_text(strip=True)
            href = link.get('href', '')
            
            if (link_text and 
                link_text.lower() != city.lower() and 
                link_text.lower() != name.lower() and
                len(link_text) > 2 and
                not link_text.isdigit() and
                link_text.lower() not in ['map', 'directions', 'website']):
                
                industry = link_text
                break
        
        if industry == "NA":
            for link in category_links:
                href = link.get('href', '')
                if 'construction-companies' in href:
                    industry = "Construction Companies"
                elif 'software-companies' in href:
                    industry = "Software Companies"
                elif 'restaurants' in href:
                    industry = "Restaurants"
                    
        if industry == "NA":
            category_elements = card_soup.find_all(['span', 'div'], class_=lambda x: x and ('category' in str(x) or 'industry' in str(x)))
            for element in category_elements:
                text = element.get_text(strip=True)
                if text and len(text) > 2:
                    industry = text
                    break
                    
    except Exception as e:
        logger.error(f"Error extracting industry: {e}")
    
    return industry

def parse_and_format_address(address_element, city):
    """
    Parse and format address to: <Street>, <City>, NA
    Properly handles the HTML structure with <br> tags
    """
    if not address_element:
        return "NA"
    
    try:
        # Get all text nodes and br-separated parts
        parts = []
        
        # Handle the HTML structure properly - split by <br> tags
        for element in address_element.children:
            if element.name == 'br':
                continue
            elif hasattr(element, 'strip'):  # Text node
                text = element.strip()
                if text:
                    parts.append(text)
            else:  # Other elements
                text = element.get_text(strip=True)
                if text:
                    parts.append(text)
        
        # If no parts found, fallback to getting all text
        if not parts:
            parts = [part.strip() for part in address_element.get_text(separator='|').split('|') if part.strip()]
        
        if not parts:
            return "NA"
        
        # Clean each part
        clean_parts = []
        for part in parts:
            # Remove UK postcodes
            part = re.sub(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b', '', part)
            part = re.sub(r'\s+', ' ', part.strip())
            if part:
                clean_parts.append(part)
        
        if not clean_parts:
            return "NA"
        
        # The first part is typically the street
        street = clean_parts[0]
        
        # Remove any city duplicates from the street if they got concatenated
        city_lower = city.lower()
        street_lower = street.lower()
        
        if city_lower in street_lower and not street_lower.endswith(' ' + city_lower):
            # Find the last occurrence of city name and split there
            city_index = street_lower.rfind(city_lower)
            if city_index > 0:
                street = street[:city_index].strip()
        
        # Format as: Street, City, NA
        formatted_address = f"{street}, {city.title()}, NA"
        
        return formatted_address
        
    except Exception as e:
        logger.error(f"Error formatting address: {e}")
        return f"NA, {city.title()}, NA"
    
async def main():
    parser = argparse.ArgumentParser(description="Scrape business listings from ShowMeLocal UK by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'construction'")
    parser.add_argument("city", help="City to search in, e.g. 'london'")
    args = parser.parse_args()
    
    city = args.city.split(",")[0].strip()
    logger.info(f"Searching for {args.industry} businesses in {city}...")
    count = 0
    async for biz in scrape_showmelocal_businesses(args.industry, city):
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