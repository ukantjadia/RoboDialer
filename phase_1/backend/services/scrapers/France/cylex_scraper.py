import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
import argparse
import time
import urllib.parse
import random
import json
import asyncio
from bs4 import BeautifulSoup
from typing import Any, AsyncGenerator, Dict
import logging
from backend.config.logger_config import setup_logger
from backend.services.helper.flaresolverr_cookies import get_solved_page

setup_logger()
logger = logging.getLogger("Cylex France Scraper")

async def scrape_cylex_businesses(
    industry: str,
    location: str,
    max_pages: int = 5
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Scrapes business listings from Cylex France using FlareSolverr to handle Cloudflare.
    
    Args:
        industry: Industry to search for (e.g., "software")
        location: Location in format "Paris,France,FRA" (will extract city name)
        max_pages: Maximum number of pages to scrape
    """
    try:
        # Extract city name from location (e.g., "Paris,France,FRA" -> "paris")
        cookies = []
        location_parts = location.split(",")
        city_name = location_parts[0].strip().lower()
        
        # URL encode parameters
        industry_slug = urllib.parse.quote_plus(industry)
        city_slug = urllib.parse.quote_plus(city_name)
        
        page_num = 1
        
        while page_num <= max_pages:
            # Construct search URL for current page
            current_url = f"https://www.cylex-locale.fr/s?q={industry_slug}&c={city_slug}&z=&p={page_num}&dst=&sUrl=&cUrl="
            
            logger.info(f"Scraping page {page_num}: {current_url}")
            
            # Use FlareSolverr to get the page content
            solution = await get_solved_page(current_url, cookies=cookies)
            if not solution:
                logger.warning(f"Failed to get content for page {page_num}. Ending scrape.")
                break
            
            # Validate that we have actual HTML content
            if not solution.get("response") or solution["response"] is None:
                logger.warning(f"FlareSolverr returned empty response for page {page_num}. Response: {solution}")
                break
            
            # Store cookies for subsequent requests
            if len(cookies) == 0:
                cookies = solution["cookies"]

            try:
                soup = BeautifulSoup(solution["response"], "html.parser")
            except TypeError as e:
                logger.error(f"Failed to parse HTML content on page {page_num}: {e}")
                logger.error(f"Response type: {type(solution['response'])}, Content preview: {str(solution['response'])[:200]}")
                break
            
            # Find business cards using the specified selector
            business_cards = soup.select("div.lm-comp.position-relative.basic.text-dark")
            
            if not business_cards:
                logger.info(f"No business cards found on page {page_num}. Ending scrape.")
                break

            logger.info(f"Found {len(business_cards)} listings on page {page_num}.")

            # Process each business card
            for card in business_cards:
                try:
                    # Extract the detail page URL from onclick attribute
                    onclick_attr = card.get("onclick", "")
                    if not onclick_attr or "location.href=" not in onclick_attr:
                        logger.warning("No detail page URL found for business card")
                        continue
                    
                    # Parse the URL from onclick="location.href='URL'"
                    start_idx = onclick_attr.find("location.href='") + len("location.href='")
                    end_idx = onclick_attr.find("'", start_idx)
                    detail_url = onclick_attr[start_idx:end_idx]
                    
                    if not detail_url.startswith("http"):
                        detail_url = "https://www.cylex-locale.fr" + detail_url
                    
                    logger.info(f"Fetching details from: {detail_url}")
                    
                    # Get the detail page using FlareSolverr
                    detail_solution = await get_solved_page(detail_url, cookies=cookies)
                    if not detail_solution:
                        logger.warning(f"Failed to get detail page content: {detail_url}")
                        continue
                    
                    # Validate detail page response
                    if not detail_solution.get("response") or detail_solution["response"] is None:
                        logger.warning(f"FlareSolverr returned empty response for detail page: {detail_url}")
                        continue
                    
                    try:
                        detail_soup = BeautifulSoup(detail_solution["response"], "html.parser")
                    except TypeError as e:
                        logger.error(f"Failed to parse detail page HTML: {e}")
                        logger.error(f"Detail response type: {type(detail_solution['response'])}")
                        continue
                    
                    # Extract business name from <span class="bold dont-break-out">
                    name_tag = detail_soup.select_one("span.bold.dont-break-out")
                    if name_tag:
                        name = name_tag.get_text(strip=True).split(",")[0]  # Take first part before comma
                    else:
                        name = "NA"
                    
                    # Extract street address from <div id="cp-street">
                    street_div = detail_soup.select_one("div#cp-street")
                    if street_div:
                        # Get the first line of text, skip other lines
                        street_text = street_div.get_text(strip=True).split('\n')[0]
                        # Take only the street address (first part before comma)
                        street_part = street_text.split(',')[0].strip()
                        # Combine with location parts for full address
                        if len(location_parts) >= 2:
                            address = f"{street_part}, {location_parts[0]}, {location_parts[1]}"
                        else:
                            address = f"{street_part}, {location_parts[0]}"
                    else:
                        address = "NA"
                    
                    # Extract phone number from <div class="contact-data d-inline-block"> <a class="text-underline">
                    phone = "NA"
                    contact_div = detail_soup.select_one("div.contact-data.d-inline-block")
                    if contact_div:
                        phone_link = contact_div.select_one("a.text-underline")
                        if phone_link:
                            phone = phone_link.get_text(strip=True)
                    
                    # Extract website from <a id="font-base text-underline"> or similar pattern
                    website = "NA"
                    # Try multiple selectors for website links
                    website_selectors = [
                        "a.font-base.text-underline",
                        "a[href*='http']:not([href*='tel:']):not([href*='mailto:'])"
                    ]
                    
                    for selector in website_selectors:
                        website_link = detail_soup.select_one(selector)
                        if website_link and website_link.get("href"):
                            href = website_link.get("href")
                            # Make sure it's an external website, not internal cylex link
                            if not href.startswith("https://www.cylex-locale.fr"):
                                website = href
                                break
                    
                    # Skip businesses with insufficient data (all critical fields are NA)
                    if address == "NA" and phone == "NA" and website == "NA":
                        logger.warning(f"Skipping business '{name}' - insufficient data (no address, phone, or website)")
                        continue
                    
                    # Industry classification - try to extract from the detail page
                    industry_classification = industry.capitalize()  # Default to search term
                    
                    # Yield the business data with exact field names for frontend compatibility
                    yield {
                        "Company": name,
                        "Industry": industry_classification,
                        "Address": address,
                        "Business_phone": phone,
                        "Website": website,
                        "BBB_rating": "NA"
                    }
                    
                    # Add a small delay between detail page requests
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                except Exception as e:
                    logger.error(f"Error processing business card: {e}")
                    continue
            
            # Check if we've reached the last page by trying to go to next page
            # Cylex will redirect back to last valid page if we exceed limit
            next_page_num = page_num + 1
            test_url = f"https://www.cylex-locale.fr/s?q={industry_slug}&c={city_slug}&z=&p={next_page_num}&dst=&sUrl=&cUrl="
            
            # Test if next page exists by checking URL pattern
            test_solution = await get_solved_page(test_url, cookies=cookies)
            if test_solution:
                # Validate test page response before parsing
                if not test_solution.get("response") or test_solution["response"] is None:
                    logger.info(f"No more pages found after page {page_num} (empty response). Ending scrape.")
                    break
                
                try:
                    test_soup = BeautifulSoup(test_solution["response"], "html.parser")
                except TypeError as e:
                    logger.warning(f"Failed to parse test page HTML: {e}")
                    break
                
                test_cards = test_soup.select("div.lm-comp.position-relative.basic.text-dark")
                
                if not test_cards:
                    logger.info(f"No more pages found after page {page_num}. Ending scrape.")
                    break
                
                # If we got redirected back to same page, we've hit the limit
                current_page_indicator = test_soup.select_one("span.pagination-current")
                if current_page_indicator and str(page_num) in current_page_indicator.get_text():
                    logger.info(f"Reached maximum available pages at page {page_num}. Ending scrape.")
                    break
            
            page_num += 1
            
            # Add delay between pages
            await asyncio.sleep(random.uniform(1, 2))
                
    except Exception as e:
        logger.error(f"An unexpected error occurred during scraping: {e}", exc_info=True)

async def main_test():
    """A standalone test function for the Cylex scraper."""
    industry_to_test = "software"
    location_to_test = "Paris,France,FRA"
    
    logger.info(f"--- Testing Cylex.fr Scraper for '{industry_to_test}' in '{location_to_test}' ---")
    start_time = time.time()
    results = []

    async for record in scrape_cylex_businesses(industry_to_test, location_to_test, max_pages=2):
        results.append(record)
        logger.info(f"  [+] Yielded: {record.get('Company')}")

    end_time = time.time()
    logger.info("\n--- Test Summary ---")
    logger.info(f"Scraped a total of {len(results)} business listings.")
    logger.info(f"Total execution time: {end_time - start_time:.2f} seconds.")
    if results:
        import pprint
        logger.info("\n--- Sample Results ---")
        pprint.pprint(results[:5])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape business listings from Cylex France by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'software'")
    parser.add_argument("location", help="Location in format 'Paris,France,FRA'")
    args = parser.parse_args()

    logger.info(f"Searching for {args.industry} businesses in {args.location}...")
    async def main():
        count = 0
        async for biz in scrape_cylex_businesses(args.industry, args.location):
            count += 1
            logger.info(f"{count}. {biz['Company']}")
            logger.info(f"   Industry: {biz['Industry']}")
            logger.info(f"   Address: {biz['Address']}")
            logger.info(f"   Phone: {biz['Business_phone']}")
            logger.info(f"   Website: {biz['Website']}")
            logger.info("-" * 40)
        logger.info(f"\nFound {count} businesses total")
    asyncio.run(main())