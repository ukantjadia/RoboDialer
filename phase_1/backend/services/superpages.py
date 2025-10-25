import asyncio
import os
import sys
from typing import Dict, List
from playwright.async_api import Locator, Page
from typing import AsyncGenerator

# sys.path.append(os.path.abspath("d:/Caprae Capital/Work/LeadGenAI/phase_1/backend"))
# from config.browser_config import PlaywrightManager

# async def save_to_csv(businesses, filename='superpages_data.csv'):
#     import csv
#     """Save extracted business data to CSV file."""
#     if not businesses:
#         print("No data to save to CSV.")
#         return None
    
#     output_dir = "superpages_data"
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)
    
#     filepath = os.path.join(output_dir, filename)
    
#     with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
#         fieldnames = ['Company', 'Business_phone', 'Website', 'Address', 'Industry']
#         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
#         writer.writeheader()
#         for business in businesses:
#             writer.writerow(business)
    
#     print(f"CSV file saved to: {filepath}")

async def handle_cookie_consent(page):
    """Handle cookie consent dialogs."""
    consent_selectors = [
        'button#onetrust-accept-btn-handler',
        'button.accept-cookies',
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
    """Scroll down the page gradually."""
    page_height = await page.evaluate("document.body.scrollHeight")
    steps = 5
    for i in range(1, steps + 1):
        position = (page_height * i) / steps
        await page.evaluate(f"window.scrollTo(0, {int(position)})")
        await asyncio.sleep(0.5)

async def extract_business_details(container: Locator) -> Dict[str, str] | None:
    """Extract business information from a listing container."""
    try:
        info = {
            'Company': 'NA',
            'Business_phone': 'NA',
            'Website': 'NA',
            'Address': 'NA',
            'Industry': 'NA'
        }

        # Extract business name
        name = container.locator('h2 a span, h2 a')
        if await name.count() > 0:
            info['Company'] = (await name.first.text_content()).strip()

        # Extract phone number
        phone = container.locator('a.phones.phone.primary, a[href^="tel:"]')
        if await phone.count() > 0:
            phone_text = await phone.first.text_content()
            digits = ''.join(char for char in phone_text if char.isdigit())
            if digits:
                info['Business_phone'] = digits

        # Extract website
        website = container.locator('a.weblink-button, a[target="_blank"][rel="nofollow noopener"]')
        if await website.count() > 0:
            href = await website.first.get_attribute('href')
            if href:
                info['Website'] = href

        # Extract address
        address = container.locator('span.street-address, p:has(span)')
        if await address.count() > 0:
            info['Address'] = (await address.first.text_content()).strip()
        
        industry = container.locator('div.categories')
        if await industry.count() > 0:
            first_industry = industry.locator('a').first
            info['Industry'] = (await first_industry.text_content()).strip()

        # Only return if we have at least a company name or phone number
        if info['Company'] != 'NA' or info['Business_phone'] != 'NA':
            return info
        
        return None
    except Exception as e:
        print(f"Error extracting business details: {e}")
        return None

async def extract_businesses(page) -> List[Dict[str, str]]:
    """Extract all business listings from the current page."""
    results = []
    
    # Wait for the page to load completely
    await page.wait_for_load_state("domcontentloaded")
    
    # Look for business listings with different selectors
    listing_selectors = [
        'div.business-listing',
        'div[id^="lid-"]',
        '.search-results > div',
        '.listing-results > div',
        '#main-content > div'
    ]
    
    # Try each selector until we find business listings
    for selector in listing_selectors:
        containers = page.locator(selector)
        count = await containers.count()
        if count > 0:
            # print(f"Found {count} business listings with selector: {selector}")
            
            for i in range(count):
                container = containers.nth(i)
                data = await extract_business_details(container)
                if data:
                    results.append(data)
            
            # If we found results with this selector, stop trying others
            if results:
                break
    
    return results

async def scrape_superpages(search_term: str, location: str, page: Page, max_pages: int = 5) -> AsyncGenerator[Dict[str, str], None]:
    """Scrape Superpages using the provided browser page."""
    # Format the search URL
    search_term_clean = search_term.replace(' ', '+')
    location_clean = location.replace(' ', '+').replace(',', '%2C')
    start_url = f"https://www.superpages.com/search?search_terms={search_term_clean}&geo_location_terms={location_clean}"
    
    # print(f"Starting scrape at URL: {start_url}")
    try:
        # Navigate to the first URL
        await page.goto(start_url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3)
        await handle_cookie_consent(page)
        
        all_results = []
        current_page = 1
        
        # Process each page sequentially
        while current_page <= max_pages:
            # print(f"Scraping page {current_page} of {max_pages}")
            await slow_scroll(page)
            
            # Extract businesses from the current page
            results = await extract_businesses(page)
            for result in results:
                yield result
            # all_results.extend(results)
            # print(f"Found {len(results)} businesses on page {current_page}")
            
            # Check if we've reached the maximum pages
            if current_page >= max_pages:
                break
            
            # Try to navigate to the next page
            try:
                next_button = await page.query_selector('a.next.ajax-page')
                if next_button:
                    await next_button.click()
                    await asyncio.sleep(2)  # Wait for the next page to load
                    current_page += 1
                else:
                    # print("No more pages available")
                    break
            except Exception as e:
                print(f"Failed to click next page: {e}")
        
        # Deduplicate results
        seen = set()
        unique = []
        for item in all_results:
            key = f"{item['Company']}_{item['Business_phone']}"
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        # print(f"Total unique businesses found: {len(unique)}")
        yield None
        return
    
    except Exception as e:
        print(f"Error during scraping: {e}")
        yield None
        return