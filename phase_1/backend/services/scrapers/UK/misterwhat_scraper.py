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
logger = logging.getLogger("MisterWhat UK")

async def scrape_misterwhat_businesses(industry: str, city: str, page=None, max_timeout=10.0):
    """
    Scrape business listings from MisterWhat.co.uk by industry and city.
    Yields each business as it is scraped.
    If page is not provided, a new browser tab will be created.
    """
    base_url = "https://www.misterwhat.co.uk/search"
    industry_encoded = urllib.parse.quote(industry.upper())
    
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
    city_encoded = urllib.parse.quote(city_name.upper())

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
                current_url = f"{base_url}?what={industry_encoded}&where={city_encoded}"
            else:
                current_url = f"{base_url}?what={industry_encoded}&where={city_encoded}&page={page_num}"

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

                page_text = soup.get_text()
                if "Sorry, no companies found" in page_text:
                    logger.info("No more results found")
                    break

                listwrapper = soup.find("div", class_="listwrapper")
                if not listwrapper:
                    logger.info("No listwrapper found - end of results")
                    break

                business_cards = listwrapper.find_all("div", class_="box nopadding")
                if not business_cards:
                    logger.info("No business cards found - end of results")
                    break

                logger.info(f"Found {len(business_cards)} businesses on page {page_num}")

                for i, card in enumerate(business_cards):
                    try:
                        comp_name_link = card.find("a", class_="compName")
                        if not comp_name_link:
                            continue

                        name = comp_name_link.get_text(strip=True)
                        detail_url = comp_name_link.get("href", "")

                        if not name or not detail_url:
                            continue

                        if detail_url.startswith("/"):
                            detail_url = "https://www.misterwhat.co.uk" + detail_url

                        name = re.sub(r'\s+', ' ', name).strip()
                        if len(name) < 2:
                            continue

                        address, phone, website, _ = await scrape_business_details(page, detail_url, city_name)

                        cleaned_street = address.replace(",", "").strip()
                        if cleaned_street:
                            full_address = f"{cleaned_street}, {city_name.capitalize()}, {state_full}"
                        else:
                            full_address = f"{city_name.capitalize()}, {state_full}"

                        business_info = {
                            "Company": name,
                            "Industry": industry.capitalize(),
                            "Address": full_address if full_address and full_address != "NA" else "NA",
                            "State": state_full,
                            "Business_phone": phone,
                            "Website": website,
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
        if internal_page and page is not None:
            await page.close()

async def scrape_business_details(page, detail_url, city):
    """
    Scrape address, phone, website, and industry from business detail page.
    """
    address = "NA"
    phone = "NA"
    website = "NA"
    industry_val = "NA"
    
    try:
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=15000)
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # Extract address from structured data
        try:
            address_span = soup.find("span", {"itemprop": "streetAddress"})
            if address_span:
                address = address_span.get_text(strip=True)
            else:
                # Try alternative selector for address
                address_div = soup.find("div", {"itemprop": "address"})
                if address_div:
                    address = address_div.get_text(strip=True)
                    # Clean up address
                    address = re.sub(r'\s+', ' ', address).strip()
        except Exception:
            pass
        
        # Extract phone number
        try:
            phone_span = soup.find("span", {"itemprop": "telephone"})
            if phone_span:
                phone = phone_span.get_text(strip=True)
            else:
                # Try to find phone number in text
                phone_pattern = r'(\+44\s?\d{1,4}\s?\d{3,4}\s?\d{3,4}|\d{3,5}\s?\d{3,4}\s?\d{3,4}|0\d{2,4}\s?\d{3,4}\s?\d{3,4})'
                page_text = soup.get_text()
                phone_match = re.search(phone_pattern, page_text)
                if phone_match:
                    phone = phone_match.group(1).strip()
        except Exception:
            pass
        
        # Extract website
        try:
            # Look for website link
            website_link = soup.find("a", {"href": re.compile(r'https?://(?!.*misterwhat\.co\.uk).*')})
            if website_link:
                website_candidate = website_link.get("href", "")
                # Exclude Google Maps links
                if website_candidate.startswith("https://www.google.com/maps"):
                    website = "NA"
                else:
                    website = website_candidate
            else:
                # Try to find website in text
                website_pattern = r'https?://(?!.*misterwhat\.co\.uk)[^\s<>"\']+|www\.(?!misterwhat\.co\.uk)[^\s<>"\']+\.[a-zA-Z]{2,}'
                page_text = soup.get_text()
                website_match = re.search(website_pattern, page_text)
                if website_match:
                    website_candidate = website_match.group(0).strip()
                    if not website_candidate.startswith('http'):
                        website_candidate = 'https://' + website_candidate
                    # Exclude Google Maps links
                    if website_candidate.startswith("https://www.google.com/maps"):
                        website = "NA"
                    else:
                        website = website_candidate
        except Exception:
            pass
        
        # Extract industry/business type
        try:
            # Look for category links within the col-sm-9 div
            col_sm_9_div = soup.find("div", class_="col-sm-9")
            if col_sm_9_div:
                category_link = col_sm_9_div.find("a", {"data-skpa": "1"})
                if category_link:
                    industry_text = category_link.get_text(strip=True)
                    
                    # Remove "in [City]" suffix if present
                    industry_text = re.sub(rf'\s+in\s+{re.escape(city)}\s*$', '', industry_text, flags=re.IGNORECASE)
                    
                    # Clean up industry text
                    industry_text = re.sub(r'\s+', ' ', industry_text).strip()
                    if industry_text and len(industry_text) > 2:
                        industry_val = industry_text
            
            # If no industry found with col-sm-9, try other methods
            if industry_val == "NA":
                # Look for category in div with class "category"
                category_div = soup.find("div", class_="category")
                if category_div:
                    category_text = category_div.get_text(strip=True)
                    # Remove "in [City]" suffix if present
                    category_text = re.sub(rf'\s+in\s+{re.escape(city)}\s*$', '', category_text, flags=re.IGNORECASE)
                    
                    # Clean up category text
                    category_text = re.sub(r'\s+', ' ', category_text).strip()
                    if category_text and len(category_text) > 2:
                        industry_val = category_text
        except Exception:
            pass
        
    except Exception as e:
        logger.error(f"Error scraping details from {detail_url}: {e}")
    
    return address, phone, website, industry_val

async def main():
    parser = argparse.ArgumentParser(description="Scrape business listings from MisterWhat.co.uk by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'software'")
    parser.add_argument("city", help="City to search in, e.g. 'london'")
    args = parser.parse_args()

    city = args.city.split(",")[0].strip()
    logger.info(f"{city}")
    logger.info(f"Searching for {args.industry} businesses in {city}...")
    count = 0
    async for biz in scrape_misterwhat_businesses(args.industry, city, max_timeout=10.0):
        count += 1
        # logger.info(f"{count}. {biz['Company']}")
        # logger.info(f"   Industry: {biz['Industry']}")
        # logger.info(f"   Address: {biz['Street']}, {biz['City']}")
        # logger.info(f"   Phone: {biz['Business_phone']}")
        # logger.info(f"   Website: {biz['Website']}")
        # logger.info(f"   BBB Rating: {biz['BBB_rating']}")
        # logger.info("-" * 40)
    logger.info(f"\nFound {count} businesses total:")
    # logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())