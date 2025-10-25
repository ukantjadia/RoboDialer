#!/usr/bin/env python3
"""
Test script for Growjo API integration
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.growjoScraper import GrowjoScraper

def test_growjo_api():
    """Test the Growjo API functionality"""
    
    print("=== Testing Growjo API Integration ===\n")
    
    # Load environment variables
    load_dotenv()
    
    # Check if credentials are set
    email = os.getenv("GROWJO_EMAIL")
    password = os.getenv("GROWJO_PASSWORD")
    
    if not email or not password:
        print("❌ GROWJO_EMAIL and GROWJO_PASSWORD must be set in .env file")
        print("Please add the following to your .env file:")
        print("GROWJO_EMAIL=your_email@example.com")
        print("GROWJO_PASSWORD=your_password")
        return False
    
    print(f"✅ Credentials found: {email}")
    
    # Create scraper instance
    scraper = GrowjoScraper()
    
    # Test initialization
    print("\n1. Testing Growjo initialization...")
    init_result = scraper.init_growjo()
    
    if init_result["success"]:
        print(f"✅ Initialization successful: {init_result['message']}")
        print(f"   Token: {init_result['token'][:50]}...")
        print(f"   Token length: {len(init_result['token'])} characters")
    else:
        print(f"❌ Initialization failed: {init_result['error']}")
        return False
    
    # Test session check
    print("\n2. Testing session validation...")
    check_result = scraper.is_growjo_init()
    
    if check_result["initialized"]:
        print(f"✅ Session is active: {check_result['message']}")
    else:
        print(f"❌ Session check failed: {check_result['error']}")
        return False
    
    # Test company enrichment (this will use the fallback for now)
    print("\n3. Testing company enrichment...")
    enrich_result = scraper.enrich_company("Test Company", "123 Main St", "New York", "NY")
    print(f"✅ Company enrichment result:")
    for key, value in enrich_result.items():
        print(f"   {key}: {value}")
    
    print("\n=== All tests completed successfully! ===")
    return True

if __name__ == "__main__":
    success = test_growjo_api()
    sys.exit(0 if success else 1) 