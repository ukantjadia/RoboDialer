import requests
import json
import csv
import io
import boto3
import time
import os # For accessing environment variables

# --- Configuration ---
# Change to your API endpoint URL
API_BASE_URL = "https://data.capraeleadseekers.site" 
API_UPLOAD_ENDPOINT = f"{API_BASE_URL}/api/upload_leads"

# Get API Key from environment variable.
# API Key MUST be set as an environment variable (e.g., export LEAD_API_KEY="...")
# If not set, the value will be an empty string.
API_KEY = os.getenv("LEAD_API_KEY", "") 

# Batch size for each API request
# Adjust this based on your API performance and server limits
# Start with 500-1000, then optimize as needed
BATCH_SIZE = 500 

# Local CSV file path
CSV_FOLDER_PATH = "/Users/ghaly/Documents/Project/LeadGenAI/backend-database/split_data"

# Columns that must exist in every file
REQUIRED_COLUMNS = ["company", "website", "owner_linkedin"]

# Column mapping if there are different names
COLUMN_MAPPING = {
    # Required fields
    "Company": "company",
    "Website": "website",
    "Owner's LinkedIn": "owner_linkedin",
    "LinkedIn URL": "owner_linkedin",
    
    # Owner Information
    "Owner First Name": "owner_first_name",
    "Owner Last Name": "owner_last_name",
    "Owner Email": "owner_email",
    "Email": "owner_email",  # Fallback
    "Owner Phone Number": "owner_phone_number",
    "Phone": "phone",
    "Owner Title": "owner_title",
    
    # Company Information
    "Company Phone": "company_phone",
    "Company LinkedIn": "company_linkedin",
    "Industry": "industry",
    "Product Category": "product_category",
    "Business Type": "business_type",
    "Employees": "employees",
    "Revenue": "revenue",
    "Year Founded": "year_founded",
    "BBB Rating": "bbb_rating",
    
    # Location Information
    "Street": "street",
    "City": "city",
    "State": "state",
    
    # Additional Information
    "Source": "source",
    "Status": "status",
    "Additional Notes": "additional_notes"
}

# --- Helper Functions ---

def send_batch_to_api(batch_data, batch_num, total_batches):
    """
    Send one batch of data to the upload leads API.
    Implements retry with exponential backoff for temporary failures.
    """
    headers = {
        "Content-Type": "application/json",
        **({"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}) 
    }
    max_retries = 5
    retry_delay_seconds = 2

    for attempt in range(max_retries):
        try:
            print(f"Sending batch {batch_num}/{total_batches} ({len(batch_data)} records)... Attempt {attempt + 1}/{max_retries}")
            response = requests.post(API_UPLOAD_ENDPOINT, json=batch_data, headers=headers, timeout=60) # 60 seconds timeout
            response.raise_for_status() # Will raise HTTPError for 4xx/5xx status codes

            result = response.json()
            status = result.get('status', 'unknown')
            message = result.get('message', 'No message')
            
            print(f"Batch {batch_num} sent successfully. Status: {status}, Message: {message}")
            if status == "error":
                print(f"Batch {batch_num} Error Details: {result.get('stats', {}).get('error_details', 'N/A')}")
            return True, result

        except requests.exceptions.Timeout:
            print(f"Timeout when sending batch {batch_num}. Retrying in {retry_delay_seconds} seconds...")
            time.sleep(retry_delay_seconds)
            retry_delay_seconds *= 2 # Exponential backoff
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error when sending batch {batch_num}: {e}. Retrying in {retry_delay_seconds} seconds...")
            time.sleep(retry_delay_seconds)
            retry_delay_seconds *= 2
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error when sending batch {batch_num}: {e.response.status_code} - {e.response.text}")
            # For 4xx errors (e.g., 400 Bad Request), probably don't retry because the data is wrong
            # For 5xx errors (server error), maybe retry
            if 500 <= e.response.status_code < 600:
                print(f"Retrying in {retry_delay_seconds} seconds...")
                time.sleep(retry_delay_seconds)
                retry_delay_seconds *= 2
            else:
                return False, {"status": "error", "message": f"HTTP Error {e.response.status_code}: {e.response.text}"}
        except json.JSONDecodeError:
            print(f"Failed to parse JSON response from API for batch {batch_num}. Response: {response.text}")
            return False, {"status": "error", "message": "Invalid JSON response from API"}
        except Exception as e:
            print(f"Unexpected error when sending batch {batch_num}: {e}")
            return False, {"status": "error", "message": f"Unexpected error: {str(e)}"}
    
    print(f"Failed to send batch {batch_num} after {max_retries} attempts.")
    return False, {"status": "error", "message": "Max retries exceeded for batch"}

def map_columns(row):
    mapped = {}
    # Manual mapping for required columns
    mapped['company'] = row.get('Company') or row.get('Company Name') or row.get('company') or ''
    mapped['website'] = row.get('Website') or row.get('website') or ''
    mapped['owner_linkedin'] = row.get("Owner's LinkedIn") or row.get('LinkedIn URL') or row.get('owner_linkedin') or ''
    # Map other columns according to COLUMN_MAPPING
    for k, v in row.items():
        mapped_key = COLUMN_MAPPING.get(k.strip(), k.strip())
        if mapped_key not in mapped:  # Don't overwrite required columns
            mapped[mapped_key] = v
    return mapped

# --- Main Import Script ---

def import_leads_from_folder():
    # Process all part_*.csv files
    files = [f for f in os.listdir(CSV_FOLDER_PATH)
             if f.endswith('.csv') and f.startswith('part_')]
    # Sort files to ensure they are processed in order (part_1.csv, part_2.csv, etc.)
    files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
    print(f"Found {len(files)} selected CSV files in folder {CSV_FOLDER_PATH}")
    for file in files:
        file_path = os.path.join(CSV_FOLDER_PATH, file)
        print(f"\n=== Processing file: {file} ===")
        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                headers = [h.strip() for h in reader.fieldnames]
                # Check required columns
                for col in REQUIRED_COLUMNS:
                    if col not in headers and col not in COLUMN_MAPPING.values():
                        print(f"File {file} DOES NOT have required column: {col}. Skipping this file.")
                        break
                else:
                    current_batch = []
                    stats = {
                        'total_leads_processed': 0,
                        'total_added_new': 0,
                        'total_updated': 0,
                        'total_no_change': 0,
                        'total_skipped_controller': 0,
                        'total_invalid_initial_check': 0,
                        'total_errors': 0
                    }
                    all_error_details = []
                    batch_num = 1
                    for row in reader:
                        mapped_row = map_columns(row)
                        current_batch.append(mapped_row)
                        if len(current_batch) >= BATCH_SIZE:
                            success, result = send_batch_to_api(current_batch, batch_num, "N/A")
                            if success:
                                batch_stats = result.get('stats', {})
                                stats['total_added_new'] += batch_stats.get('added_new', 0)
                                stats['total_updated'] += batch_stats.get('updated', 0)
                                stats['total_no_change'] += batch_stats.get('no_change', 0)
                                stats['total_skipped_controller'] += batch_stats.get('skipped_controller', 0)
                                stats['total_invalid_initial_check'] += batch_stats.get('invalid_initial_check', 0)
                                stats['total_errors'] += batch_stats.get('errors', 0)
                                all_error_details.extend(batch_stats.get('error_details', []))
                            else:
                                stats['total_errors'] += len(current_batch)
                                all_error_details.append(f"Batch {batch_num} totally failed: {result.get('message', 'Unknown error')}")
                            stats['total_leads_processed'] += len(current_batch)
                            current_batch = []
                            batch_num += 1
                    # Remaining batch
                    if current_batch:
                        success, result = send_batch_to_api(current_batch, batch_num, "N/A")
                        if success:
                            batch_stats = result.get('stats', {})
                            stats['total_added_new'] += batch_stats.get('added_new', 0)
                            stats['total_updated'] += batch_stats.get('updated', 0)
                            stats['total_no_change'] += batch_stats.get('no_change', 0)
                            stats['total_skipped_controller'] += batch_stats.get('skipped_controller', 0)
                            stats['total_invalid_initial_check'] += batch_stats.get('invalid_initial_check', 0)
                            stats['total_errors'] += batch_stats.get('errors', 0)
                            all_error_details.extend(batch_stats.get('error_details', []))
                        else:
                            stats['total_errors'] += len(current_batch)
                            all_error_details.append(f"Batch {batch_num} totally failed: {result.get('message', 'Unknown error')}")
                        stats['total_leads_processed'] += len(current_batch)
                    print(f"\n--- Import Process Finished for {file} ---")
                    print(f"Total records processed: {stats['total_leads_processed']}")
                    print(f"Result Statistics:")
                    print(f"  - Added New: {stats['total_added_new']}")
                    print(f"  - Updated: {stats['total_updated']}")
                    print(f"  - No Change: {stats['total_no_change']}")
                    print(f"  - Skipped (Controller Logic): {stats['total_skipped_controller']}")
                    print(f"  - Invalid (Initial Check): {stats['total_invalid_initial_check']}")
                    print(f"  - Errors During Processing: {stats['total_errors']}")
                    if all_error_details:
                        print("\nError Details:")
                        for err in all_error_details:
                            print(f"- {err}")
        except Exception as e:
            print(f"Failed to process file {file}: {e}")

if __name__ == "__main__":
    import_leads_from_folder()

