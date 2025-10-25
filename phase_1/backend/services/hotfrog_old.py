import asyncio
import os
import csv
import re
from typing import Dict, List
from playwright.async_api import async_playwright, Locator

async def setup_browser(headless=False):
    """Set up the browser with stealth configurations to avoid detection."""
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
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    """)
    return playwright, browser, context, page

async def handle_cookie_consent(page):
    """Handle any cookie consent or popup banners."""
    consent_selectors = [
        'button#onetrust-accept-btn-handler',
        'button.accept-cookies',
        'button.consent-accept',
        'button[aria-label="Accept"]',
        'button[aria-label="Accept all"]',
        'button:has-text("Accept")',
        'button:has-text("Accept All")'
    ]
    
    for selector in consent_selectors:
        try:
            if await page.locator(selector).count() > 0:
                await page.locator(selector).click()
                await asyncio.sleep(1)
                break
        except Exception:
            pass

async def slow_scroll(page):
    """Scroll through the page to trigger lazy loading content."""
    page_height = await page.evaluate("document.body.scrollHeight")
    view_height = await page.evaluate("window.innerHeight")
    
    steps = 8
    for i in range(1, steps + 1):
        position = (page_height * i) / steps
        await page.evaluate(f"window.scrollTo(0, {int(position)})")
        await asyncio.sleep(1)
        
        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height > page_height:
            page_height = new_height
            steps += 1

async def extract_business_details(container: Locator, search_term: str) -> Dict[str, str]:
    """Extract details from a single business container using Locator API."""
    try:
        business_info = {
            'Company': 'NA',
            'Industry': search_term,
            'Address': 'NA',
            'Business_phone': 'NA',
        }
        
        # Extract name
        name_locator = container.locator('h3 a strong')
        if await name_locator.count() > 0:
            business_info['Company'] = (await name_locator.first.text_content()).strip()
        
        # Extract address - using a more specific approach to avoid multiple matches
        # First try to find the specific address span (usually the second span.small)
        address_spans = await container.locator('span.small').all()
        if len(address_spans) >= 2:
            # The second span is typically the address
            address_text = (await address_spans[1].text_content()).strip()
            # Clean up address text
            address_text = re.sub(r'Is this your business\?.*', '', address_text)
            address_text = re.sub(r'Claim this business.*', '', address_text)
            address_text = re.sub(r'Message business.*', '', address_text)
            address_text = re.sub(r'Review now.*', '', address_text)
            
            # Check if it looks like an address (contains numbers)
            if re.search(r'\d', address_text) and len(address_text) > 5:
                business_info['Address'] = address_text.strip()
        
        # Extract phone
        phone_locator = container.locator('a[href^="tel:"] strong')
        if await phone_locator.count() > 0:
            phone_text = (await phone_locator.first.text_content()).strip()
            phone_text = re.sub(r'[^\d\s\-\+\(\)]', '', phone_text)
            business_info['Business_phone'] = phone_text
        
        # Extract website
        # website_locators = await container.locator('a[href^="http"]:not([href*="hotfrog.com"]):not([href^="tel:"])').all()
        # for locator in website_locators:
        #     href = await locator.get_attribute('href')
        #     if href and not href.startswith('tel:'):
        #         business_info['Website'] = href
        #         break
        
        if ((business_info['Company'] != 'N/A' and business_info['Company'] != '') or 
            (business_info['Business_phone'] != 'N/A' and business_info['Business_phone'] != '')):
            return business_info
        return None
    
    except Exception as e:
        print(f"Error extracting business details: {e}")
        return None

async def extract_businesses(page, search_term: str) -> List[Dict[str, str]]:
    """Extract all businesses from the page using Locator API."""
    businesses_data = []
    
    main_container = page.locator('.col-lg-8.hf-serps-main')
    if await main_container.count() > 0:
        listing_containers = main_container.locator('> div')
        listings_count = await listing_containers.count()
        
        for i in range(listings_count):
            container = listing_containers.nth(i)
            business_info = await extract_business_details(container, search_term)
            if business_info:
                businesses_data.append(business_info)
    
    return businesses_data

async def scrape_page(search_term: str, location: str, page_num: int) -> List[Dict[str, str]]:
    """Scrape a single page of Hotfrog results."""
    if page_num == 1:
        url = f"https://www.hotfrog.com/search/{location}/{search_term}"
    else:
        url = f"https://www.hotfrog.com/search/{location}/{search_term}/{page_num}"
    
    playwright, browser, context, page = await setup_browser(headless=False)
    businesses = []
    
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(5)
        
        await handle_cookie_consent(page)
        await slow_scroll(page)
        
        businesses = await extract_businesses(page, search_term)
    
    except Exception as e:
        print(f"Error scraping page {page_num}: {e}")
    
    finally:
        await browser.close()
        await playwright.stop()
    
    return businesses

async def scrape_hotfrog(search_term: str, location: str, max_pages: int = 3) -> List[Dict[str, str]]:
    """Scrape multiple pages of Hotfrog results."""
    all_businesses = []
    
    search_term = search_term.lower().replace(' ', '-')
    location = location.lower().replace(', ', '-')
    
    for page_num in range(1, max_pages + 1):
        page_businesses = await scrape_page(search_term, location, page_num)
        
        if page_businesses:
            all_businesses.extend(page_businesses)
            
        if page_num < max_pages:
            delay = 5 + (2 * (page_num - 1))
            await asyncio.sleep(delay)
    
    unique_businesses = []
    seen = set()
    
    for business in all_businesses:
        identifier = f"{business['Company']}_{business['Business_phone']}"
        if identifier not in seen:
            seen.add(identifier)
            unique_businesses.append(business)
    
    return unique_businesses

async def save_to_csv(businesses, filename='hotfrog_data.csv'):
    """Save extracted business data to CSV file."""
    if not businesses:
        print("No data to save to CSV.")
        return None
    
    output_dir = "yellowpages_data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Company', 'Industry', 'Address', 'Business_phone']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for business in businesses:
            writer.writerow(business)
    
    print(f"CSV file saved to: {filepath}")
    return filepath

async def main():
    """Main function to run the scraper with user interaction."""
    print("\n=== HotFrog Business Scraper ===\n")
    
    search_term = "primary care"
    location = "glendale, ca"
     
    print(f"\nScraping Hotfrog for '{search_term}' in '{location}'...")
    
    businesses = await scrape_hotfrog(search_term, location, 5)
    
    if businesses:
        print(f"\nSuccessfully scraped {len(businesses)} unique businesses.")
        filename = f"{search_term.replace(' ', '_')}_{location.replace(' ', '_')}.csv"
        await save_to_csv(businesses, filename)
        print(f"Data saved {filename}")
    else:
        print("\nNo businesses were scraped. Try running the script again or adjusting your search terms.")

if __name__ == "__main__":
    asyncio.run(main())