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
from backend.config.browser_config import PlaywrightManager
import logging
from backend.config.logger_config import setup_logger
from backend.services.helper.flaresolverr_cookies import get_solved_page

setup_logger()
logger = logging.getLogger("Yell UK Scraper")

async def new_scrape_yell_businesses(
    industry: str,
    location: str,
    max_pages: int = 5
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Scrapes business listings from Yell UK using FlareSolverr to handle Cloudflare.
    This version does not use Playwright.
    """
    try:
        # Construct the initial search URL
        cookies = []
        location_parts = location.split(",")
        location_slug = urllib.parse.quote_plus(location_parts[0].strip())
        industry_slug = urllib.parse.quote_plus(industry)
        current_url = f"https://www.yell.com/ucs/UcsSearchAction.do?keywords={industry_slug}&location={location_slug}"
        
        page_num = 1
        while page_num <= max_pages:
            logger.info(f"Scraping page {page_num}: {current_url}")
            
            # Use FlareSolverr to get the page content
            solution = await get_solved_page(current_url, cookies=cookies)
            if not solution:
                logger.warning(f"Failed to get content for page {page_num}. Ending scrape.")
                break
            
            if len(cookies) == 0:
                cookies = solution["cookies"]

            soup = BeautifulSoup(solution["response"], "html.parser")
            
            business_cards = soup.select("div.row.businessCapsule--mainRow")
            if not business_cards:
                with open("output_prettified_html.txt", "w", encoding="utf-8") as file:
                    file.write(soup.prettify())
                logger.info(f"No business cards found on page {page_num}. Ending scrape.")
                break

            logger.info(f"Found {len(business_cards)} listings on page {page_num}.")

            # The data extraction logic remains the same, using BeautifulSoup
            for card in business_cards:
                name_tag = card.select_one("h2.businessCapsule--name")
                name = name_tag.get_text(strip=True) if name_tag else "NA"

                class_tags = card.select("span.businessCapsule--classification")
                classifications = ", ".join([tag.get_text(strip=True) for tag in class_tags]) or "NA"

                address_parts = []
                street_address = card.find("span", attrs={"itemprop": "addressLocality"})
                if street_address:
                    address_parts.append(street_address.get_text(strip=True))
                
                city = card.find("span", attrs={"itemprop": "addressLocality"})
                if city:
                    address_parts.append(city.get_text(strip=True))
                
                address = ", ".join(address_parts + ['']) or "NA" 

                phone_tag = card.select_one("span.business--telephoneNumber")
                phone = phone_tag.get_text(strip=True) if phone_tag else "NA"

                website_tag = card.select_one("a.btn-yellow[data-test='localBusiness--website']")
                website = website_tag.get("href") if website_tag else "NA"

                yield {
                    "Company": name,
                    "Industry": classifications,
                    "Address": address,
                    "Business_phone": phone,
                    "Website": website,
                    "BBB_rating": "NA"
                }

            # Find the next page link to continue pagination
            next_page_link = soup.select_one("a.pagination--next")
            if next_page_link and next_page_link.get("href"):
                current_url = "https://www.yell.com" + next_page_link["href"]
                page_num += 1
            else:
                logger.info("No 'Next' page link found. Scrape complete.")
                break
                
    except Exception as e:
        logger.error(f"An unexpected error occurred during scraping: {e}", exc_info=True)

async def scrape_yell_businesses(industry: str, location: str, page=None):
    """
    Scrape business listings from Yell UK by industry and city.
    Uses the proper user flow instead of direct API calls.
    Streams results using yield.
    If page is not provided, a new browser tab will be created.
    """
    manager = None
    internal_page = False
    if page is None:
        manager = PlaywrightManager(headless=True)
        page = await manager.start_browser(stealth_on=True)
        internal_page = True
    try:
        logger.info("Step 1: Loading Yell homepage...")
        # First, load the homepage to establish session
        await page.goto("https://www.yell.com", wait_until="domcontentloaded", timeout=30000)
        
        # Wait for the page to fully load
        await page.wait_for_timeout(random.uniform(1000, 2000))  # 1-2s delay

        logger.info("Step 2: Performing search using the search form...")
        # Use the search form instead of direct URL manipulation
        try:
            # Use correct selectors for search inputs and button
            business_input = page.locator('#search_keyword').first
            location_input = page.locator('#search_location').first

            await business_input.clear()
            await location_input.clear()
            await business_input.type(industry.capitalize())  # Type instantly, no delay
            await location_input.type(location.split(",")[0].strip())  # Type instantly, no delay

            # Submit the search using the correct button
            search_button = page.locator('button.searchBar--submit.btn.btn-big.btn-black.btn-fullWidth').first
            await search_button.click()
            
            # Wait for search results to load
            await page.wait_for_url("**/ucs/UcsSearchAction.do**", timeout=30000)
            
        except Exception as e:
            logger.error(f"Search form approach failed: {e}")
            logger.info("Trying alternative URL approach...")
            
            # Fallback: try the simpler search URL format
            search_url = f"https://www.yell.com/s/services-{urllib.parse.quote(industry)}-{urllib.parse.quote(location.split(',')[0].strip())}.html"
            logger.info(f"Trying URL: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        
        page_num = 1
        
        while True:
            # logger.info(f"Processing page {page_num}...")
            
            # Wait for content to load
            await page.wait_for_timeout(5000)
            
            # Check for Cloudflare verification
            cloudflare_selectors = [
                "text=Verify you are human",
                "text=www.yell.com needs to review the security",
                ".cf-browser-verification",
                "#cf-challenge-running",
                "text=Checking if the site connection is secure"
            ]
            
            verification_detected = False
            for selector in cloudflare_selectors:
                if await page.locator(selector).count() > 0:
                    verification_detected = True
                    break
            
            if verification_detected:
                logger.info("Cloudflare verification detected. Waiting...")
                try:
                    await page.wait_for_timeout(15000)  # Wait 15 seconds for verification
                except:
                    logger.warning("Verification may have failed. Continuing...")
            
            soup = BeautifulSoup(await page.content(), "html.parser")
            
            # Try multiple selectors for business listings
            business_cards = []
            
            # Try different possible selectors
            selectors_to_try = [
                "article.businessCapsule",
                "div.businessCapsule",
                "article[class*='businessCapsule']",
                "div[class*='businessCapsule']",
                "article.col-sm-24",
                "div.searchResultsCard",
                "div.organic-result"
            ]
            
            for selector in selectors_to_try:
                if selector.startswith("article"):
                    business_cards = soup.find_all("article", class_=selector.split(".", 1)[1])
                else:
                    business_cards = soup.find_all("div", class_=selector.split(".", 1)[1])
                
                if business_cards:
                    logger.info(f"Found {len(business_cards)} businesses using selector: {selector}")
                    break
            
            if not business_cards:
                # logger.info("No business cards found with any selector")
                # logger.info("Page content preview:")
                # logger.info(soup.get_text()[:500] + "...")
                break
            
            # Process each business card
            for i, card in enumerate(business_cards):
                try:
                    # Extract business name - try multiple selectors
                    name = "NA"
                    name_selectors = [
                        "h2.businessCapsule--name",
                        "h3.businessCapsule--name", 
                        "h2[class*='name']",
                        "h3[class*='name']",
                        "a[class*='name']"
                    ]
                    
                    for name_sel in name_selectors:
                        name_tag = card.find(name_sel.split("[")[0], class_=name_sel.split(".", 1)[1] if "." in name_sel else None)
                        if name_tag:
                            name = name_tag.get_text(strip=True)
                            break
                    
                    # Extract industry/classification
                    industry_val = "NA"
                    industry_selectors = [
                        "span.businessCapsule--classification",
                        "span[class*='classification']",
                        "div[class*='classification']"
                    ]
                    
                    for industry_sel in industry_selectors:
                        industry_tags = card.find_all(industry_sel.split("[")[0], class_=industry_sel.split(".", 1)[1] if "." in industry_sel else None)
                        if industry_tags:
                            industries = [tag.get_text(strip=True) for tag in industry_tags if tag.get_text(strip=True)]
                            if industries:
                                industry_val = ", ".join(industries)
                                break
                    
                    # Extract address
                    address = "NA"
                    address_container = card.find("span", attrs={"itemprop": "address"}) or card.find("div", attrs={"itemprop": "address"})
                    if address_container:
                        address_parts = []
                        street_address = address_container.find("span", attrs={"itemprop": "streetAddress"})
                        locality = address_container.find("span", attrs={"itemprop": "addressLocality"})
                        postal_code = address_container.find("span", attrs={"itemprop": "postalCode"})
                        
                        if street_address:
                            address_parts.append(street_address.get_text(strip=True))
                        if locality:
                            address_parts.append(locality.get_text(strip=True))
                        if postal_code:
                            address_parts.append(postal_code.get_text(strip=True))
                        
                        if address_parts:
                            address = ", ".join(address_parts)
                    
                    # Extract phone number
                    phone = "NA"
                    phone_selectors = [
                        "span.business--telephoneNumber",
                        "span[class*='telephone']",
                        "a[href^='tel:']"
                    ]
                    
                    for phone_sel in phone_selectors:
                        if phone_sel.startswith("a[href"):
                            phone_tag = card.find("a", href=lambda x: x and x.startswith("tel:"))
                            if phone_tag:
                                phone = phone_tag.get_text(strip=True)
                                break
                        else:
                            phone_tag = card.find("span", class_=phone_sel.split(".", 1)[1] if "." in phone_sel else None)
                            if phone_tag:
                                phone = phone_tag.get_text(strip=True)
                                break
                    
                    # Extract website
                    website = "NA"
                    website_selectors = [
                        "a.btn-yellow",
                        "a[class*='cta']",
                        "a[href*='http']"
                    ]
                    
                    for website_sel in website_selectors:
                        if "[href*=" in website_sel:
                            website_tag = card.find("a", href=lambda x: x and "http" in x)
                        else:
                            website_tag = card.find("a", class_=website_sel.split(".", 1)[1] if "." in website_sel else None)
                        
                        if website_tag and website_tag.get("href"):
                            website = website_tag.get("href")
                            break
                    
                    business_info = {
                        "name": name,
                        "industry": industry_val,
                        "address": address,
                        "phone": phone,
                        "website": website,
                        "bbb_rating": "NA"
                    }
                    
                    # logger.info(f"{i+1}. {business_info['name']}")
                    # logger.info(f"   Industry: {business_info['industry']}")
                    # logger.info(f"   Address: {business_info['address']}")
                    # logger.info(f"   Phone: {business_info['phone']}")
                    # logger.info(f"   Website: {business_info['website']}")
                    # logger.info("-" * 40)
                    
                    yield business_info

                except Exception as e:
                    logger.error(f"Error processing business card {i+1}: {e}")
                    continue
            
            # Look for next page
            next_page_link = soup.find("a", {"aria-label": "Next page"}) or soup.find("a", string="Next")
            if next_page_link and next_page_link.get("href"):
                next_url = next_page_link.get("href")
                if next_url.startswith("/"):
                    next_url = "https://www.yell.com" + next_url
                
                # logger.info(f"Going to next page: {next_url}")
                await page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
                page_num += 1
                
                # Safety limit
                if page_num > 10:  # Reduced for testing
                    logger.warning("Reached page limit")
                    break
            else:
                logger.info("No next page found")
                break
                
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        # logger.info(f"Current page URL: {page.url}")
        # # Save page content for debugging
        # with open("debug_page.html", "w", encoding="utf-8") as f:
        #     f.write(await page.content())
        # logger.info("Page content saved to debug_page.html for analysis")
    finally:
        if internal_page and page is not None:
            await manager.stop_browser()

async def main_test():
    """A standalone test function for the Yell scraper."""
    industry_to_test = "plumbers"
    location_to_test = "London, England, UK"
    
    logger.info(f"--- Testing Yell.com Scraper for '{industry_to_test}' in '{location_to_test}' ---")
    start_time = time.time()
    results = []

    async for record in new_scrape_yell_businesses(industry_to_test, location_to_test, max_pages=2):
        results.append(record)
        logger.info(f"  [+] Yielded: {record.get('Company')}")

    end_time = time.time()
    logger.info("\n--- Test Summary ---")
    logger.info(f"Scraped a total of {len(results)} business listings.")
    logger.info(f"Total execution time: {end_time - start_time:.2f} seconds.")
    if results:
        import pprint
        logger.info("\n--- Sample Results ---")
        pprint.pprint(results[:10])

if __name__ == "__main__":
    asyncio.run(main_test())
    # parser = argparse.ArgumentParser(description="Scrape business listings from Yell UK by industry and city.")
    # parser.add_argument("industry", help="Industry to search for, e.g. 'software'")
    # parser.add_argument("city", help="City to search in, e.g. 'London'")
    # args = parser.parse_args()

    # logger.info(f"Searching for {args.industry} businesses in {args.city}...")
    # async def main():
    #     count = 0
    #     async for biz in new_scrape_yell_businesses(args.industry, args.city):
    #         count += 1
    #     #     logger.info(f"{count}. {biz['name']}")
    #     #     logger.info(f"   Industry: {biz['industry']}")
    #     #     logger.info(f"   Address: {biz['address']}")
    #     #     logger.info(f"   Phone: {biz['phone']}")
    #     #     logger.info(f"   Website: {biz['website']}")
    #     #     logger.info("-" * 40)
    #     logger.info(f"\nFound {count} businesses total:")
    #     # logger.info("=" * 60)
    # asyncio.run(main())
