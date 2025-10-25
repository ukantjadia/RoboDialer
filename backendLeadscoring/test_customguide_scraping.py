import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.enhanced_scraping_service import EnhancedScrapingService

async def test_customguide_scraping():
    print("🔍 TESTING CUSTOMGUIDE WEBSITE SCRAPING")
    print("=" * 50)
    
    # Test data for CustomGuide
    company_name = "CustomGuide Training"
    website_url = "http://www.customguide.com/"
    keywords = ["training", "courses", "education", "AI"]
    city = "Minneapolis"
    state = "MN"
    
    print(f"🌐 Testing website: {website_url}")
    print(f"🏢 Company: {company_name}")
    print(f"📍 Location: {city}, {state}")
    print(f"🔑 Keywords: {keywords}")
    print()
    
    try:
        # Initialize the scraping service
        scraper = EnhancedScrapingService(None)
        
        # Attempt to scrape the website
        print("🔄 Attempting to scrape website...")
        result = await scraper.scrape_company(company_name, website_url, keywords, city, state)
        
        print("✅ Scraping completed!")
        print(f"📄 Text snippet length: {len(result.get('text_snippet', ''))}")
        print(f"🔗 Final URL: {result.get('final_url', 'N/A')}")
        print(f"📊 Success: {result.get('success', False)}")
        
        if result.get('text_snippet'):
            print("\n📝 Sample text (first 500 chars):")
            print("-" * 40)
            print(result['text_snippet'][:500] + "...")
        else:
            print("\n❌ No text content extracted")
            
    except Exception as e:
        print(f"❌ Error during scraping: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_customguide_scraping()) 