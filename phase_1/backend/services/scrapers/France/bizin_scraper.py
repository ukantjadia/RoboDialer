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
from backend.config.logger_config import setup_logger

setup_logger()
logger = logging.getLogger("Bizin FR")

async def scrape_bizin_businesses(industry: str, city: str, page=None):
    """
    Scrape business listings from fr.bizin.eu by industry and city.
    Yields each business as it is scraped.
    If page is not provided, a new browser tab will be created.
    """
    base_url = "https://fr.bizin.eu/eng/search/all"
    industry_encoded = urllib.parse.quote(industry)
    
    # Extract city and state from location string, e.g. "Paris,France,FRA"
    city_parts = city.split(",")
    city_name = city_parts[0].strip()
    state_name = city_parts[1].strip() if len(city_parts) > 1 else "France"
    country_code = "fr"
    
    # Use the state name directly from the input
    state_full = state_name
    city_encoded = urllib.parse.quote(city_name)

    manager = None
    internal_page = False
    if page is None:
        manager = PlaywrightManager(headless=True)
        page = await manager.start_browser(stealth_on=True)
        internal_page = True

    page_num = 1
    visited_urls = set()

    try:
        while True:
            if page_num == 1:
                current_url = f"{base_url}?what={industry_encoded}&where={city_encoded}&country={country_code}&lang=eng"
            else:
                current_url = f"{base_url}?p={page_num}&what={industry_encoded}&where={city_encoded}&country={country_code}&lang=eng"

            logger.info(f"Scraping page {page_num}...")
            logger.info(f"URL: {current_url}")
            
            if current_url in visited_urls:
                logger.warning("Already visited this URL - avoiding infinite loop")
                break
            visited_urls.add(current_url)

            try:
                await page.goto(current_url, wait_until="domcontentloaded", timeout=60000)
                
                content = await page.content()
                if not content:
                    page_num += 1
                    continue

                soup = BeautifulSoup(content, "html.parser")

                # Check for no results
                page_text = soup.get_text()
                if "No results found" in page_text or "Aucun résultat" in page_text:
                    logger.info("No more results found")
                    break

                # Find all containers with span8 organization_list
                all_containers = soup.find_all("div", class_="span8 organization_list")
                
                # We need the SECOND container - if there's only one, we're done
                if len(all_containers) < 2:
                    logger.info("Only one or no span8 organization_list found - end of results")
                    break
                
                # Use the second container (index 1)
                main_container = all_containers[1]

                # Find business containers ONLY within the main container
                business_cards = main_container.find_all("div", class_="row-fluid organization")
                if not business_cards:
                    logger.info("No business cards found - end of results")
                    break

                logger.info(f"Found {len(business_cards)} businesses on page {page_num}")

                for i, card in enumerate(business_cards):
                    try:
                        # Extract company name
                        name = ""
                        name_element = card.find("h2")
                        if name_element:
                            name_link = name_element.find("a")
                            if name_link:
                                name_span = name_link.find("span", {"itemprop": "name"})
                                if name_span:
                                    name = name_span.get_text(strip=True)

                        if not name or len(name) < 2:
                            continue

                        # Clean name
                        name = re.sub(r'\s+', ' ', name).strip()

                        # Extract address components
                        address_parts = []
                        street = ""
                        postal_code = ""
                        locality = ""
                        
                        # Find address list
                        address_ul = card.find("ul")
                        if address_ul:
                            address_li = address_ul.find("li", {"itemprop": "address"})
                            if address_li:
                                # Extract street address
                                street_span = address_li.find("span", {"itemprop": "streetAddress"})
                                if street_span:
                                    street = street_span.get_text(strip=True)
                                
                                # Extract postal code
                                postal_span = address_li.find("span", {"itemprop": "postalCode"})
                                if postal_span:
                                    postal_code = postal_span.get_text(strip=True)
                                
                                # Extract locality (city)
                                locality_span = address_li.find("span", {"itemprop": "addressLocality"})
                                if locality_span:
                                    locality = locality_span.get_text(strip=True)

                        # Build full address
                        if street:
                            if postal_code and locality:
                                full_address = f"{street}, {postal_code} {locality}, {state_full}"
                            elif locality:
                                full_address = f"{street}, {locality}, {state_full}"
                            else:
                                full_address = f"{street}, {city_name.title()}, {state_full}"
                        else:
                            full_address = f"{city_name.title()}, {state_full}"

                        # Extract phone number
                        # Extract phone number - FIXED
                        phone = "NA"
                        if address_ul:
                            # Look for any li containing a telephone span
                            phone_span = address_ul.find("span", {"itemprop": "telephone"})
                            if phone_span:
                                phone = phone_span.get_text(strip=True)
                                # Clean up the phone number
                                phone = re.sub(r'\s+', ' ', phone).strip()
                            else:
                                # Alternative: look for li with icon-volume-up class containing phone span
                                phone_li = address_ul.find("li", class_="icon-volume-up")
                                if phone_li:
                                    phone_span = phone_li.find("span", {"itemprop": "telephone"})
                                    if phone_span:
                                        phone = phone_span.get_text(strip=True)
                                        phone = re.sub(r'\s+', ' ', phone).strip()
                                        
                        # Extract website
                        website = "NA"
                        website_div = card.find("div", class_="url")
                        if website_div:
                            website_link = website_div.find("a", {"rel": "nofollow"})
                            if website_link:
                                href = website_link.get("href", "")
                                if href and not href.startswith("mailto:"):
                                    website = href

                        industry_val = industry.capitalize()

                        business_info = {
                            "Company": name,
                            "Industry": industry_val,
                            "Street": street,
                            "City": locality if locality else city_name.title(),
                            "State": state_full,
                            "Address": full_address,  # Include both formats
                            "Business_phone": phone,
                            "Website": website,
                            "BBB_rating": "NA"
                        }

                        yield business_info

                    except Exception as e:
                        logger.error(f"Error processing business card {i+1}: {e}")
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
    parser = argparse.ArgumentParser(description="Scrape business listings from fr.bizin.eu by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'software'")
    parser.add_argument("city", help="City to search in, e.g. 'Paris'")
    args = parser.parse_args()

    city = args.city.split(",")[0].strip()
    logger.info(f"Searching for {args.industry} businesses in {city}...")
    count = 0
    async for biz in scrape_bizin_businesses(args.industry, args.city):
        count += 1

    logger.info(f"\nFound {count} businesses total:")

if __name__ == "__main__":
    asyncio.run(main())