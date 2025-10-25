#!/usr/bin/env python3
"""
Simple wrapper script to run the combination processor
"""

import os
import sys
import json
from datetime import datetime
from combination_api_processor import CombinationProcessor

def load_config(config_file='config_combination_processor.json'):
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Config file {config_file} not found, using defaults")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing config file: {e}")
        return {}

def make_timestamped_filename(base_name: str) -> str:
    """Return base_name with _YYYYMMDD_HHMMSS before .csv"""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    if base_name.lower().endswith('.csv'):
        stem = base_name[:-4]
        return f"{stem}_{ts}.csv"
    return f"{base_name}_{ts}.csv"

def main():
    # Default values
    input_csv = 'sample_input.csv'
    base_output_csv = 'results_output.csv'
    output_csv = make_timestamped_filename(base_output_csv)

    # Load configuration
    config = load_config()

    # Get settings from config or use defaults
    api_url = config.get('api_settings', {}).get('url', 'https://sandbox-api.saasquatchleads.com/scraper/scrape-stream')
    max_workers = config.get('resource_limits', {}).get('max_workers', 1)
    max_memory = config.get('resource_limits', {}).get('max_memory_percent', 70.0)
    max_cpu = config.get('resource_limits', {}).get('max_cpu_percent', 50.0)
    calls_per_second = config.get('resource_limits', {}).get('calls_per_second', 0.1)
    batch_size = config.get('resource_limits', {}).get('batch_size', 10)
    industry_col = config.get('csv_settings', {}).get('industry_column', 'industry')
    city_col = config.get('csv_settings', {}).get('city_column', 'city')
    state_col = config.get('csv_settings', {}).get('state_column', 'state')
    country_col = config.get('csv_settings', {}).get('country_column', 'country')

    # Auth settings
    auth_settings = config.get('auth', {
        'login_url': None,
        'email': None,
        'password': None,
    })

    # Check if input file exists
    if not os.path.exists(input_csv):
        print(f"Input file {input_csv} not found!")
        print("Please create a CSV file with 'industry', 'city', 'state', and 'country' columns")
        print("Example format:")
        print("industry,city,state,country")
        print("software development,Dallas,TX,USA")
        print("healthcare,Los Angeles,CA,USA")
        sys.exit(1)

    print("=== CSV Combination API Processor ===")
    print(f"Input file: {input_csv}")
    print(f"Output file: {output_csv}")
    print(f"API URL: {api_url}")
    print(f"Max workers: {max_workers}")
    print(f"Max memory: {max_memory}%")
    print(f"Max CPU: {max_cpu}%")
    print(f"Rate limit: {calls_per_second} calls/second")
    print(f"Batch size: {batch_size}")
    if auth_settings.get('login_url'):
        print(f"Login URL: {auth_settings.get('login_url')}")
        print(f"Auth Email: {auth_settings.get('email', '***hidden***')}\n")
    print("=" * 40)

    # Create processor
    processor = CombinationProcessor(
        api_url=api_url,
        max_workers=max_workers,
        max_memory_percent=max_memory,
        max_cpu_percent=max_cpu,
        calls_per_second=calls_per_second,
        batch_size=batch_size,
        auth_settings=auth_settings
    )

    try:
        # Run processing
        processor.run(
            csv_file=input_csv,
            output_file=output_csv,
            industry_col=industry_col,
            city_col=city_col,
            state_col=state_col,
            country_col=country_col
        )
        print(f"\nProcessing completed! Results saved to {output_csv}")

    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        print(f"Partial results (if any) saved alongside {output_csv.replace('.csv','_partial.csv')}")
    except Exception as e:
        print(f"Error during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()