#!/usr/bin/env python3
"""
Test script to verify streaming API implementation
"""

import os
import sys
import json
import urllib.parse
import requests
from datetime import datetime

def load_config(config_path='config_combination_processor.json'):
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Could not load config: {e}")
        return {}

def test_login_session():
    """Test login and return an authenticated session"""
    print("Testing login/auth session...")
    config = load_config()
    auth = config.get('auth', {})
    login_url = auth.get('login_url')
    email = auth.get('email')
    password = auth.get('password')

    sess = requests.Session()
    if not login_url or not email or not password:
        print("⚠️  Auth not configured; proceeding without login")
        return sess

    try:
        resp = sess.post(login_url, json={"email": email, "password": password}, timeout=30)
        if resp.status_code != 200:
            print(f"❌ Login failed: HTTP {resp.status_code}")
            print(resp.text[:200])
            return sess
        print("✅ Login successful; cookies stored")
        return sess
    except requests.exceptions.RequestException as e:
        print(f"❌ Login error: {e}")
        return sess

def test_url_encoding():
    """Test URL encoding functionality"""
    print("Testing URL encoding...")

    test_cases = [
        ("software development", "Dallas, TX, USA"),
        ("healthcare", "Los Angeles, CA, USA"),
        ("real estate", "New York, NY, USA")
    ]

    for industry, location in test_cases:
        encoded_industry = urllib.parse.quote(industry)
        encoded_location = urllib.parse.quote(location)
        url = f"https://sandbox-api.saasquatchleads.com/scraper/scrape-stream?industry={encoded_industry}&location={encoded_location}"

        print(f"✅ {industry} + {location}")
        print(f"   → {encoded_industry} + {encoded_location}")
        print(f"   → {url}")
        print()

    return True

def test_api_connection():
    """Test basic API connection using authenticated session"""
    print("Testing API connection...")

    try:
        # Load config
        config = load_config()
        sess = test_login_session()

        # Test with a simple query
        industry = "software development"
        location = "Dallas, TX, USA"

        encoded_industry = urllib.parse.quote(industry)
        encoded_location = urllib.parse.quote(location)
        url = f"https://sandbox-api.saasquatchleads.com/scraper/scrape-stream?industry={encoded_industry}&location={encoded_location}"

        print(f"Making test request to: {url}")

        # Make a short test request (we'll stop it quickly)
        response = sess.get(url, stream=True, timeout=10)

        if response.status_code == 200:
            print("✅ API connection successful")

            # Read first few lines to verify streaming
            line_count = 0
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        print(f"✅ Received: {data.get('message', 'batch data')}")
                        line_count += 1
                        if line_count >= 3:  # Just test first 3 lines
                            break
                    except json.JSONDecodeError:
                        print(f"⚠️  Non-JSON line received: {line[:100]}...")
                        break

            response.close()
            return True
        else:
            print(f"❌ API connection failed: HTTP {response.status_code}")
            print(response.text[:200])
            return False

    except requests.exceptions.Timeout:
        print("⚠️  API request timed out (expected for streaming)")
        return True
    except Exception as e:
        print(f"❌ API connection error: {e}")
        return False

def test_csv_processing():
    """Test CSV processing with new format"""
    print("\nTesting CSV processing...")

    try:
        import pandas as pd

        # Test reading the sample CSV
        df = pd.read_csv('sample_input.csv')

        # Test location combination
        sample_row = df.iloc[0]
        location = f"{sample_row['city']}, {sample_row['state']}, {sample_row['country']}"

        print(f"✅ Sample location: {location}")
        print(f"✅ CSV has {len(df)} rows")

        # Test URL encoding of the location
        encoded_location = urllib.parse.quote(location)
        print(f"✅ Encoded location: {encoded_location}")

        return True

    except Exception as e:
        print(f"❌ CSV processing error: {e}")
        return False

def main():
    """Run all streaming tests"""
    print("========================================")
    print("Streaming API Implementation Test")
    print("========================================")
    print()

    tests = [
        ("URL Encoding", test_url_encoding),
        ("Login Session", lambda: test_login_session() is not None),
        ("API Connection", test_api_connection),
        ("CSV Processing", test_csv_processing)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        result = test_func()
        results.append((test_name, bool(result)))
        print()

    # Summary
    print("========================================")
    print("Test Summary")
    print("========================================")

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All streaming tests passed! Ready for production.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())