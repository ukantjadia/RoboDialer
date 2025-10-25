import asyncio
import os
import csv
from typing import Dict, List
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
from typing import AsyncGenerator

async def setup_browser(headless=True):
    """Set up and return a configured Playwright browser instance."""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 800},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    )
    page = await context.new_page()
    await page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false
    });
    """)
    return playwright, browser, context, page

async def quick_scroll(page):
    """Minimal scrolling implementation to load content."""
    page_height = await page.evaluate("document.body.scrollHeight")
    scroll_positions = [
        page_height * 0.5,
        page_height * 0.9
    ]
    for position in scroll_positions:
        await page.evaluate(f"window.scrollTo(0, {int(position)})")
        await asyncio.sleep(0.5)

async def extract_businesses(page):
    """Extract business information from the current page."""
    businesses = []
    selectors = [
        '.result', 
        '.organic', 
        '.listing', 
        '.info', 
        'div.srp-listing', 
        'div.v-card',
        'div[class*="listing"]',
        'div[class*="business"]'
    ]
    
    listings = None
    for selector in selectors:
        try:
            listings = await page.query_selector_all(selector)
            if listings and len(listings) > 0:
                # print(f"Found {len(listings)} listings with selector: {selector}")
                break
        except Exception:
            continue
    
    if not listings or len(listings) == 0:
        print("No listings found with standard selectors")
        return businesses
    
    for listing in listings:
        business_info = {'Company': 'NA', 'Industry': 'NA', 'Address': 'NA', 'Business_phone': 'NA', 'Website': 'NA'}
        
        # Extract business name
        try:
            name_element = await listing.query_selector('.business-name, h2 a, .name, a.business-name')
            if name_element:
                business_info['Company'] = (await name_element.inner_text()).strip()
            else:
                alt_name = await listing.query_selector('h2, .title, strong a, h3')
                if alt_name:
                    business_info['Company'] = (await alt_name.inner_text()).strip()
        except Exception:
            pass
        
        # Extract category/industry - only first category
        try:
            # Try to get individual category elements first
            category_elements = await listing.query_selector_all('.categories a, .category a, .business-categories a')
            if category_elements and len(category_elements) > 0:
                # Get just the first category
                first_category = await category_elements[0].inner_text()
                business_info['Industry'] = first_category.strip()
            else:
                # Fall back to getting the full category text and splitting
                category_element = await listing.query_selector('.categories, .category, .business-categories')
                if category_element:
                    full_category = await category_element.inner_text()
                    # Extract just the first category - split by common delimiters
                    for delimiter in [',', '\n', '•']:
                        if delimiter in full_category:
                            business_info['Industry'] = full_category.split(delimiter)[0].strip()
                            break
                    else:
                        # If no delimiter found, try to split by capital letters (common pattern)
                        import re
                        matches = re.findall(r'[A-Z][a-z]+', full_category)
                        if matches:
                            business_info['Industry'] = matches[0].strip()
                        else:
                            business_info['Industry'] = full_category.strip()
        except Exception:
            pass
        
        # Extract address
        try:
            address_parts = []
            street = await listing.query_selector('.street-address')
            if street:
                address_parts.append((await street.inner_text()).strip())
            
            locality = await listing.query_selector('.locality')
            if locality:
                address_parts.append((await locality.inner_text()).strip())
            
            if address_parts:
                business_info['Address'] = ", ".join(address_parts)
            else:
                full_address = await listing.query_selector('.address')
                if full_address:
                    business_info['Address'] = (await full_address.inner_text()).strip()
        except Exception:
            pass
        
        # Extract phone
        try:
            phone_element = await listing.query_selector('.phones, .phone, [class*="phone"]')
            if phone_element:
                business_info['Business_phone'] = (await phone_element.inner_text()).strip()
        except Exception:
            pass
        
        # Extract website
        try:
            website_element = await listing.query_selector('.track-visit-website, a[class*="website"], a[href*="http"][target="_blank"]')
            if website_element:
                business_info['Website'] = await website_element.get_attribute('href')
        except Exception:
            pass
        
        # Only add businesses where we got at least a name
        if business_info['Company'] != 'NA':
            businesses.append(business_info)
    
    return businesses

async def scrape_page(search_term: str, location: str, page_num: int) -> List[Dict[str, str]]:
    """Scrape a single page of Yellow Pages results with a fresh browser instance."""
    search_term_encoded = quote_plus(search_term)
    location_encoded = quote_plus(location)
    
    # Construct URL with page parameter
    if page_num == 1:
        url = f"https://www.yellowpages.com/search?search_terms={search_term_encoded}&geo_location_terms={location_encoded}"
    else:
        url = f"https://www.yellowpages.com/search?search_terms={search_term_encoded}&geo_location_terms={location_encoded}&page={page_num}"
    
    # print(f"Navigating to page {page_num}: {url}")
    
    # Set up a fresh browser instance for this page
    playwright, browser, context, page = await setup_browser(headless=True)
    businesses = []
    
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(1)
        await quick_scroll(page)
        businesses = await extract_businesses(page)
        
        # if businesses:
        #     print(f"Found {len(businesses)} businesses on page {page_num}")
        # else:
        #     print(f"No businesses found on page {page_num}")
    
    except Exception as e:
        print(f"Error scraping page {page_num}: {e}")
    
    finally:
        await browser.close()
        await playwright.stop()
    
    return businesses

# async def scrape_yellowpages(search_term: str, location: str, max_pages: int = 3) -> AsyncGenerator[Dict[str, str], None]:
#     """Asynchronously scrapes Yellow Pages for business listings, using a fresh browser for each page."""
#     all_businesses = []
    
#     for page_num in range(1, max_pages + 1):
#         # Scrape each page with a fresh browser instance
#         page_businesses = await scrape_page(search_term, location, page_num)
        
#         if page_businesses:
#             yield page_businesses
#             # all_businesses.extend(page_businesses)
            
#         # Add a delay between page requests
#         if page_num < max_pages:
#             # delay = 3 + (2 * (page_num - 1))  # Increasing delay for each subsequent page
#             # print(f"Waiting {delay} seconds before next page...")
#             await asyncio.sleep(1)
    
#     yield None
#     return

async def scrape_yellowpages(search_term: str, location: str, max_pages: int = 3) -> AsyncGenerator[Dict[str, str], None]:
    """Asynchronously scrapes Yellow Pages for business listings, yielding complete pages.
    
    This function streams results page by page, yielding each batch of businesses
    as they are found rather than waiting for all pages to be scraped.
    Each yield is a complete business dictionary that can be processed independently.
    """
    for page_num in range(1, max_pages + 1):
        # Scrape each page with a fresh browser instance
        page_businesses = await scrape_page(search_term, location, page_num)
        
        if page_businesses:
            # Yield each complete business dictionary individually
            for business in page_businesses:
                # Make sure the business has all required fields before yielding
                if business and business.get('Company', 'NA') != 'NA':
                    yield business
            
        # Add a delay between page requests
        if page_num < max_pages:
            await asyncio.sleep(1)

async def save_to_csv(businesses, filename='yellowpages_data.csv'):
    """Saves the scraped business data to a CSV file."""
    if not businesses:
        print("No data to save.")
        return
    
    # Create output directory if needed
    output_dir = "yellowpages_data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'industry', 'address', 'phone', 'website']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for business in businesses:
            writer.writerow(business)
    
    print(f"Data saved to {filepath}")
    return filepath

async def main():
    """Main function to run the scraper."""
    print("\n=== Yellow Pages Scraper ===\n")
    
    search_term = input("Enter business type to search for (e.g., 'restaurants'): ")
    location = input("Enter location (city, state, or zip code): ")
    
    try:
        max_pages = int(input("Enter maximum number of pages to scrape (1-5 recommended): "))
        if max_pages < 1:
            max_pages = 1
        if max_pages > 5:
            print("Limiting to 5 pages maximum to avoid blocks")
            max_pages = 5
    except:
        print("Invalid input, defaulting to 1 page.")
        max_pages = 1
    
    print(f"\nScraping Yellow Pages for '{search_term}' in '{location}'...")
    
    businesses = await scrape_yellowpages(search_term, location, max_pages)
    
    if businesses:
        print(f"\nSuccessfully scraped {len(businesses)} businesses.")
        filename = f"{search_term.replace(' ', '_')}_{location.replace(' ', '_')}.csv"
        await save_to_csv(businesses, filename)
        print(f"Data saved to yellowpages_data/{filename}")
    else:
        print("\nNo businesses were scraped.")

if __name__ == "__main__":
    asyncio.run(main())