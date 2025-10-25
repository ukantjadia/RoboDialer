#!/usr/bin/env python3
"""
Resource-Controlled CSV Combination API Processor

This script reads a CSV file with industry and location columns,
generates all possible combinations, makes API calls with controlled resources,
and saves the results back to a CSV file.

Features:
- Memory usage monitoring and control
- CPU usage limiting
- Rate limiting for API calls
- Progress tracking and resumability
- Error handling and logging
- Background processing with low resource impact
"""

import pandas as pd
import requests
import json
import time
import logging
import os
import sys
from itertools import product
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Event
import psutil
import signal
from datetime import datetime
import argparse
from typing import List, Dict, Tuple, Optional
import queue
import threading
import urllib.parse
import csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'combination_processor.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ResourceController:
    """Controls system resource usage"""

    def __init__(self, max_memory_percent: float = 70.0, max_cpu_percent: float = 50.0):
        self.max_memory_percent = max_memory_percent
        self.max_cpu_percent = max_cpu_percent
        self.stop_event = Event()

    def get_memory_usage(self) -> float:
        """Get current memory usage percentage"""
        return psutil.virtual_memory().percent

    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=1)

    def should_pause(self) -> bool:
        """Check if processing should pause due to resource constraints"""
        memory_usage = self.get_memory_usage()
        cpu_usage = self.get_cpu_usage()

        if memory_usage > self.max_memory_percent or cpu_usage > self.max_cpu_percent:
            logger.warning(f"Resource usage high - Memory: {memory_usage:.1f}%, CPU: {cpu_usage:.1f}%")
            return True
        return False

    def wait_for_resources(self, check_interval: float = 5.0):
        """Wait until resources are available"""
        while self.should_pause() and not self.stop_event.is_set():
            logger.info(f"Pausing for {check_interval}s due to high resource usage...")
            time.sleep(check_interval)

class RateLimiter:
    """Controls API call rate"""

    def __init__(self, calls_per_second: float = 2.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0
        self.lock = Lock()

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_call_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_call_time = time.time()

class AuthSessionManager:
    """Manages authenticated session via login to obtain cookies"""

    def __init__(self, login_url: Optional[str] = None, email: Optional[str] = None, password: Optional[str] = None):
        self.login_url = login_url
        self.email = email
        self.password = password
        self.session: Optional[requests.Session] = None

    def is_configured(self) -> bool:
        return bool(self.login_url and self.email and self.password)

    def login(self) -> requests.Session:
        if not self.is_configured():
            # Return a basic session if no auth configured
            self.session = requests.Session()
            return self.session

        sess = requests.Session()
        payload = {"email": self.email, "password": self.password}
        try:
            logger.info("Attempting login for authenticated scraping session...")
            resp = sess.post(self.login_url, json=payload, timeout=30)
            if resp.status_code != 200:
                logger.error(f"Login failed: HTTP {resp.status_code} - {resp.text[:200]}")
                # Still return session; requests will 401/403 later if not valid
                self.session = sess
                return sess
            # Optionally validate JSON response
            try:
                resp_json = resp.json()
                logger.info(f"Login response: {json.dumps(resp_json)[:200]}")
            except Exception:
                logger.info("Login response is not JSON; proceeding with cookies present")
            self.session = sess
            logger.info("Login successful; session cookies stored.")
            return sess
        except requests.exceptions.RequestException as e:
            logger.error(f"Login request failed: {e}")
            self.session = sess
            return sess

    def ensure_session(self) -> requests.Session:
        if self.session is None:
            return self.login()
        return self.session

class CombinationProcessor:
    """Main processor for CSV combinations and API calls"""

    def __init__(self,
                 api_url: str,
                 max_workers: int = 3,
                 max_memory_percent: float = 70.0,
                 max_cpu_percent: float = 50.0,
                 calls_per_second: float = 2.0,
                 batch_size: int = 100,
                 auth_settings: Optional[Dict] = None):

        self.api_url = api_url
        self.max_workers = max_workers
        self.batch_size = batch_size

        # Initialize controllers
        self.resource_controller = ResourceController(max_memory_percent, max_cpu_percent)
        self.rate_limiter = RateLimiter(calls_per_second)

        # Authenticated session
        auth_settings = auth_settings or {}
        self.auth_manager = AuthSessionManager(
            login_url=auth_settings.get('login_url'),
            email=auth_settings.get('email'),
            password=auth_settings.get('password')
        )
        self.session = self.auth_manager.ensure_session()

        # Threading and synchronization
        self.results_lock = Lock()
        self.progress_lock = Lock()
        self.stop_event = Event()

        # Progress tracking
        self.total_combinations = 0
        self.processed_count = 0
        self.successful_count = 0
        self.failed_count = 0

        # Results storage
        self.results = []
        self.errors = []

        # Output paths (set at runtime in run())
        self.output_file_current: Optional[str] = None
        self.partial_output_file: Optional[str] = None

        # Company CSV header
        self.company_fieldnames = [
            'industry', 'location', 'scrape_timestamp', 'api_call_id', 'batch_number',
            'Company', 'Industry', 'Street', 'City', 'State', 'BBB_rating', 'Business_phone', 'Website'
        ]

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop_event.set()
        # Re-raise as KeyboardInterrupt so blocking calls are interrupted immediately
        raise KeyboardInterrupt

    def read_csv_data(self, csv_file: str, industry_col: str = 'industry',
                     city_col: str = 'city', state_col: str = 'state', country_col: str = 'country') -> Tuple[List[str], List[str]]:
        """Read industry and location data from CSV file"""
        try:
            logger.info(f"Reading CSV file: {csv_file}")
            df = pd.read_csv(csv_file)

            # Check for required columns
            required_cols = [industry_col, city_col, state_col, country_col]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Required columns {missing_cols} not found in CSV")

            # Clean and filter data
            industries = df[industry_col].dropna().astype(str).unique().tolist()

            # Combine city, state, country into location format
            locations = []
            for _, row in df.iterrows():
                if pd.notna(row[city_col]) and pd.notna(row[state_col]) and pd.notna(row[country_col]):
                    city = str(row[city_col]).strip()
                    state = str(row[state_col]).strip()
                    country = str(row[country_col]).strip()
                    location = f"{city}, {state}, {country}"
                    locations.append(location)

            # Remove empty strings and whitespace
            industries = [ind.strip() for ind in industries if ind.strip()]
            locations = list(set(locations))  # Remove duplicates

            logger.info(f"Found {len(industries)} unique industries and {len(locations)} unique locations")
            return industries, locations

        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise

    def generate_combinations(self, industries: List[str], locations: List[str]) -> List[Tuple[str, str]]:
        """Generate all possible industry-location combinations"""
        logger.info("Generating combinations...")
        combinations = list(product(industries, locations))
        self.total_combinations = len(combinations)
        logger.info(f"Generated {self.total_combinations} combinations")
        return combinations

    def _perform_stream_request(self, url: str) -> requests.Response:
        """Perform the streaming GET request with session and simple auth-retry"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        }
        resp = self.session.get(url, headers=headers, timeout=600, stream=True)
        if resp.status_code in (401, 403):
            logger.warning(f"Auth error {resp.status_code}; attempting re-login and retry...")
            self.session = self.auth_manager.login()
            resp = self.session.get(url, headers=headers, timeout=600, stream=True)
        return resp

    def _ensure_csv_with_header(self, path: str) -> None:
        try:
            needs_header = True
            if os.path.exists(path):
                # If file exists and has size > 0, assume header exists
                needs_header = os.path.getsize(path) == 0
            if needs_header:
                with open(path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.company_fieldnames)
                    writer.writeheader()
        except Exception as e:
            logger.error(f"Failed to ensure CSV header for {path}: {e}")

    def _get_company_row(self, industry: str, location: str, api_call_id: str, batch_number: int, company: Dict) -> Dict:
        return {
            'industry': industry,
            'location': location,
            'scrape_timestamp': company.get('scrape_timestamp', datetime.now().isoformat()),
            'api_call_id': api_call_id,
            'batch_number': batch_number,
            'Company': company.get('Company', ''),
            'Industry': company.get('Industry', ''),
            'Street': company.get('Street', ''),
            'City': company.get('City', ''),
            'State': company.get('State', ''),
            'BBB_rating': company.get('BBB_rating', ''),
            'Business_phone': company.get('Business_phone', ''),
            'Website': company.get('Website', '')
        }

    def _append_company_rows(self, path: str, rows: List[Dict]) -> None:
        if not rows:
            return
        try:
            self._ensure_csv_with_header(path)
            with open(path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.company_fieldnames)
                writer.writerows(rows)
        except Exception as e:
            logger.error(f"Failed to append company rows to {path}: {e}")

    def make_api_call(self, industry: str, location: str) -> Dict:
        """Make streaming API call for a single industry-location combination"""
        try:
            # Rate limiting
            self.rate_limiter.wait_if_needed()

            # URL encode parameters
            encoded_industry = urllib.parse.quote(industry)
            encoded_location = urllib.parse.quote(location)

            # Construct URL with query parameters
            url = f"{self.api_url}?industry={encoded_industry}&location={encoded_location}"

            logger.info(f"Starting streaming API call: {industry} + {location}")
            start_time = time.time()

            # Make streaming API call
            response = None
            try:
                response = self._perform_stream_request(url)

                if response.status_code == 200:
                    # Process streaming response
                    companies = []
                    api_call_id = f"{industry}_{location}_{int(start_time)}"
                    batch_count = 0
                    total_scraped = 0
                    total_processed = 0
                    elapsed_time = 0

                    logger.info(f"Stream started for {industry} + {location}")

                    buffer = ""
                    for raw_line in response.iter_lines(decode_unicode=True):
                        if self.stop_event.is_set():
                            logger.info("Stopping stream due to stop signal")
                            raise KeyboardInterrupt
                        if not raw_line:
                            # heartbeat/keepalive chunk
                            continue
                        line = raw_line.strip()
                        if not line:
                            continue
                        # Handle SSE-style prefixes
                        if line.startswith('data:'):
                            line = line[5:].strip()
                        if line.startswith(':'):
                            # SSE comment/heartbeat line
                            continue
                        # Some servers may send non-JSON notices; skip if not likely JSON
                        if not (line.startswith('{') or line.startswith('[')):
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            # Accumulate partial JSON across chunks
                            buffer += line
                            try:
                                data = json.loads(buffer)
                                buffer = ""
                            except json.JSONDecodeError:
                                # Wait for next chunk to complete JSON
                                continue

                        if data.get('message') == 'Scraper started':
                            logger.info(f"Scraper started for {industry} + {location}")
                            continue
                        if 'batch' in data:
                            batch_count += 1
                            batch_data = data
                            batch_number = batch_data.get('batch', batch_count)
                            new_items = batch_data.get('new_items', [])
                            batch_total = batch_data.get('total_scraped', 0)
                            batch_elapsed = batch_data.get('elapsed_time', 0)

                            # Process companies in this batch
                            new_rows: List[Dict] = []
                            for company in new_items:
                                # Check for duplicates (company name + industry)
                                company_key = f"{company.get('Company', '')}_{company.get('Industry', '')}"
                                if not any(c.get('company_key') == company_key for c in companies):
                                    company['company_key'] = company_key
                                    company['api_call_id'] = api_call_id
                                    company['batch_number'] = batch_number
                                    company['scrape_timestamp'] = datetime.now().isoformat()
                                    companies.append(company)
                                    # Build row for incremental save
                                    new_rows.append(self._get_company_row(industry, location, api_call_id, batch_number, company))
                            # Incrementally persist progress to partial CSV
                            if self.partial_output_file and new_rows:
                                self._append_company_rows(self.partial_output_file, new_rows)

                            total_scraped = batch_data.get('total_scraped', total_scraped)
                            total_processed = batch_data.get('processed_count', total_processed)
                            elapsed_time = batch_data.get('elapsed_time', elapsed_time)

                            logger.info(f"Batch {batch_number}: {len(new_items)} new companies, "
                                      f"Total: {total_scraped}, Elapsed: {elapsed_time:.1f}s")
                            continue
                        if data.get('message') == 'Scraping completed':
                            final_total = data.get('total_scraped', total_scraped)
                            final_processed = data.get('total_processed', total_processed)
                            final_elapsed = data.get('elapsed_time', elapsed_time)

                            logger.info(f"Stream completed for {industry} + {location}: "
                                      f"{final_total} companies, {final_processed} processed, "
                                      f"{final_elapsed:.1f}s elapsed")
                            break

                    # Calculate final elapsed time
                    final_elapsed_time = time.time() - start_time

                    return {
                        'industry': industry,
                        'location': location,
                        'status': 'success',
                        'api_call_id': api_call_id,
                        'companies': companies,
                        'total_scraped': total_scraped,
                        'total_processed': total_processed,
                        'batch_count': batch_count,
                        'elapsed_time': final_elapsed_time,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    return {
                        'industry': industry,
                        'location': location,
                        'status': 'error',
                        'error': f"HTTP {response.status_code}: {response.text}",
                        'timestamp': datetime.now().isoformat()
                    }
            except KeyboardInterrupt:
                logger.info("Interrupted by user during streaming; closing connection")
                if response is not None:
                    try:
                        response.close()
                    except Exception:
                        pass
                raise
            finally:
                if response is not None:
                    try:
                        response.close()
                    except Exception:
                        pass

        except requests.exceptions.Timeout:
            return {
                'industry': industry,
                'location': location,
                'status': 'error',
                'error': 'Request timeout (streaming took too long)',
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            return {
                'industry': industry,
                'location': location,
                'status': 'error',
                'error': f"Request failed: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'industry': industry,
                'location': location,
                'status': 'error',
                'error': f"Unexpected error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }

    def process_combination(self, combination: Tuple[str, str]) -> Dict:
        """Process a single combination with resource checking"""
        if self.stop_event.is_set():
            return None

        # Check resources before processing
        self.resource_controller.wait_for_resources()

        industry, location = combination
        logger.info(f"Starting streaming API call for: {industry} + {location}")

        result = self.make_api_call(industry, location)

        # Update progress
        with self.progress_lock:
            self.processed_count += 1
            if result['status'] == 'success':
                self.successful_count += 1
                company_count = len(result.get('companies', []))
                elapsed_time = result.get('elapsed_time', 0)
                logger.info(f"✅ Completed: {industry} + {location} - {company_count} companies in {elapsed_time:.1f}s")
            else:
                self.failed_count += 1
                logger.error(f"❌ Failed: {industry} + {location} - {result.get('error', 'Unknown error')}")

            # Log progress every combination (since streaming takes 5-8 minutes each)
            progress = (self.processed_count / self.total_combinations) * 100
            logger.info(f"📊 Progress: {progress:.1f}% ({self.processed_count}/{self.total_combinations}) - "
                      f"Success: {self.successful_count}, Failed: {self.failed_count}")

        return result

    def process_combinations_batch(self, combinations: List[Tuple[str, str]]) -> None:
        """Process combinations sequentially for streaming API calls"""
        logger.info(f"Starting sequential batch processing for {len(combinations)} combinations")

        # Process combinations sequentially since streaming API can't be concurrent
        for i, combination in enumerate(combinations):
            if self.stop_event.is_set():
                logger.info("Stopping batch processing due to stop signal")
                break

            try:
                result = self.process_combination(combination)
                if result:
                    with self.results_lock:
                        self.results.append(result)
                        if result['status'] == 'error':
                            self.errors.append(result)

                # Small delay between calls to prevent overwhelming the API
                if i < len(combinations) - 1:  # Don't delay after the last call
                    time.sleep(2)

            except Exception as e:
                logger.error(f"Error processing combination {combination}: {e}")
                with self.progress_lock:
                    self.failed_count += 1

    def save_results(self, output_file: str) -> None:
        """Save results to CSV file"""
        try:
            logger.info(f"Saving {len(self.results)} results to {output_file}")

            # Convert results to DataFrame
            df_results = pd.DataFrame(self.results)

            # For intermediate files, save API call metadata only
            if 'intermediate' in output_file or 'batch' in output_file:
                # Extract metadata for intermediate files
                metadata_data = []
                for result in self.results:
                    if result['status'] == 'success':
                        metadata = {
                            'industry': result['industry'],
                            'location': result['location'],
                            'status': result['status'],
                            'api_call_id': result.get('api_call_id', ''),
                            'total_scraped': result.get('total_scraped', 0),
                            'total_processed': result.get('total_processed', 0),
                            'batch_count': result.get('batch_count', 0),
                            'elapsed_time': result.get('elapsed_time', 0),
                            'company_count': len(result.get('companies', [])),
                            'timestamp': result['timestamp']
                        }
                    else:
                        metadata = {
                            'industry': result['industry'],
                            'location': result['location'],
                            'status': result['status'],
                            'error': result.get('error', ''),
                            'timestamp': result['timestamp']
                        }
                    metadata_data.append(metadata)

                df_metadata = pd.DataFrame(metadata_data)
                df_metadata.to_csv(output_file, index=False)
                logger.info(f"API call metadata saved to {output_file}")

            else:
                # For final output, flatten company data
                all_companies = []

                for result in self.results:
                    if result['status'] == 'success' and 'companies' in result:
                        for company in result['companies']:
                            company_row = {
                                'industry': result['industry'],
                                'location': result['location'],
                                'scrape_timestamp': company.get('scrape_timestamp', result['timestamp']),
                                'api_call_id': company.get('api_call_id', ''),
                                'batch_number': company.get('batch_number', ''),
                                'Company': company.get('Company', ''),
                                'Industry': company.get('Industry', ''),
                                'Street': company.get('Street', ''),
                                'City': company.get('City', ''),
                                'State': company.get('State', ''),
                                'BBB_rating': company.get('BBB_rating', ''),
                                'Business_phone': company.get('Business_phone', ''),
                                'Website': company.get('Website', '')
                            }
                            all_companies.append(company_row)

                if all_companies:
                    df_companies = pd.DataFrame(all_companies)
                    df_companies.to_csv(output_file, index=False)
                    logger.info(f"Company data saved to {output_file} ({len(all_companies)} companies)")
                else:
                    logger.warning("No company data to save")

            # Save errors separately if any
            if self.errors:
                error_file = output_file.replace('.csv', '_errors.csv')
                df_errors = pd.DataFrame(self.errors)
                df_errors.to_csv(error_file, index=False)
                logger.info(f"Errors saved to {error_file}")

        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise

    def run(self, csv_file: str, output_file: str,
            industry_col: str = 'industry', city_col: str = 'city',
            state_col: str = 'state', country_col: str = 'country') -> None:
        """Main execution method"""
        start_time = time.time()

        try:
            logger.info("Starting combination processing...")

            # Read CSV data
            industries, locations = self.read_csv_data(csv_file, industry_col, city_col, state_col, country_col)

            # Generate combinations
            combinations = self.generate_combinations(industries, locations)

            # Set output file for incremental saving
            self.output_file_current = output_file
            self.partial_output_file = output_file.replace('.csv', '_partial.csv')

            # Process in batches
            for i in range(0, len(combinations), self.batch_size):
                if self.stop_event.is_set():
                    logger.info("Stopping due to stop signal")
                    break

                batch = combinations[i:i + self.batch_size]
                logger.info(f"Processing batch {i//self.batch_size + 1}/{(len(combinations) + self.batch_size - 1)//self.batch_size}")

                self.process_combinations_batch(batch)

                # Save intermediate results
                if self.results:
                    intermediate_file = output_file.replace('.csv', f'_batch_{i//self.batch_size + 1}.csv')
                    self.save_results(intermediate_file)

            # Save final results
            if self.results:
                self.save_results(output_file)

            # Print final statistics
            elapsed_time = time.time() - start_time
            logger.info(f"Processing completed in {elapsed_time:.2f} seconds")
            logger.info(f"Total combinations: {self.total_combinations}")
            logger.info(f"Processed: {self.processed_count}")
            logger.info(f"Successful: {self.successful_count}")
            logger.info(f"Failed: {self.failed_count}")

        except KeyboardInterrupt:
            logger.info("Processing interrupted by user")
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            raise
        finally:
            # Save any remaining results
            if self.results:
                self.save_results(output_file.replace('.csv', '_partial.csv'))

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Process CSV combinations with API calls')
    parser.add_argument('input_csv', help='Input CSV file path')
    parser.add_argument('output_csv', help='Output CSV file path')
    parser.add_argument('--api-url', default='https://sandbox-api.saasquatchleads.com/scraper/scrape-stream',
                       help='API endpoint URL')
    parser.add_argument('--industry-col', default='industry', help='Industry column name')
    parser.add_argument('--city-col', default='city', help='City column name')
    parser.add_argument('--state-col', default='state', help='State column name')
    parser.add_argument('--country-col', default='country', help='Country column name')
    parser.add_argument('--max-workers', type=int, default=1, help='Maximum concurrent workers (use 1 for streaming)')
    parser.add_argument('--max-memory', type=float, default=70.0, help='Maximum memory usage percentage')
    parser.add_argument('--max-cpu', type=float, default=50.0, help='Maximum CPU usage percentage')
    parser.add_argument('--calls-per-second', type=float, default=0.1, help='API calls per second')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
    parser.add_argument('--login-url', default=None, help='Auth login URL for obtaining cookies')
    parser.add_argument('--email', default=None, help='Auth email')
    parser.add_argument('--password', default=None, help='Auth password')

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input_csv):
        logger.error(f"Input file not found: {args.input_csv}")
        sys.exit(1)

    # Create processor
    processor = CombinationProcessor(
        api_url=args.api_url,
        max_workers=args.max_workers,
        max_memory_percent=args.max_memory,
        max_cpu_percent=args.max_cpu,
        calls_per_second=args.calls_per_second,
        batch_size=args.batch_size,
        auth_settings={
            'login_url': args.login_url,
            'email': args.email,
            'password': args.password,
        }
    )

    # Run processing
    try:
        processor.run(
            csv_file=args.input_csv,
            output_file=args.output_csv,
            industry_col=args.industry_col,
            city_col=args.city_col,
            state_col=args.state_col,
            country_col=args.country_col
        )
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()