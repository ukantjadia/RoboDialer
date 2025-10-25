import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import logging
import re
from urllib.parse import quote_plus
import httpx

logger = logging.getLogger(__name__)

class EnhancedScrapingService:
    def __init__(self, companies_collection):
        self.companies_collection = companies_collection

    async def is_valid_website(self, url: str) -> bool:
        try:
            # Always use https if not present
            if not url.startswith('http'):
                url = 'https://' + url
            elif url.startswith('http://'):
                url = 'https://' + url[len('http://'):]
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.info(f"Invalid website {url}: HTTP {resp.status_code}")
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Invalid website {url}: {e}")
            return False

    async def fetch_html(self, url: str) -> Optional[str]:
        try:
            # Always use https if not present
            if not url.startswith('http'):
                url = 'https://' + url
            elif url.startswith('http://'):
                url = 'https://' + url[len('http://'):]
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    html = resp.text
                    # Check for block page keywords
                    block_keywords = ['captcha', 'forbidden', 'not a robot', 'login', 'cloudflare', 'verify you are human']
                    lower_html = html[:1000].lower()
                    if any(kw in lower_html for kw in block_keywords):
                        logger.warning(f"Possible block page for {url}: {html[:300]}")
                    return html
                else:
                    logger.info(f"Failed to fetch HTML from {url}: HTTP {resp.status_code} | Content: {resp.text[:300]}")
        except Exception as e:
            logger.error(f"Failed to fetch HTML from {url}: {e}")
        return None
    
    async def get_final_url(self, url: str) -> str:
        # Returns the final URL after following redirects
        if not url.startswith('http'):
            url = "https://" + url
        elif url.startswith("http://"):
            url = 'https://' + url[len('http://'):]
            
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            return str(resp.url)
        
    async def is_redirect(self, url: str) -> bool:
        # Returns True if the URL is a redirect.
        final_url = await self.get_final_url(url)
        
        # Normalize both URLs for comparison
        orig = url.rstrip('/').lower()
        final = final_url.rstrip('/').lower()
        
        return orig != final

    def extract_info_from_html(self, html: str, keywords: List[str]) -> Dict[str, Any]:
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        keyword_matches = {kw: len(re.findall(re.escape(kw), text, re.IGNORECASE)) for kw in keywords}
        return {
            'keyword_matches': keyword_matches,
            'text_snippet': text[:5000]
        }

    async def google_search_first_result(self, company_name: str) -> Optional[str]:
        search_url = f"https://www.google.com/search?q={quote_plus(company_name)}"
        html = await self.fetch_html(search_url)
        if not html:
            return None
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.select('a'):
            href = a.get('href')
            if href and href.startswith('/url?q='):
                url = href.split('/url?q=')[1].split('&')[0]
                if await self.is_valid_website(url):
                    return url
        return None

    async def scrape_company(self, company_name: str, website_url: Optional[str], keywords: List[str], city: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
        # 1. Try to scrape the provided website
        if website_url and await self.is_valid_website(website_url):
            if await self.is_redirect(website_url):
                final_url = await self.get_final_url(website_url)
                logger.info(f"Website {website_url} redirects to {final_url}")
                html = await self.fetch_html(final_url)
            else:
                html = await self.fetch_html(website_url)
            if html:
                return self.extract_info_from_html(html, keywords)
            
        # 2. If no valid website, search Google by company name
        google_url = await self.google_search_first_result(company_name)
        if google_url:
            html = await self.fetch_html(google_url)
            if html:
                return self.extract_info_from_html(html, keywords)
            
        # 3. Try Google search with company name + city + state for more accuracy
        if city or state:
            search_terms = company_name
            if city:
                search_terms += f" {city}"
            if state:
                search_terms += f" {state}"
            google_url2 = await self.google_search_first_result(search_terms)
            if google_url2:
                html = await self.fetch_html(google_url2)
                if html:
                    return self.extract_info_from_html(html, keywords)
                
        # 4. If all fails, return empty info
        return {'keyword_matches': {}, 'text_snippet': ''} 