#!/usr/bin/env python3
"""
Test script to verify the combination processor setup
"""

import os
import sys
import json

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")

    try:
        import pandas as pd
        print("✅ pandas imported successfully")
    except ImportError as e:
        print(f"❌ pandas import failed: {e}")
        return False

    try:
        import requests
        print("✅ requests imported successfully")
    except ImportError as e:
        print(f"❌ requests import failed: {e}")
        return False

    try:
        import psutil
        print("✅ psutil imported successfully")
    except ImportError as e:
        print(f"❌ psutil import failed: {e}")
        return False

    try:
        from combination_api_processor import CombinationProcessor
        print("✅ CombinationProcessor imported successfully")
    except ImportError as e:
        print(f"❌ CombinationProcessor import failed: {e}")
        return False

    return True

def test_files():
    """Test if all required files exist"""
    print("\nTesting required files...")

    required_files = [
        'combination_api_processor.py',
        'run_combination_processor.py',
        'config_combination_processor.json',
        'requirements_combination_processor.txt',
        'sample_input.csv'
    ]

    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            all_exist = False

    return all_exist

def test_config():
    """Test if configuration file is valid"""
    print("\nTesting configuration...")

    try:
        with open('config_combination_processor.json', 'r') as f:
            config = json.load(f)

        required_keys = ['api_settings', 'resource_limits', 'csv_settings']
        for key in required_keys:
            if key in config:
                print(f"✅ {key} configuration found")
            else:
                print(f"❌ {key} configuration missing")
                return False

        # Check API URL
        api_url = config.get('api_settings', {}).get('url', '')
        if 'saasquatchleads.com' in api_url:
            print(f"✅ Streaming API URL configured: {api_url}")
        else:
            print(f"⚠️  API URL may not be streaming endpoint: {api_url}")

        # Check resource limits for streaming
        resource_limits = config.get('resource_limits', {})
        if resource_limits.get('max_workers', 0) == 1:
            print("✅ Sequential processing configured for streaming")
        else:
            print(f"⚠️  Consider setting max_workers=1 for streaming API")

        print("✅ Configuration file is valid JSON")
        return True

    except FileNotFoundError:
        print("❌ Configuration file not found")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Configuration file is not valid JSON: {e}")
        return False

def test_csv_reading():
    """Test if CSV file can be read"""
    print("\nTesting CSV reading...")

    try:
        import pandas as pd
        df = pd.read_csv('sample_input.csv')

        required_columns = ['industry', 'city', 'state', 'country']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if not missing_columns:
            print("✅ CSV file has all required columns")
            print(f"✅ Found {len(df)} rows")

            # Test location combination
            sample_row = df.iloc[0]
            location = f"{sample_row['city']}, {sample_row['state']}, {sample_row['country']}"
            print(f"✅ Sample location format: {location}")
            return True
        else:
            print(f"❌ CSV file missing required columns: {missing_columns}")
            return False

    except Exception as e:
        print(f"❌ CSV reading failed: {e}")
        return False

def main():
    """Run all tests"""
    print("========================================")
    print("Combination Processor Setup Test")
    print("========================================")
    print()

    # Get current directory
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    print()

    # Run tests
    tests = [
        ("Imports", test_imports),
        ("Files", test_files),
        ("Configuration", test_config),
        ("CSV Reading", test_csv_reading)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        result = test_func()
        results.append((test_name, result))
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
        print("🎉 All tests passed! Setup is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())