import sys
import os
import argparse
import asyncio
import urllib.parse
import re
from bs4 import BeautifulSoup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
from backend.config.browser_config import PlaywrightManager
import logging
from backend.config.logger_config import setup_logger

setup_logger()
logger = logging.getLogger("PagesJaunes FR")

async def scrape_pagesjaunes_businesses(industry: str, city: str, page=None):
    """
    Scrape business listings from PagesJaunes by industry and city.
    Yields each business as it is scraped.
    If page is not provided, a new browser tab will be created.
    """
    # Note: PagesJaunes requires a custom stealth config different to the manager's default.
    # Always create our own browser for PagesJaunes regardless of page parameter
    base_url = "https://www.pagesjaunes.fr/annuaire/chercherlespros"
    industry_encoded = urllib.parse.quote(industry)
    
    city_parts = city.split(",")
    city_name = city_parts[0].strip()
    state_name = city_parts[1].strip() if len(city_parts) > 1 else "France"
    
    city_encoded = urllib.parse.quote(city_name)
    url = f"{base_url}?quoiqui={industry_encoded}&ou={city_encoded}&univers=pagesjaunes&idOu="
    
    # Always use our own browser for PagesJaunes - ignore passed page parameter
    from playwright.async_api import async_playwright
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,  # Changed to True for API calls
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-gpu',
            '--disable-features=VizDisplayCompositor',
        ]
    )
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        extra_http_headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    )
    page = await context.new_page()
    
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
    """)

    try:
        current_url = url
        page_num = 1
        visited_urls = set()
        
        while True:
            logger.info(f"Scraping page {page_num}...")
            logger.info(f"URL: {current_url}")
            
            # Avoid infinite loops
            if current_url in visited_urls:
                logger.warning("Already visited this URL - avoiding infinite loop")
                break
            visited_urls.add(current_url)
            
            try:
                await page.goto(current_url, wait_until="domcontentloaded", timeout=60000)
                
                # CAPTCHA/verification check
                captcha_locator = page.locator("text=vérification")
                captcha_locator2 = page.locator("text=captcha")
                if await captcha_locator.count() > 0 or await captcha_locator2.count() > 0:
                    logger.warning("CAPTCHA detected. Reloading page...")
                    await page.reload()
                
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Check if on detail page instead of results
                title = soup.find("title")
                page_title = title.text if title else 'No title'
                if any(keyword in page_title.lower() for keyword in ['adresse', 'horaires', 'ouvert']):
                    logger.warning("On business detail page, not search results. Redirecting...")
                    search_url = f"https://www.pagesjaunes.fr/annuaire/chercherlespros?quoiqui={industry_encoded}&ou={city_encoded}"
                    await page.goto(search_url, wait_until="domcontentloaded")
                    await page.wait_for_timeout(5000)
                    content = await page.content()
                    soup = BeautifulSoup(content, "html.parser")
                
                business_cards = []
                
                # Find main results container
                results_containers = [
                    soup.find("div", class_=lambda x: x and "bi-list" in str(x)),
                    soup.find("ul", class_=lambda x: x and "bi-list" in str(x)),
                    soup.find("div", {"id": "search-results"}),
                    soup.find("div", class_=lambda x: x and "results" in str(x)),
                ]
                
                business_list = None
                for container in results_containers:
                    if container:
                        business_list = container
                        break
                
                if business_list:
                    # Find business cards
                    potential_cards = business_list.find_all("li", class_=lambda x: x and any(cls in str(x) for cls in ["bi-generic", "bi-professional", "listing"]))
                    for card in potential_cards:
                        card_text = card.get_text().lower()
                        if any(nav_text in card_text for nav_text in ['se référencer', 'créer mon compte', 'se connecter', 'suivant', 'précédent']):
                            continue
                        if card.find("a", href=lambda x: x and "/pros/" in str(x)):
                            business_cards.append(card)
                        elif card.find("h3") or card.find("div", class_=lambda x: x and "denomination" in str(x)):
                            business_cards.append(card)
                
                if not business_cards:
                    # Check for explicit "no results" message
                    page_text = soup.get_text()
                    if (
                        any(phrase in page_text.lower() for phrase in ['aucun résultat', 'pas de résultat', '0 résultat'])
                        or "Oups… nous n'avons pas encore de réponse à cette recherche !" in page_text
                    ):
                        logger.info("No results found for this search")
                        break
                    
                    # Try alternative: links with /pros/
                    pros_links = soup.find_all("a", href=lambda x: x and "/pros/" in str(x))
                    if pros_links:
                        for link in pros_links[:10]:
                            fake_card = {"link": link, "name": link.get_text(strip=True)}
                            business_cards.append(fake_card)
                    else:
                        logger.info("No business cards found - end of results")
                        break
                
                logger.info(f"Found {len(business_cards)} businesses on page {page_num}")
                
                # Process business cards
                for i, card in enumerate(business_cards):
                    try:
                        if isinstance(card, dict) and "link" in card:
                            name = card["name"]
                            detail_url = card["link"].get("href", "")
                            address = "NA"
                        else:
                            # Extract business name
                            name = None
                            name_elements = [
                                card.find("h3"),
                                card.find("a", class_=lambda x: x and "denomination" in str(x)),
                                card.find("div", class_=lambda x: x and "denomination" in str(x)),
                            ]
                            for elem in name_elements:
                                if elem:
                                    name = elem.get_text(strip=True)
                                    break
                            
                            if not name:
                                link = card.find("a", href=lambda x: x and "/pros/" in str(x))
                                if link:
                                    name = link.get_text(strip=True)
                            
                            # Extract detail URL
                            detail_url = None
                            link_element = card.find("a", href=lambda x: x and "/pros/" in str(x))
                            if link_element:
                                detail_url = link_element.get("href", "")
                            
                            # Extract address
                            address = "NA"
                            try:
                                address_link = card.find("a", class_="pj-lb pj-link")
                                if address_link:
                                    spans = address_link.find_all("span")
                                    if spans:
                                        first_span = spans[0]
                                        address_text = first_span.get_text(strip=True)
                                        if address_text and len(address_text) > 3:
                                            address_text = re.sub(r'\bVoir le plan\b', '', address_text, flags=re.IGNORECASE)
                                            address_text = re.sub(r'\s+', ' ', address_text).strip()
                                            if not re.match(r'^(Paris|Lyon|Marseille|Toulouse|Nice|Nantes|Strasbourg|Montpellier|Bordeaux|Lille)$', address_text, flags=re.IGNORECASE):
                                                address = address_text
                                        
                                    if address == "NA":
                                        full_text = address_link.get_text(strip=True)
                                        parts = re.split(r'(?:Paris|Lyon|Marseille|Toulouse|Nice|Nantes|Strasbourg|Montpellier|Bordeaux|Lille)', full_text, flags=re.IGNORECASE)
                                        if parts and len(parts[0].strip()) > 3:
                                            address_text = parts[0].strip()
                                            address_text = re.sub(r'\bVoir le plan\b', '', address_text, flags=re.IGNORECASE)
                                            address_text = re.sub(r'\s+', ' ', address_text).strip()
                                            if address_text:
                                                address = address_text
                            except Exception:
                                pass
                        
                        if not name or not detail_url:
                            continue
                        
                        name = re.sub(r'\s+', ' ', name).strip()
                        if len(name) < 2:
                            continue
                        
                        if detail_url.startswith("/"):
                            detail_url = "https://www.pagesjaunes.fr" + detail_url
                        
                        if not detail_url.startswith("https://www.pagesjaunes.fr/pros/"):
                            continue
                        
                        # Extract industry
                        industry_val = industry.capitalize()
                        if not isinstance(card, dict):
                            industry_elements = [
                                card.find("li", class_=lambda x: x and "tag" in str(x)),
                                card.find("span", class_=lambda x: x and "activite" in str(x)),
                                card.find("div", class_=lambda x: x and "activite" in str(x)),
                            ]
                            for elem in industry_elements:
                                if elem:
                                    extracted_industry = elem.get_text(strip=True)
                                    if extracted_industry and extracted_industry != "NA":
                                        industry_val = extracted_industry.capitalize()
                                    break
                        
                        # Scrape business details
                        website, phone = await scrape_business_details(page, detail_url)
                        
                        # Parse address for consistent formatting
                        cleaned_street = address.replace(",", "").strip() if address != "NA" else ""
                        if cleaned_street:
                            full_address = f"{cleaned_street}, {city_name.capitalize()}, {state_name}"
                        else:
                            full_address = f"{city_name.capitalize()}, {state_name}"
                        
                        business_info = {
                            "Company": name,
                            "Industry": industry_val,
                            "Address": full_address,
                            "State": state_name,
                            "Business_phone": phone,
                            "Website": website,
                            "BBB_rating": "NA"
                        }
                        
                        yield business_info
                        
                    except Exception as e:
                        logger.error(f"Error processing business card {i+1}: {e}")
                        continue
                
                # Next page URL
                next_url = None
                current_page_match = re.search(r'page=(\d+)', current_url)
                if current_page_match:
                    current_page_num = int(current_page_match.group(1))
                    next_page_num = current_page_num + 1
                    next_url = re.sub(r'page=\d+', f'page={next_page_num}', current_url)
                else:
                    if '?' in current_url:
                        next_url = current_url + '&page=2'
                    else:
                        next_url = current_url + '?page=2'
                
                if not next_url or next_url == current_url:
                    logger.info("No more pages available")
                    break
                
                current_url = next_url
                page_num += 1
                
                # Safety limit
                if page_num > 50:
                    logger.warning("Reached maximum page limit")
                    break
                    
            except Exception as e:
                logger.error(f"Error scraping page {page_num}: {e}")
                break
                
    finally:
            if 'browser' in locals():
                await browser.close()
                await playwright.stop()

async def scrape_business_details(page, detail_url):
    """
    Scrape website and phone from business detail page.
    """
    website = "NA"
    phone = "NA"
    
    try:
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
        
        # Extract website
        try:
            website_selectors = [
                "a[href*='www.']:not([href*='pagesjaunes']):not([href*='solocal'])",
                "a[href*='http']:not([href*='pagesjaunes']):not([href*='solocal'])",
                "span:has-text('.com')",
                "span:has-text('.fr')",
            ]
            for selector in website_selectors:
                element = page.locator(selector).first
                if await element.count() > 0:
                    if 'href' in selector:
                        website = await element.get_attribute('href')
                    else:
                        website = await element.text_content()
                        website = website.strip() if website else ""
                    if website and not any(exclude in website.lower() for exclude in ['pagesjaunes', 'solocal']):
                        break
        except Exception:
            pass
        
        # Extract phone number
        try:
            phone_selectors = [
                "span.noTrad",
                "span:regex('^\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}$')",
                "span:regex('^0\\d{1}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}$')",
                "span:regex('^\\+33\\s?\\d{1}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}\\s?\\d{2}$')",
            ]
            for selector in phone_selectors:
                elements = page.locator(selector)
                count = await elements.count()
                for i in range(count):
                    element = elements.nth(i)
                    text = await element.text_content()
                    text = text.strip() if text else ""
                    if text and re.match(r'^(\+33|0)\d[\s\d]{8,}$', text.replace(' ', '')):
                        phone = text
                        break
                if phone != "NA":
                    break
        except Exception:
            pass
            
    except Exception as e:
        logger.error(f"Error scraping details from {detail_url}: {e}")
    
    return website, phone

async def main():
    parser = argparse.ArgumentParser(description="Scrape business listings from PagesJaunes by industry and city.")
    parser.add_argument("industry", help="Industry to search for, e.g. 'software'")
    parser.add_argument("city", help="City to search in, e.g. 'paris'")
    args = parser.parse_args()
    
    city_name = args.city.split(",")[0].strip()
    logger.info(f"Searching for {args.industry} businesses in {city_name}...")
    count = 0
    async for biz in scrape_pagesjaunes_businesses(args.industry, args.city):
        count += 1
        # logger.info(f"{count}. {biz['Company']}")
        # logger.info(f"   Industry: {biz['Industry']}")
        # logger.info(f"   Address: {biz['Address']}")
        # logger.info(f"   Phone: {biz['Business_phone']}")
        # logger.info(f"   Website: {biz['Website']}")
        # logger.info(f"   BBB Rating: {biz['BBB_rating']}")
        # logger.info("-" * 40)
    
    logger.info(f"\nFound {count} businesses total:")

if __name__ == "__main__":
    asyncio.run(main())