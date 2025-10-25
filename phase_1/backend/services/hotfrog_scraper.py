from ast import parse
import asyncio
import os
import sys
from typing import Dict, List
from playwright.async_api import Locator
from playwright_stealth import stealth_async

from backend.services.parser import parse_number
# from parser import parse_number
from typing import AsyncGenerator, Dict


from backend.config.browser_config import PlaywrightManager

async def handle_cookie_consent(page):
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
    page_height = await page.evaluate("document.body.scrollHeight")
    steps = 8
    for i in range(1, steps + 1):
        position = (page_height * i) / steps
        await page.evaluate(f"window.scrollTo(0, {int(position)})")
        await asyncio.sleep(1)

async def extract_business_details(container: Locator, search_term: str) -> Dict[str, str] | None:
    try:
        info = {
            'Company': 'NA',
            'Industry': search_term.title(),
            'Address': 'NA',
            'Business_phone': 'NA'
        }

        name = container.locator('h3 a strong')
        if await name.count() > 0:
            info['Company'] = (await name.first.text_content()).strip()

        spans = await container.locator('span.small').all()
        for span in spans:
            text = (await span.text_content()).strip()
            if (
                text and
                "Is this your business" not in text and
                "Claim this business" not in text and
                "Review now" not in text and
                any(char.isdigit() for char in text) and
                len(text) > 5
            ):
                info['Address'] = "[H]" + text
            else:
                info['Address'] = "NA"

        phone = container.locator('a[href^="tel:"] strong')
        if await phone.count() > 0:
            raw = (await phone.first.text_content()).strip()
            parsed_num = parse_number(raw)
            info['Business_phone'] = parsed_num

        if info['Company'] != 'NA' or info['Business_phone'] != 'NA':
            return info
        
        return None
    except Exception:
        return None

async def extract_businesses(page, search_term: str) -> List[Dict[str, str]]:
    results = []
    main = page.locator('.col-lg-8.hf-serps-main')
    if await main.count() > 0:
        containers = main.locator('> div')
        for i in range(await containers.count()):
            container = containers.nth(i)
            data = await extract_business_details(container, search_term)
            if data:
                results.append(data)
    return results

async def scrape_hotfrog(search_term: str, location: str, page=None, max_pages: int = 5) -> AsyncGenerator[Dict[str, str], None]:
    search_term_clean = search_term.lower().replace(' ', '-')
    location_clean = location.lower().replace(', ', '-')
    start_url = f"https://www.hotfrog.com/search/{location_clean}/{search_term_clean}"

    internal_browser = False

    if page is None:
        manager = PlaywrightManager(headless=True)
        page = await manager.start_browser(stealth_on=True)
        internal_browser = True

    all_results = []
    seen = set()

    try:
        await stealth_async(page)
        await page.goto(start_url, wait_until='domcontentloaded')
        await asyncio.sleep(2)
        await handle_cookie_consent(page)

        for current_page in range(1, max_pages + 1):
            await slow_scroll(page)

            results = await extract_businesses(page, search_term)
            for item in results:
                key = f"{item['Company']}_{item['Business_phone']}"
                if key not in seen:
                    seen.add(key)
                    # all_results.append(item)
                    yield item
                    

            next_button = page.locator('nav[aria-label="Pagination"] a:has-text("Next")')
            if await next_button.count() == 0:
                break

            href = await next_button.get_attribute("href")
            if not href:
                break

            next_url = f"https://www.hotfrog.com{href}"
            await page.goto(next_url, wait_until='domcontentloaded')
            await asyncio.sleep(2)

    except Exception as e:
        print(f"Error during scraping: {e}")
        yield None
        return
    finally:
        if internal_browser:
            await manager.stop_browser()

    yield None
    return
