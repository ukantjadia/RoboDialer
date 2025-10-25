# Scraper worker entrypoint
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import sys
import os

# Add the parent directory to the path to import the scraper tool
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.scraper import ScraperTool

# Import agentic logging
from agentic_logging import get_agentic_logger

logger = get_agentic_logger('workers.scraper')

class ScraperWorker:
    """
    Web scraper worker for extracting content from URLs using enhanced ScraperTool
    """
    
    def __init__(self):
        self.session_data = {}
        self.scraper_tool = ScraperTool(timeout=30, max_retries=3)
    
    async def scrape_url(self, url: str, selectors: Optional[list] = None, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape content from a given URL using SmartScraperGraph, Playwright, or fallback methods
        """
        try:
            logger.info(f"Starting scrape for URL: {url}")
            
            # Use the enhanced scraper tool with SmartScraperGraph support
            result = await self.scraper_tool.scrape_url(url, selectors, prompt=prompt)
            
            logger.info(f"Successfully scraped URL: {url}")
            return result
            
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {str(e)}")
            return {
                "url": url,
                "content": "",
                "financial_data": {},
                "business_metrics": {},
                "metadata": {
                    "fetched_at": datetime.now().isoformat(),
                    "error": str(e),
                    "status": "error"
                }
            }
    
    async def batch_scrape(self, urls: list, selectors: Optional[list] = None, prompt: Optional[str] = None) -> list:
        """
        Scrape multiple URLs in batch using the enhanced scraper tool
        """
        try:
            results = await self.scraper_tool.batch_scrape(urls, selectors, prompt=prompt)
            return results
        except Exception as e:
            logger.error(f"Batch scrape error: {str(e)}")
            return []
    
    async def close(self):
        """
        Clean up scraper resources
        """
        try:
            await self.scraper_tool.close()
        except Exception as e:
            logger.error(f"Error closing scraper tool: {str(e)}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

# Standalone execution
async def main():
    """
    Standalone execution for testing
    """
    async with ScraperWorker() as worker:
        # Test SmartScraperGraph scrape with prompt
        print("Testing SmartScraperGraph scrape...")
        result = await worker.scrape_url(
            "https://example.com", 
            prompt="Extract company information, financial data, and business metrics from this website"
        )
        print(f"SmartScraperGraph result: {result}")
        
        # Test fallback scrape without prompt
        print("Testing fallback scrape...")
        result = await worker.scrape_url("https://example.com")
        print(f"Fallback scrape result: {result}")
        
        # Test batch scrape
        urls = [
            "https://example.com",
            "https://httpbin.org/html"
        ]
        batch_results = await worker.batch_scrape(
            urls, 
            prompt="Extract the main content and any business information from this website"
        )
        print(f"Batch scrape results: {batch_results}")

if __name__ == "__main__":
    asyncio.run(main()) 