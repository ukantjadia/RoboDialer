# Production-ready web scraping tool with SmartScraperGraph, Playwright and fallback support
import logging
import asyncio
import re
import platform
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from urllib.parse import urljoin, urlparse
import json

# Windows-specific asyncio event loop policy fix
def setup_windows_event_loop():
    """Setup Windows-compatible event loop policy"""
    if platform.system() == "Windows":
        try:
            # Check if we need to set the event loop policy
            current_policy = asyncio.get_event_loop_policy()
            if not isinstance(current_policy, asyncio.WindowsProactorEventLoopPolicy):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                logger.info("Set Windows ProactorEventLoopPolicy for subprocess support")
        except AttributeError:
            # Fallback for older Python versions
            logger.warning("WindowsProactorEventLoopPolicy not available, using default")
        except Exception as e:
            logger.warning(f"Failed to set Windows event loop policy: {e}")

# Initialize Windows compatibility
setup_windows_event_loop()

# Try to import SmartScraperGraph API client, but handle gracefully if it fails
try:
    from scrapegraph_py import Client
    SMARTSCRAPERGRAPH_API_AVAILABLE = True
except ImportError:
    SMARTSCRAPERGRAPH_API_AVAILABLE = False

# Try to import Playwright, but handle gracefully if it fails
try:
    from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    PlaywrightTimeoutError = Exception

# Fallback imports for when Playwright fails
import aiohttp
from bs4 import BeautifulSoup

# Try to import readability, but handle gracefully if it fails
try:
    from readability import Document
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False
    Document = None

logger = logging.getLogger(__name__)

class ScraperTool:
    """
    Production-ready web scraping tool with Playwright and cross-platform fallback support
    """
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, delay_between_requests: float = 1.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay_between_requests = delay_between_requests
        self.session_data = {}
        self.rate_limits = {}
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.use_fallback = False
        self.playwright_failed = False
        self.smartscrapergraph_failed = False
        
        # Detect Windows-specific issues
        self.is_windows = platform.system() == "Windows"
        self.is_windows_store_python = (
            self.is_windows and 
            "WindowsApps" in sys.executable and 
            "PythonSoftwareFoundation.Python" in sys.executable
        )
        
        # SmartScraperGraph API configuration
        self.scrapegraph_api_key = os.getenv("SCRAPEGRAPH_API_KEY")
        self.scrapegraph_client = None
        if self.scrapegraph_api_key and SMARTSCRAPERGRAPH_API_AVAILABLE:
            try:
                self.scrapegraph_client = Client(api_key=self.scrapegraph_api_key)
                logger.info("SmartScraperGraph API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize SmartScraperGraph API client: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                self.scrapegraph_client = None
        else:
            logger.info(f"SmartScraperGraph API not available: api_key={bool(self.scrapegraph_api_key)}, package_available={SMARTSCRAPERGRAPH_API_AVAILABLE}")
    
    async def scrape_url(self, url: str, selectors: Optional[List[str]] = None, 
                        timeout: Optional[int] = None, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape content from a URL with SmartScraperGraph, Playwright and fallback support
        """
        timeout = timeout or self.timeout
        
        # Try SmartScraperGraph API first if available and configured
        if (not self.smartscrapergraph_failed and self.scrapegraph_client and prompt):
            try:
                return await self._scrape_with_smartscrapergraph_api(url, prompt, timeout)
            except Exception as e:
                logger.warning(f"SmartScraperGraph API failed: {str(e)}")
                logger.info("Falling back to Playwright scraping method")
                # Don't mark as failed permanently, might be temporary issue
        
        # Try Playwright second, then fallback if it fails
        if not self.playwright_failed and PLAYWRIGHT_AVAILABLE:
            try:
                return await self._scrape_with_playwright(url, selectors, timeout)
            except (NotImplementedError, OSError, Exception) as e:
                logger.warning(f"Playwright failed on {platform.system()}: {str(e)}")
                if "NotImplementedError" in str(e) or "subprocess" in str(e).lower():
                    logger.info("Switching to fallback scraping method for Windows compatibility")
                    self.playwright_failed = True
                else:
                    # Re-raise if it's not a Windows subprocess issue
                    raise
        
        # Use fallback method
        return await self._scrape_with_fallback(url, selectors, timeout)
    
    async def _scrape_with_smartscrapergraph_api(self, url: str, prompt: str, 
                                               timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Scrape using SmartScraperGraph API (primary method)
        """
        timeout = timeout or self.timeout
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Scraping URL with SmartScraperGraph API: {url} (attempt {attempt + 1}/{self.max_retries})")
                
                # Validate URL
                if not self._is_valid_url(url):
                    raise ValueError(f"Invalid URL: {url}")
                
                # Use the API client to scrape
                response = self.scrapegraph_client.smartscraper(
                    website_url=url,
                    user_prompt=prompt
                )
                
                # Get the result from API response
                result = response
                
                # Log the raw SmartScraperGraph API result
                logger.info(f"🤖 SmartScraperGraph API RAW RESULT for {url}:")
                logger.info(f"📊 Result type: {type(result)}")
                logger.info(f"📄 Raw result: {json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)}")
                
                # Convert result to string if it's not already
                if isinstance(result, dict):
                    content = json.dumps(result, indent=2)
                elif isinstance(result, list):
                    content = json.dumps(result, indent=2)
                else:
                    content = str(result)
                
                # Log the processed content
                logger.info(f"📝 PROCESSED CONTENT for {url}:")
                logger.info(f"📄 Content length: {len(content)} characters")
                logger.info(f"🔍 Content preview: {content[:500]}...")
                
                # Extract financial data and business metrics from the structured result
                financial_data = self.extract_financial_data(content)
                business_metrics = self.extract_business_metrics(content)
                
                # If result is a dict, try to extract more structured data
                if isinstance(result, dict):
                    # Look for common financial keys in the result
                    for key, value in result.items():
                        key_lower = key.lower()
                        if any(term in key_lower for term in ['revenue', 'sales', 'income']):
                            financial_data['revenue'] = str(value)
                        elif any(term in key_lower for term in ['profit', 'margin', 'ebitda']):
                            financial_data['profit_margin'] = str(value)
                        elif any(term in key_lower for term in ['growth', 'increase']):
                            financial_data['growth_rate'] = str(value)
                        elif any(term in key_lower for term in ['employee', 'staff', 'team']):
                            business_metrics['employees'] = value
                        elif any(term in key_lower for term in ['founded', 'established', 'started']):
                            business_metrics['founded_year'] = value
                        elif any(term in key_lower for term in ['location', 'address', 'based']):
                            business_metrics['location'] = str(value)
                
                # Log extracted data
                logger.info(f"💰 FINANCIAL DATA extracted from {url}: {financial_data}")
                logger.info(f"📊 BUSINESS METRICS extracted from {url}: {business_metrics}")
                
                scraper_result = {
                    "url": url,
                    "content": content,
                    "raw_result": result,  # Include the raw SmartScraperGraph result
                    "financial_data": financial_data,
                    "business_metrics": business_metrics,
                    "metadata": {
                        "fetched_at": datetime.now().isoformat(),
                        "prompt_used": prompt,
                        "timeout": timeout,
                        "status": "success",
                        "attempt": attempt + 1,
                        "content_length": len(content),
                        "scraping_method": "smartscrapergraph"
                    }
                }
                
                logger.info(f"✅ Successfully scraped URL with SmartScraperGraph: {url}")
                logger.info(f"📋 FINAL RESULT SUMMARY:")
                logger.info(f"   - Content: {len(content)} chars")
                logger.info(f"   - Financial data: {len(financial_data)} items")
                logger.info(f"   - Business metrics: {len(business_metrics)} items")
                logger.info(f"   - Method: smartscrapergraph")
                
                return scraper_result
                
            except Exception as e:
                logger.error(f"Error scraping URL {url} with SmartScraperGraph on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    # Mark as failed and return error result
                    error_result = self._create_error_result(url, f"SmartScraperGraph failed after {self.max_retries} attempts: {str(e)}")
                    error_result["metadata"]["scraping_method"] = "smartscrapergraph_failed"
                    return error_result
                await asyncio.sleep(self.delay_between_requests * (attempt + 1))
        
        return self._create_error_result(url, f"SmartScraperGraph failed after {self.max_retries} attempts")
    
    async def _scrape_with_playwright(self, url: str, selectors: Optional[List[str]] = None, 
                                    timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Scrape using Playwright (original implementation)
        """
        timeout = timeout or self.timeout
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Scraping URL with Playwright: {url} (attempt {attempt + 1}/{self.max_retries})")
                
                # Validate URL
                if not self._is_valid_url(url):
                    raise ValueError(f"Invalid URL: {url}")
                
                # Initialize browser if needed
                await self._ensure_browser()
                
                # Create new page
                page = await self.browser.new_page()
                
                try:
                    # Set comprehensive headers to avoid bot detection
                    await page.set_extra_http_headers({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0'
                    })
                    
                    # Set viewport to simulate real browser
                    await page.set_viewport_size({"width": 1920, "height": 1080})
                    
                    # Navigate to URL with timeout
                    await page.goto(url, timeout=timeout * 1000, wait_until='domcontentloaded')
                    
                    # Wait for page to stabilize
                    await page.wait_for_timeout(1000)
                    
                    # Get page content
                    html_content = await page.content()
                    
                    # Extract content based on selectors or full page
                    if selectors:
                        extracted_content = await self._extract_with_selectors(page, selectors)
                    else:
                        extracted_content = await self._extract_full_content(html_content)
                    
                    # Clean and structure the content
                    cleaned_content = self.clean_and_structure_content(extracted_content)
                    
                    # Extract financial data and business metrics
                    financial_data = self.extract_financial_data(cleaned_content)
                    business_metrics = self.extract_business_metrics(cleaned_content)
                    
                    result = {
                        "url": url,
                        "content": cleaned_content,
                        "financial_data": financial_data,
                        "business_metrics": business_metrics,
                        "metadata": {
                            "fetched_at": datetime.now().isoformat(),
                            "selectors_used": selectors or [],
                            "timeout": timeout,
                            "status": "success",
                            "attempt": attempt + 1,
                            "content_length": len(cleaned_content)
                        }
                    }
                    
                    logger.info(f"Successfully scraped URL: {url}")
                    return result
                    
                finally:
                    await page.close()
                    
            except PlaywrightTimeoutError as e:
                logger.warning(f"Timeout scraping URL {url} on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return self._create_error_result(url, f"Timeout after {self.max_retries} attempts: {str(e)}")
                await asyncio.sleep(self.delay_between_requests * (attempt + 1))
                
            except Exception as e:
                logger.error(f"Error scraping URL {url} on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return self._create_error_result(url, f"Failed after {self.max_retries} attempts: {str(e)}")
                await asyncio.sleep(self.delay_between_requests * (attempt + 1))
        
        return self._create_error_result(url, f"Failed after {self.max_retries} attempts")
    
    async def _scrape_with_fallback(self, url: str, selectors: Optional[List[str]] = None, 
                                  timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Fallback scraping method using aiohttp + BeautifulSoup (Windows-compatible)
        """
        timeout = timeout or self.timeout
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Scraping URL with fallback method: {url} (attempt {attempt + 1}/{self.max_retries})")
                
                # Validate URL
                if not self._is_valid_url(url):
                    raise ValueError(f"Invalid URL: {url}")
                
                # Use aiohttp for HTTP requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            raise Exception(f"HTTP {response.status}: {response.reason}")
                        
                        html_content = await response.text()
                
                # Extract content using BeautifulSoup
                if selectors:
                    extracted_content = self._extract_with_selectors_fallback(html_content, selectors)
                else:
                    extracted_content = self._extract_full_content_fallback(html_content)
                
                # Clean and structure the content
                cleaned_content = self.clean_and_structure_content(extracted_content)
                
                # Extract financial data and business metrics
                financial_data = self.extract_financial_data(cleaned_content)
                business_metrics = self.extract_business_metrics(cleaned_content)
                
                result = {
                    "url": url,
                    "content": cleaned_content,
                    "financial_data": financial_data,
                    "business_metrics": business_metrics,
                    "metadata": {
                        "fetched_at": datetime.now().isoformat(),
                        "selectors_used": selectors or [],
                        "timeout": timeout,
                        "status": "success",
                        "attempt": attempt + 1,
                        "content_length": len(cleaned_content),
                        "scraping_method": "fallback_aiohttp"
                    }
                }
                
                logger.info(f"Successfully scraped URL with fallback: {url}")
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout scraping URL {url} on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    return self._create_error_result(url, f"Timeout after {self.max_retries} attempts")
                await asyncio.sleep(self.delay_between_requests * (attempt + 1))
                
            except Exception as e:
                logger.error(f"Error scraping URL {url} on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return self._create_error_result(url, f"Failed after {self.max_retries} attempts: {str(e)}")
                await asyncio.sleep(self.delay_between_requests * (attempt + 1))
        
        return self._create_error_result(url, f"Failed after {self.max_retries} attempts")
    
    def _extract_with_selectors_fallback(self, html_content: str, selectors: List[str]) -> str:
        """
        Extract content using CSS selectors with BeautifulSoup (fallback method)
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        extracted_parts = []
        
        for selector in selectors:
            try:
                # Convert simple selectors to BeautifulSoup format
                if selector.startswith('[class*='):
                    # Convert [class*="about"] to class containing "about"
                    class_name = selector.split('"')[1]
                    elements = soup.find_all(attrs={"class": lambda x: x and class_name in ' '.join(x)})
                elif selector.startswith('[id*='):
                    # Convert [id*="about"] to id containing "about"
                    id_name = selector.split('"')[1]
                    elements = soup.find_all(attrs={"id": lambda x: x and id_name in x})
                elif selector.startswith('.'):
                    # Class selector
                    class_name = selector[1:]
                    elements = soup.find_all(class_=class_name)
                elif selector.startswith('#'):
                    # ID selector
                    id_name = selector[1:]
                    elements = soup.find_all(id=id_name)
                else:
                    # Tag selector
                    elements = soup.find_all(selector)
                
                for element in elements:
                    text = element.get_text(strip=True)
                    if text:
                        extracted_parts.append(text)
                        
            except Exception as e:
                logger.warning(f"Error extracting with selector '{selector}': {str(e)}")
        
        return "\n".join(extracted_parts)
    
    def _extract_full_content_fallback(self, html_content: str) -> str:
        """
        Extract main content from full HTML using readability (fallback method)
        """
        try:
            if READABILITY_AVAILABLE and Document:
                doc = Document(html_content)
                return doc.summary()
            else:
                raise ImportError("Readability not available")
        except Exception as e:
            logger.warning(f"Readability extraction failed: {str(e)}, using BeautifulSoup")
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
    
    async def batch_scrape(self, urls: List[str], selectors: Optional[List[str]] = None, 
                          timeout: Optional[int] = None, prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs in batch with rate limiting
        """
        results = []
        
        for i, url in enumerate(urls):
            if i > 0:
                # Add delay between requests to be respectful
                await asyncio.sleep(self.delay_between_requests)
            
            result = await self.scrape_url(url, selectors, timeout, prompt)
            results.append(result)
            
            logger.info(f"Batch scrape progress: {i + 1}/{len(urls)}")
        
        return results
    
    def scrape_website(self, url: str, prompt: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for SmartScraperGraph scraping (matches your requested function signature)
        """
        if not SMARTSCRAPERGRAPH_AVAILABLE:
            raise ImportError("SmartScraperGraph is not available. Please install scrapegraphai.")
        
        if not self.deepseek_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured in environment variables.")
        
        try:
            # Create graph instance
            smart_scraper_graph = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=self.graph_config
            )
            
            # Run the scraper
            result = smart_scraper_graph.run()
            return result
            
        except Exception as e:
            logger.error(f"Error in scrape_website: {str(e)}")
            raise
    
    async def _ensure_browser(self):
        """
        Ensure browser is initialized with Windows compatibility
        """
        if not self.playwright and PLAYWRIGHT_AVAILABLE:
            try:
                # Windows-specific event loop handling
                if self.is_windows:
                    # Ensure we're using the correct event loop policy
                    try:
                        loop = asyncio.get_running_loop()
                        if not isinstance(loop, asyncio.ProactorEventLoop):
                            logger.warning("Windows detected but not using ProactorEventLoop, switching to fallback")
                            self.playwright_failed = True
                            return
                    except Exception as loop_error:
                        logger.warning(f"Event loop check failed: {loop_error}, using fallback")
                        self.playwright_failed = True
                        return
                
                self.playwright = await async_playwright().start()
                
                # Windows-specific browser launch options
                launch_options = {
                    'headless': True,
                    'args': ['--no-sandbox', '--disable-dev-shm-usage']
                }
                
                # Additional Windows compatibility options
                if self.is_windows:
                    launch_options['args'].extend([
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                        '--disable-extensions',
                        '--no-first-run',
                        '--disable-default-apps',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-features=TranslateUI',
                        '--disable-ipc-flooding-protection'
                    ])
                    
                    # Windows Store Python specific fixes
                    if self.is_windows_store_python:
                        launch_options['args'].extend([
                            '--no-zygote',
                            '--single-process'
                        ])
                
                # Try different browsers in order of preference
                browsers_to_try = ['chromium', 'firefox', 'webkit']
                
                for browser_name in browsers_to_try:
                    try:
                        browser_launcher = getattr(self.playwright, browser_name)
                        self.browser = await browser_launcher.launch(**launch_options)
                        logger.info(f"Successfully launched {browser_name} browser on {platform.system()}")
                        break
                    except Exception as browser_error:
                        logger.warning(f"Failed to launch {browser_name}: {str(browser_error)}")
                        # If it's a subprocess error on Windows, switch to fallback immediately
                        if self.is_windows and ("subprocess" in str(browser_error).lower() or 
                                              "NotImplementedError" in str(browser_error)):
                            logger.info("Detected Windows subprocess issue, switching to fallback")
                            self.playwright_failed = True
                            return
                        continue
                
                if not self.browser:
                    logger.warning("Failed to launch any browser, switching to fallback")
                    self.playwright_failed = True
                    return
                    
            except Exception as e:
                logger.error(f"Failed to initialize Playwright: {str(e)}")
                # Check if it's a Windows-specific subprocess error
                if self.is_windows and ("subprocess" in str(e).lower() or 
                                      "NotImplementedError" in str(e) or
                                      "ProactorEventLoop" in str(e)):
                    logger.info("Detected Windows compatibility issue, switching to fallback")
                self.playwright_failed = True
                return
    
    async def _extract_with_selectors(self, page: Page, selectors: List[str]) -> str:
        """
        Extract content using CSS selectors
        """
        extracted_parts = []
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    text = await element.inner_text()
                    if text.strip():
                        extracted_parts.append(text.strip())
            except Exception as e:
                logger.warning(f"Error extracting with selector '{selector}': {str(e)}")
        
        return "\n".join(extracted_parts)
    
    async def _extract_full_content(self, html_content: str) -> str:
        """
        Extract main content from full HTML using readability
        """
        try:
            if READABILITY_AVAILABLE and Document:
                doc = Document(html_content)
                return doc.summary()
            else:
                raise ImportError("Readability not available")
        except Exception as e:
            logger.warning(f"Readability extraction failed: {str(e)}, falling back to BeautifulSoup")
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
    
    def clean_and_structure_content(self, raw_content: str) -> str:
        """
        Clean and structure extracted content
        """
        if not raw_content:
            return ""
        
        # Remove HTML tags if any remain
        soup = BeautifulSoup(raw_content, 'html.parser')
        text = soup.get_text()
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # Trim and return
        return text.strip()
    
    def extract_financial_data(self, content: str) -> Dict[str, Any]:
        """
        Extract financial data and metrics from scraped content
        """
        financial_data = {}
        
        # Revenue patterns
        revenue_patterns = [
            r'revenue[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:million|billion|k|m|b)?',
            r'sales[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:million|billion|k|m|b)?',
            r'turnover[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:million|billion|k|m|b)?',
            r'generated\s+\$?([\d,]+(?:\.\d+)?)\s*(?:million|billion|k|m|b)?\s+in\s+revenue',
            r'achieved\s+\$?([\d,]+(?:\.\d+)?)\s*(?:million|billion|k|m|b)?\s+in\s+revenue'
        ]
        
        for pattern in revenue_patterns:
            matches = re.findall(pattern, content.lower())
            if matches:
                financial_data['revenue'] = matches[0]
                break
        
        # Profit/margin patterns
        profit_patterns = [
            r'profit[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:million|billion|k|m|b|%)?',
            r'margin[:\s]+([\d,]+(?:\.\d+)?)\s*%',
            r'ebitda[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:million|billion|k|m|b)?',
            r'profit\s+margin\s+is\s+([\d,]+(?:\.\d+)?)\s*%',
            r'profit\s+margin\s+of\s+([\d,]+(?:\.\d+)?)\s*%'
        ]
        
        for pattern in profit_patterns:
            matches = re.findall(pattern, content.lower())
            if matches:
                financial_data['profit_margin'] = matches[0]
                break
        
        # Growth rate patterns
        growth_patterns = [
            r'growth[:\s]+([\d,]+(?:\.\d+)?)\s*%',
            r'increase[:\s]+([\d,]+(?:\.\d+)?)\s*%',
            r'up[:\s]+([\d,]+(?:\.\d+)?)\s*%',
            r'seen\s+([\d,]+(?:\.\d+)?)\s*%\s+growth',
            r'growth\s+rate\s+of\s+([\d,]+(?:\.\d+)?)\s*%'
        ]
        
        for pattern in growth_patterns:
            matches = re.findall(pattern, content.lower())
            if matches:
                financial_data['growth_rate'] = matches[0]
                break
        
        return financial_data
    
    def extract_business_metrics(self, content: str) -> Dict[str, Any]:
        """
        Extract business metrics and key information from scraped content
        """
        metrics = {}
        
        # Employee count patterns
        employee_patterns = [
            r'(\d+)\s+employees?',
            r'team\s+of\s+(\d+)',
            r'staff\s+of\s+(\d+)',
            r'workforce\s+of\s+(\d+)'
        ]
        
        for pattern in employee_patterns:
            matches = re.findall(pattern, content.lower())
            if matches:
                metrics['employees'] = int(matches[0])
                break
        
        # Founded year patterns
        founded_patterns = [
            r'founded\s+in\s+(\d{4})',
            r'established\s+in\s+(\d{4})',
            r'since\s+(\d{4})',
            r'started\s+in\s+(\d{4})'
        ]
        
        for pattern in founded_patterns:
            matches = re.findall(pattern, content.lower())
            if matches:
                metrics['founded_year'] = int(matches[0])
                break
        
        # Location patterns
        location_patterns = [
            r'based\s+in\s+([^,\n]+)',
            r'located\s+in\s+([^,\n]+)',
            r'headquarters\s+in\s+([^,\n]+)'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, content.lower())
            if matches:
                metrics['location'] = matches[0].strip()
                break
        
        # Industry/sector keywords
        industry_keywords = [
            'technology', 'software', 'fintech', 'healthcare', 'manufacturing',
            'retail', 'consulting', 'marketing', 'finance', 'education',
            'real estate', 'construction', 'automotive', 'energy', 'telecommunications'
        ]
        
        content_lower = content.lower()
        detected_industries = [keyword for keyword in industry_keywords if keyword in content_lower]
        if detected_industries:
            metrics['industry_keywords'] = detected_industries
        
        return metrics
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _create_error_result(self, url: str, error_message: str) -> Dict[str, Any]:
        """
        Create standardized error result
        """
        return {
            "url": url,
            "content": "",
            "financial_data": {},
            "business_metrics": {},
            "metadata": {
                "fetched_at": datetime.now().isoformat(),
                "error": error_message,
                "status": "error",
                "scraping_method": "fallback_aiohttp" if self.playwright_failed else "playwright",
                "platform": platform.system(),
                "is_windows_store_python": self.is_windows_store_python
            }
        }
    
    async def get_scraping_status(self, url: str) -> Dict[str, Any]:
        """
        Get status of scraping for a URL
        """
        if url in self.session_data:
            return {
                "url": url,
                "status": "cached",
                "last_scraped": self.session_data[url].get("timestamp", "unknown"),
                "content_length": len(self.session_data[url].get("content", ""))
            }
        else:
            return {
                "url": url,
                "status": "not_scraped",
                "last_scraped": None,
                "content_length": 0
            }
    
    async def clear_cache(self, url: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear scraping cache
        """
        if url:
            if url in self.session_data:
                del self.session_data[url]
            return {"status": "cleared", "url": url}
        else:
            self.session_data.clear()
            return {"status": "cleared", "message": "All cache cleared"}
    
    async def close(self):
        """
        Clean up browser resources (handles both Playwright and fallback)
        """
        try:
            if self.browser and PLAYWRIGHT_AVAILABLE:
                await self.browser.close()
                self.browser = None
            
            if self.playwright and PLAYWRIGHT_AVAILABLE:
                await self.playwright.stop()
                self.playwright = None
                
            logger.info("Browser resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up browser resources: {str(e)}")
    
    async def __aenter__(self):
        """
        Async context manager entry
        """
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit
        """
        await self.close()

# Standalone execution
async def main():
    """
    Standalone execution for testing
    """
    async with ScraperTool(timeout=15, max_retries=2) as scraper:
        # Test SmartScraperGraph scrape if available
        if SMARTSCRAPERGRAPH_AVAILABLE and scraper.deepseek_key:
            print("Testing SmartScraperGraph scrape...")
            try:
                result = await scraper.scrape_url(
                    "https://example.com", 
                    prompt="Extract the main content and any business information from this website"
                )
                print(f"SmartScraperGraph result: {result}")
            except Exception as e:
                print(f"SmartScraperGraph test failed: {e}")
        
        # Test single URL scrape with Playwright fallback
        print("Testing Playwright fallback scrape...")
        result = await scraper.scrape_url("https://example.com")
        print(f"Single scrape result: {result['metadata']['status']}")
        print(f"Content length: {len(result['content'])}")
        print(f"Financial data: {result['financial_data']}")
        print(f"Business metrics: {result['business_metrics']}")
        
        # Test batch scrape
        print("\nTesting batch scrape...")
        urls = [
            "https://httpbin.org/html",
            "https://example.com",
            "https://httpstat.us/200"
        ]
        batch_results = await scraper.batch_scrape(urls)
        print(f"Batch scrape results: {len(batch_results)}")
        
        successful_scrapes = [r for r in batch_results if r['metadata']['status'] == 'success']
        print(f"Successful scrapes: {len(successful_scrapes)}")

if __name__ == "__main__":
    asyncio.run(main()) 