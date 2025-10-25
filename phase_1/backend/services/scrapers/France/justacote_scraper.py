import sys
import os
import argparse
import urllib.parse
import re
from bs4 import BeautifulSoup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from backend.services.helper.flaresolverr_cookies import get_solved_page, post_solved_page
from backend.config.browser_config import PlaywrightManager
import asyncio
import logging
import time
from backend.config.logger_config import setup_logger

setup_logger()
logger = logging.getLogger("Justacote France")

def is_cloudflare_challenge(content):
    """Check if the page content indicates a Cloudflare challenge."""
    if not content:
        return False
    return any(indicator in content for indicator in [
        "Cloudflare",
        "Just a moment...",
        "DDoS protection by Cloudflare",
        "cf-browser-verification",
        "challenge-platform"
    ])

async def scrape_justacote_businesses(industry: str, city: str, page=None, max_timeout=10.0):
    """
    Scrape business listings from Justacote.com by industry and city.
    Yields each business as it is scraped.
    Uses Playwright as primary method, falls back to FlareSolverr if Cloudflare is detected.
    """
    base_url = "https://www.justacote.com/resultats"
    industry_encoded = urllib.parse.quote(industry)
    city_encoded = urllib.parse.quote(city)
    
    # Extract city name for address formatting
    city_parts = city.split()
    city_name = city_parts[0].strip()
    
    page_num = 1
    visited_urls = set()
    cookies = []
    use_flaresolverr = False
    
    # Initialize Playwright manager
    manager = None
    internal_page = False
    if page is None:
        manager = PlaywrightManager(headless=False)
        page = await manager.start_browser(stealth_on=True)
        internal_page = True

    try:
        # Construct the initial search URL
        current_url = f"{base_url}?what={industry_encoded}&where={city_encoded}"
        
        while True:
            logger.info(f"Scraping page {page_num}...")
            logger.info(f"URL: {current_url}")
            
            if current_url in visited_urls:
                logger.warning("Already visited this URL - avoiding infinite loop")
                break
            visited_urls.add(current_url)

            # Check if URL matches the termination pattern
            if should_terminate_scraping(current_url):
                logger.info("Reached generic page URL - terminating scraper")
                break

            try:
                content = None
                
                if not use_flaresolverr:
                    # Try Playwright first
                    try:
                        await page.goto(current_url, wait_until="domcontentloaded", timeout=60000)
                        content = await page.content()
                        
                        # Check for Cloudflare challenge
                        if is_cloudflare_challenge(content):
                            logger.warning("Cloudflare challenge detected, switching to FlareSolverr")
                            use_flaresolverr = True
                            content = None
                        else:
                            logger.info("Successfully loaded page with Playwright")
                            
                    except Exception as e:
                        logger.warning(f"Playwright failed: {e}, switching to FlareSolverr")
                        use_flaresolverr = True
                
                if use_flaresolverr or not content:
                    solution = await get_solved_page(current_url, cookies=cookies)
                    if not solution:
                        logger.error(f"Failed to get page content for {current_url}")
                        break
                    
                    # Store cookies from first request
                    if page_num == 1:
                        cookies = solution.get("cookies", [])
                    
                    content = solution.get("response", "")
                
                if not content or len(content) == 0:
                    break

                soup = BeautifulSoup(content, "html.parser")

                # Check for no results
                page_text = soup.get_text()
                if "Aucun résultat" in page_text or "No results" in page_text:
                    break

                # Find business listings container
                listings_container = soup.find("ul", class_="mt-4 mb-3 list-unstyled best-addresses-list")
                if not listings_container:
                    logger.info("No listings container found - end of results")
                    break

                business_cards = listings_container.find_all("div", class_="bg-main d-flex flex-column flex-md-row list-element my-3 poi-common-block")
                if not business_cards:
                    break

                logger.info(f"Found {len(business_cards)} businesses on page {page_num}")

                for i, card in enumerate(business_cards):
                    try:
                        # Extract business name and detail URL
                        name_link = card.find("a", class_="fs-5 teal")
                        if not name_link:
                            continue

                        name = name_link.get_text(strip=True)
                        detail_url = name_link.get("href", "")

                        if not name or not detail_url:
                            continue

                        if detail_url.startswith("/"):
                            detail_url = "https://www.justacote.com" + detail_url

                        name = re.sub(r'\s+', ' ', name).strip()
                        if len(name) < 2:
                            continue

                        # Scrape business details from detail page
                        address, phone, website, industry_detail = await scrape_business_details(
                            detail_url, city_name, page if not use_flaresolverr else None, cookies, use_flaresolverr
                        )

                        # Format address similar to other scrapers
                        if address and address != "NA":
                            full_address = f"{address}, {city_name.title()}, France"
                        else:
                            full_address = f"{city_name.title()}, France"

                        business_info = {
                            "Company": name,
                            "Industry": industry_detail if industry_detail != "NA" else industry.capitalize(),
                            "Address": full_address,
                            "State": "France",
                            "Business_phone": phone,
                            "Website": website,
                            "BBB_rating": "NA"
                        }

                        yield business_info

                    except Exception as e:
                        continue

                # Find the next page link to continue pagination
                next_page_link = soup.find("a", {"aria-label": "Page suivante"})
                if next_page_link and next_page_link.get("href"):
                    next_href = next_page_link.get("href")
                    if next_href.startswith("/"):
                        current_url = "https://www.justacote.com" + next_href
                    else:
                        current_url = next_href
                    page_num += 1
                    
                    if page_num > 100:
                        break
                else:
                    break

            except Exception as e:
                break

    except Exception as e:
        logger.error(f"An unexpected error occurred during scraping: {e}", exc_info=True)
    finally:
        if internal_page and manager is not None:
            await manager.stop_browser()

async def get_next_page_url(current_url, session_id, cookies):
    """
    Find the next page URL from the pagination section using FlareSolverr.
    Returns None if no next page is available.
    """
    try:
        # Get current page content to find pagination
        solution = await get_solved_page(current_url, cookies=cookies)
        if not solution:
            return None
            
        content = solution.get("response", "")
        soup = BeautifulSoup(content, "html.parser")
        
        # Look for pagination container
        pagination = soup.find("ul", class_="pagination")
        if not pagination:
            return None
        
        # Find the "Page suivante" link
        next_link = pagination.find("a", {"aria-label": "Page suivante"})
        if not next_link:
            return None
            
        next_href = next_link.get("href", "")
        if not next_href:
            return None
            
        if next_href.startswith("/"):
            next_href = "https://www.justacote.com" + next_href
            
        return next_href
        
    except Exception as e:
        return None

def should_terminate_scraping(url):
    """
    Check if the URL matches the termination pattern:
    justacote.com/something/page-x.htm (only 2 path components)
    Continue if: justacote.com/something/something/page-x.htm (3+ path components)
    """
    try:
        parsed_url = urllib.parse.urlparse(url)
        path_parts = [part for part in parsed_url.path.split('/') if part]
        
        # Check if it's a page-x.htm pattern
        if len(path_parts) >= 1 and re.match(r'page-\d+\.htm$', path_parts[-1]):
            # If only 2 path parts (city and page-x.htm), terminate
            if len(path_parts) == 2:
                return True
        
        return False
        
    except Exception:
        return False

async def scrape_business_details(detail_url, city, page=None, cookies=None, use_flaresolverr=False):
    """
    Scrape address, phone, website, and industry from business detail page.
    Uses Playwright if available, otherwise falls back to FlareSolverr.
    """
    address = "NA"
    phone = "NA"
    website = "NA"
    industry_val = "NA"
    
    try:
        content = None
        
        if not use_flaresolverr and page:
            # Try Playwright first
            try:
                await page.goto(detail_url, wait_until="domcontentloaded", timeout=15000)
                content = await page.content()
                
                # Check for Cloudflare challenge
                if is_cloudflare_challenge(content):
                    logger.warning(f"Cloudflare challenge detected on detail page {detail_url}, using FlareSolverr")
                    content = None
                    use_flaresolverr = True
                    
            except Exception as e:
                logger.warning(f"Playwright failed for detail page {detail_url}: {e}, using FlareSolverr")
                use_flaresolverr = True
        
        if use_flaresolverr or not content:
            # Use FlareSolverr
            solution = await get_solved_page(detail_url, cookies=cookies)
            if not solution:
                logger.error(f"Failed to get detail page: {detail_url}")
                return address, phone, website, industry_val
                
            content = solution.get("response", "")
        
        if not content:
            return address, phone, website, industry_val
            
        soup = BeautifulSoup(content, "html.parser")
        
        # Extract industry from h2-like bg-main title
        try:
            title_element = soup.find("h1", class_="h2-like bg-main")
            if title_element:
                title_text = title_element.get_text(strip=True)
                # Try to extract industry from title (often contains industry info)
                if "|" in title_text:
                    parts = title_text.split("|")
                    if len(parts) > 1:
                        industry_val = parts[1].strip()
                else:
                    # Look for industry in h3-like mt-5 section
                    industry_header = soup.find("h2", class_="h3-like mt-5")
                    if industry_header and "Coordonnées" not in industry_header.get_text():
                        industry_val = industry_header.get_text(strip=True)
        except Exception:
            pass
        
        try:
            first_p = soup.find("p", class_="mb-0 lh-sm")
            if first_p:
                address_text = first_p.get_text(strip=True)
                if address_text and len(address_text) > 2:
                    address = address_text
            else:
                logger.info("No p tag with 'mb-0 lh-sm' class found anywhere on page")
        except Exception as e:
            logger.error(f"Error extracting address: {e}")
            pass
        
        try:
            phone_element = soup.find("span", class_="text-purple fw-bold fs-5")
            if phone_element:
                phone_text = phone_element.get_text(strip=True)
                if phone_text and len(phone_text) > 5:
                    phone = phone_text
            else:
                # Look for phone in tel: links
                phone_link = soup.find("a", href=lambda x: x and x.startswith("tel:"))
                if phone_link:
                    phone_href = phone_link.get("href", "")
                    phone_number = phone_href.replace("tel:", "").strip()
                    if phone_number and len(phone_number) > 5:
                        phone = phone_number
                else:
                    # Look for phone reveal button - this would need more complex handling
                    phone_button = soup.find("button", class_="btn show-phone-number bg-teal d-flex align-items-center mb-4")
                    if phone_button:
                        # For now, just indicate phone is available but hidden
                        phone = "NA"
        except Exception:
            pass
        
        # Extract website - look for tooltipTrigger links
        try:
            tooltip_links = soup.find_all("a", class_="d-block border-0 icon tooltipTrigger")
            website_candidates = []
            
            for link in tooltip_links:
                href = link.get("href", "")
                if href.startswith("http") and "justacote.com" not in href:
                    # Skip email links
                    if not href.startswith("mailto:"):
                        website_candidates.append(href)
            
            # Take the first valid website link
            if len(website_candidates) >= 1:
                website = website_candidates[0]
                
        except Exception:
            pass
        
    except Exception as e:
        logger.error(f"Error scraping details from {detail_url}: {e}")
    
    return address, phone, website, industry_val

async def main():
    parser = argparse.ArgumentParser(description="Scrape business listings from Justacote.com by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'restaurant'")
    parser.add_argument("city", help="City to search in, e.g. 'Paris'")
    args = parser.parse_args()

    city = args.city.split(",")[0].strip()
    logger.info(f"Searching for {args.industry} businesses in {city}...")
    count = 0
    async for biz in scrape_justacote_businesses(args.industry, city, max_timeout=10.0):
        count += 1
        # logger.info(f"{count}. {biz['Company']}")
        # logger.info(f"   Industry: {biz['Industry']}")
        # logger.info(f"   Address: {biz['Address']}")
        # logger.info(f"   Phone: {biz['Business_phone']}")
        # logger.info(f"   Website: {biz['Website']}")
        # logger.info(f"   BBB Rating: {biz['BBB_rating']}")
        # logger.info("-" * 40)
    logger.info(f"\nFound {count} businesses total")

if __name__ == "__main__":
    asyncio.run(main())