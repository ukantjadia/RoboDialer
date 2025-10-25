from urllib.parse import urlparse
import requests
import json
import csv
import time
import os
import pandas as pd
import datetime
import re

# ----------------------------------
# Paths: base/data/{input,logs}
# ----------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # script folder  [relative to script]
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_DIR = os.path.join(DATA_DIR, "input")            # read input CSVs from here
LOGS_DIR = os.path.join(DATA_DIR, "logs")              # write logs + audit CSVs here
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ----------------------------------
# Logging (Rotating file + console)
# ----------------------------------
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = LOGS_DIR
logger = logging.getLogger("lead_import")
logger.setLevel(logging.INFO)

fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "import.log"),
    maxBytes=2_000_000,
    backupCount=5,
    encoding="utf-8"
)
file_handler.setFormatter(fmt)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(fmt)
console_handler.setLevel(logging.INFO)

logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ----------------------------------
# Configuration
# ----------------------------------
API_BASE_URL = "https://data.saasquatchleads.com"
API_UPLOAD_ENDPOINT = f"{API_BASE_URL}/api/upload_leads"
API_KEY = os.getenv("LEAD_API_KEY", "lead_api_key")

BATCH_SIZE = 500
CSV_FOLDER_PATH = INPUT_DIR  # source files folder (data/input)

# ----------------------------------
# Per-row audit CSV (ledger)
# ----------------------------------
AUDIT_CSV = os.path.join(LOGS_DIR, "audit_uploads.csv")
AUDIT_COLUMNS = [
    "file_name", "file_row_number", "api_status", "api_message",
    "db_id", "processed_at"
]

def append_audit_rows(rows):
    df = pd.DataFrame(rows, columns=AUDIT_COLUMNS)
    header_needed = not os.path.exists(AUDIT_CSV)
    df.to_csv(AUDIT_CSV, mode="a", index=False, header=header_needed, encoding="utf-8")

# ----------------------------------
# File-level audit (progress for retries)
# ----------------------------------
RUN_AUDIT_CSV = os.path.join(LOGS_DIR, "audit_runs.csv")
RUN_AUDIT_COLUMNS = [
    "file_name", "total_rows", "batches_total", "batches_done",
    "rows_done", "last_batch", "status", "last_updated"
]

def _append_or_update_run_audit(row_dict):
    if os.path.exists(RUN_AUDIT_CSV):
        df = pd.read_csv(RUN_AUDIT_CSV)
    else:
        df = pd.DataFrame(columns=RUN_AUDIT_COLUMNS)
    idx_list = df.index[df["file_name"] == row_dict["file_name"]].tolist()
    if idx_list:
        idx = idx_list
        for k, v in row_dict.items():
            df.loc[idx, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    df.to_csv(RUN_AUDIT_CSV, index=False, encoding="utf-8")

def begin_file_audit(file_name, total_rows, batches_total):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    _append_or_update_run_audit({
        "file_name": file_name,
        "total_rows": int(total_rows),
        "batches_total": int(batches_total),
        "batches_done": 0,
        "rows_done": 0,
        "last_batch": 0,
        "status": "in_progress",
        "last_updated": now
    })

def update_file_audit(file_name, batches_done, rows_done, last_batch, status=None):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    total_rows = None
    batches_total = None
    if os.path.exists(RUN_AUDIT_CSV):
        df = pd.read_csv(RUN_AUDIT_CSV)
        row = df[df["file_name"] == file_name]
        if not row.empty:
            total_rows = int(row["total_rows"].iloc) if pd.notna(row["total_rows"].iloc) else None
            batches_total = int(row["batches_total"].iloc) if pd.notna(row["batches_total"].iloc) else None
    _append_or_update_run_audit({
        "file_name": file_name,
        "total_rows": total_rows if total_rows is not None else "",
        "batches_total": batches_total if batches_total is not None else "",
        "batches_done": int(batches_done),
        "rows_done": int(rows_done),
        "last_batch": int(last_batch),
        "status": status if status else "in_progress",
        "last_updated": now
    })



# ----------------------------------
# Cleaning and mapping 
# ----------------------------------

# Columns that must exist in every file
REQUIRED_COLUMNS = ["company", "website", "owner_linkedin"]

# Column mapping if there are different names
COLUMN_MAPPING = {
    # Required fields
    "Company": "company",
    "Website": "website",
    "Owner's LinkedIn": "owner_linkedin",
    "Owner LinkedIn": "owner_linkedin",    # ✅ new
    "LinkedIn URL": "owner_linkedin",
    
    # Owner Information
    "Owner First Name": "owner_first_name",
    "Owner Last Name": "owner_last_name",
    "Owner Email": "owner_email",
    "Email": "owner_email",  
    "Owner Phone Number": "owner_phone_number",
    "Owner Phone": "owner_phone_number",  # ✅ NEW
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
    "Additional Notes": "additional_notes",


    "organization_name": "company",
    "organization_website_url": "website",
    "organization_phone": "company_phone",
    "organization_industries": "industry",
    "organization_num_current_employees": "employees",
    "organization_revenue_in_thousands_int": "revenue",
    "organization_founded_year": "year_founded",
    "organization_hq_location_city": "city",
    "organization_hq_location_state": "state",
    "organization_short_description": "additional_notes",
}

STATE_MAPPING = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'District of Columbia': 'DC', 'Puerto Rico': 'PR', 'Guam': 'GU', 'American Samoa': 'AS',
    'U.S. Virgin Islands': 'VI', 'Northern Mariana Islands': 'MP'
}
VALID_US_STATES = set(STATE_MAPPING.values()) # ✅ new 

# US-style regex (NANP)
# phone_extract_pattern = re.compile(
#     r"(1[\s\-]*)?"                   # optional US country code
#     r"\(?(\d{3})\)?[-\s\.]?"         # area code (3 digits)
#     r"(\d{3})[-\s\.]?"               # exchange (3 digits)
#     r"(\d{4})"                       # subscriber (4 digits)
# ) # ✅ new

phone_extract_pattern = re.compile(
    r"^\+?1?[-.\s(]*([2-9]\d{2})[-.\s)]*([2-9]\d{2})[-.\s]*(\d{4})$")

def normalize_dashes(s):
    return s.replace("–", "-").replace("—", "-").replace("−", "-")

def standardize_state(state):
    """Convert state names to their two-letter abbreviations"""
    if not state or pd.isna(state):
        return None
    state = str(state).strip()
    # If it's already a 2-letter code, return as is
    if len(state) == 2 and state.isalpha():
        state_code = state.upper()
        return state_code if state_code in VALID_US_STATES else None # ✅ new 
    # Try to find in mapping
    return STATE_MAPPING.get(state.title(), state)

# --- Helper Functions ---
def send_batch_to_api(batch_data, batch_num, total_batches):
    headers = {
        "Content-Type": "application/json",
        **({"Authorization": f"Bearer {API_KEY}"} if API_KEY else {})
    }
    max_retries = 5
    retry_delay_seconds = 2
    for attempt in range(max_retries):
        try:
            logger.info("Sending batch %s/%s (%s records), attempt %s",
                        batch_num, total_batches, len(batch_data), attempt + 1)
            response = requests.post(API_UPLOAD_ENDPOINT, json=batch_data, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()
            logger.info("Batch %s success. Status=%s Message=%s",
                        batch_num, result.get("status"), result.get("message"))
            return True, result
        except requests.exceptions.Timeout:
            logger.warning("Timeout on batch %s. Retrying in %ss", batch_num, retry_delay_seconds)
            time.sleep(retry_delay_seconds); retry_delay_seconds *= 2
        except requests.exceptions.ConnectionError as e:
            logger.warning("Connection error on batch %s: %s. Retrying in %ss",
                           batch_num, e, retry_delay_seconds)
            time.sleep(retry_delay_seconds); retry_delay_seconds *= 2
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            logger.warning("HTTP %s on batch %s: %s", status, batch_num, e.response.text)
            if 500 <= status < 600:
                logger.info("Retrying in %ss due to server error", retry_delay_seconds)
                time.sleep(retry_delay_seconds); retry_delay_seconds *= 2
            else:
                return False, {"status": "error", "message": f"HTTP {status}: {e.response.text}"}
        except json.JSONDecodeError:
            logger.error("Invalid JSON response for batch %s: %s", batch_num, response.text)
            return False, {"status": "error", "message": "Invalid JSON response from API"}
        except Exception as e:
            logger.error("Unexpected error on batch %s: %s", batch_num, str(e))
            return False, {"status": "error", "message": f"Unexpected error: {str(e)}"}
    logger.error("Failed to send batch %s after %s attempts", batch_num, max_retries)
    return False, {"status": "error", "message": "Max retries exceeded for batch"}

    

def clean_employees(employees_str):
    """Clean and standardize employees field"""

    # | Input                         | Output |
    # | ----------------------------- | ------ |
    # | `"51-200"`                    | `51`   |
    # | `"100-400 (Employee number)"` | `100`  |
    # | `"1.7K"`                      | `1700` |
    # | `"2K"`                        | `2000` |
    # | `"399 (but on zoom info 80)"` | `399`  |
    # | `"N/A (school page)"`         | `None` |
    # | `"Feb-14"`                    | `None` |
    # | `"2020-10"`                   | `None` |

    if not employees_str or pd.isna(employees_str):
        return None
    
    
    # Convert to string and clean
    employees_str = str(employees_str).strip().lower()


    # Drop obvious non-employee markers
    if any(x in employees_str for x in ["n/a", "doesnt say", "no employee", "school page"]):  # ✅ new 
        return None
    
    # Drop date-like patterns (Feb-14, 2020-10)
    if re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", employees_str):        # ✅ new 
        return None
    if re.match(r"\d{1,4}[-/]\d{1,2}([-/]\d{1,4})?", employees_str):
        return None
    
    # Normalize special characters                                                            # ✅ new 
    employees_str = employees_str.replace("â€“", "-").replace("–", "-").replace("—", "-")    
    employees_str = employees_str.replace("employees", "").replace("employee", "")
    employees_str = re.sub(r"\([^)]*\)", "", employees_str)  # remove text inside parentheses
    employees_str = re.sub(r"[^0-9kK\+\-<>\s]", " ", employees_str)  # keep only digits, k, +, -, <, >
    employees_str =" ".join(employees_str.split())  # normalize whitespace
    
    # Remove common suffixes and extra text
    # employees_str = employees_str.replace('employees', '').replace('employee', '')
    # employees_str = employees_str.replace('(on website)', '').replace('(website)', '')
    # employees_str = employees_str.replace('(https://', '').replace(')', '')
    
    # Handle ranges like "11-50"
    if '-' in employees_str:
        try:
            parts = re.findall(r"\d+", employees_str)                                       # ✅ new 
            return int(parts[0])  if parts else None  # take lower bound
        except:
            return None
    
    # Handle "X+" format
    if employees_str.endswith('+'):
        try:
            num=re.findall(r"\d+", employees_str)                                           # ✅ new
            return int(num[0]) if num else None  # take the number before '+'
        except:
            return None
    
    # Handle "<X" format
    if employees_str.startswith('<'):
        try:
            num = re.findall(r"\d+", employees_str)                                         # ✅ new
            return int(num[0]) if num else None
        except:
            return None

    # Handle shorthand like "1.7K" or "2k"                                                  # ✅ new
    match = re.match(r"(\d+(\.\d+)?)k", employees_str)
    if match:
        return int(float(match.group(1)) * 1000)


    # Handle plain numbers, including decimals like 37.5 or 51.0
    try:
        num = float(employees_str.replace(",", ""))
        return int(num)  # truncate decimals
    except ValueError:
        pass

    # Fallback: try digits only
    num = re.findall(r"\d+", employees_str.replace(",", ""))
    if num:
        return int(num[0])
    
    return None

def clean_revenue(revenue_str):
    """Clean and standardize revenue field"""

#     $5M → 5000000.0
#     2.5b → 2500000000.0
#     1-5m → 1000000.0 (first number)
#     <10M → 10000000.0
#     5822813.75 → 5822813.75
#     10,000,000 → 10000000.0
#     USD 25k → 25000.0
# and safely returns None if parsing fails.

    if not revenue_str or pd.isna(revenue_str):
        return None
    
    try:
        # Convert to string and clean
        revenue_str = str(revenue_str).strip().lower()
        
        # Remove common suffixes and extra text
        # revenue_str = revenue_str.replace('million', '').replace('m', '')
        # revenue_str = revenue_str.replace('billion', '').replace('b', '')
        # revenue_str = revenue_str.replace('$', '').replace(',', '')


        # Remove extra text                                                                        # ✅ new                                         
        revenue_str = revenue_str.replace("â€“", "-").replace("–", "-").replace("—", "-")  # normalize dashes
        revenue_str = re.sub(r"\([^)]*\)", "", revenue_str)   # remove text in parentheses
        revenue_str = revenue_str.replace("raised to date", "")
        revenue_str = revenue_str.replace("usd", "").replace("us$", "")
        revenue_str = revenue_str.replace("$", "").replace(",", "").strip()
        



        # Handle ranges like "1-5m" or "<5m"
        if "-" in revenue_str:
            nums = re.findall(r"\d+\.?\d*", revenue_str)
            if nums:
                return float(nums[0]) * (1e6 if "m" in revenue_str else 1e9 if "b" in revenue_str else 1)
            
        if revenue_str.startswith("<") or revenue_str.startswith(">"):
            nums = re.findall(r"\d+\.?\d*", revenue_str)
            if nums:
                return float(nums[0]) * (1e6 if "m" in revenue_str else 1e9 if "b" in revenue_str else 1)
            
        # Handle shorthand with multipliers
        match = re.match(r"(\d+(\.\d+)?)([kmb])?", revenue_str)
        if match:
            value, _, suffix = match.groups()
            value = float(value)
            if suffix == "k":
                return value * 1e3
            elif suffix == "m":
                return value * 1e6
            elif suffix == "b":
                return value * 1e9
            return value


        # Handle plain numbers (like 5822813.75, 10,000,000)
        nums = re.findall(r"\d+\.?\d*", revenue_str)
        if nums:
            return float(nums[0])
        return None
    except:
        return None

def clean_year(year_str):
    """Clean and standardize year field"""
    if not year_str or pd.isna(year_str):
        return None
    
    try:
        # Convert to string and clean
        year_str = str(year_str).strip()

        # Remove approximate markers
        year_str = year_str.replace("~", "")                    # ✅ new
        year_str = year_str.replace("approx", "")
        
        # Extract 4-digit year
        match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", year_str)
        
        # Validate year is reasonable (between 1800 and current year + 5)
        if match:
            year = int(match.group(1))
            current_year = datetime.datetime.now().year
            if 1800 <= year <= current_year + 5:
                return year
            
        # Handle two-digit shorthand years (e.g. '99 → 1999, '05 → 2005)
        match = re.search(r"'(\d{2})", year_str)
        if match:
            yr = int(match.group(1))
            year = 1900 + yr if yr > 25 else 2000 + yr  # heuristic: '99=1999, '05=2005
            return year
    except:
        pass
    
    return None

def clean_phone(phone_str, default_region="US"):                                       # ✅ new
    """Clean and standardize phone number 
    US numbers -> 10 digits only (no country code)
    """

    if not phone_str or pd.isna(phone_str):
        return None
    
    
    # Convert to string and clean
    phone_str = normalize_dashes(str(phone_str).strip())

    # Explicit junk markers → None
    junk_values = ["unavailable", "not available", "not found",
                   "cannot found", "cannot find", "n/a", "no phone"]
    if any(junk in phone_str for junk in junk_values):
        return None
    
    # Remove obvious non-phone values (emails, urls, words)
    if "@" in phone_str or "http" in phone_str.lower() or phone_str.isalpha():
        return None
    
    match = phone_extract_pattern.match(phone_str)
    if match:
        area, first_three, last_four = match.groups()
        digits = area + first_three + last_four
        if len(digits) == 10:
            return digits
        
    return None


def clean_email(email_str):                                                             # ✅ new
    """Clean and validate email address"""
    if not email_str or pd.isna(email_str):
        return None

    email_pattern = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")
    text = str(email_str).lower().strip()
    emails = email_pattern.findall(text)

    if not emails:
        return None

    # Deduplicate & preserve order
    emails = list(dict.fromkeys(emails))

    # Save first email only (common case)
    return emails[0]

def clean_linkedin(linkedin_str):                                                          # ✅ new
    """Validate and clean LinkedIn URL (owner/company). Returns None if invalid."""
    if not linkedin_str or pd.isna(linkedin_str):
        return None

    text = str(linkedin_str).strip().lower()

    linkedin_pattern = re.compile(
    r"^(https?://)?(www\.)?([a-z]{2}\.)?linkedin\.com/(in|company|pub|school|showcase)/.+",
    re.IGNORECASE)

    if not linkedin_pattern.match(text):
        return None


    # Normalize: ensure https:// prefix
    if not text.lower().startswith("http"):
        text = "https://" + text

    # Drop query params / fragments
    text = text.split("?")[0].split("#")[0]

    return text

# def clean_website(website_str):
#     """Clean and validate website URL. Returns None if invalid."""
#     if not website_str or pd.isna(website_str):
#         return None
    
#     text = str(website_str).strip().lower()
    
#     # ✅ NORMALIZE FIRST
#     # Ensure scheme
#     if not text.startswith(("http://", "https://")):
#         text = "https://" + text
    
#     # Drop query params / fragments (don't touch path)
#     text = text.split("?")[0].split("#")[0]
    
#     # ✅ VALIDATE AFTER NORMALIZATION
#     website_pattern = re.compile(r"^(https?://)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$")
#     if not website_pattern.match(text):
#         return website_str  # return original uncleaned if invalid
    
#     return text


def clean_website(website_str):
    """
    Cleans and validates a website URL.
    Returns a descriptive error string if invalid.
    """
    if not website_str or pd.isna(website_str):
        return None
    
    text = str(website_str).strip()
    
    if not text.startswith(("http://", "https://")):
        text = "https://" + text
    
    try:
        parsed_url = urlparse(text)
        domain = parsed_url.netloc
        
        # The validation happens here with four specific rules:
        if (domain and                           # Rule 1: Domain must exist
            '.' in domain and                    # Rule 2: Domain must contain a dot
            '@' not in domain and                # Rule 3: Domain cannot be an email address
            len(domain.split('.')[-1]) > 1):     # Rule 4: TLD must be at least 2 characters long
            
            # If all rules pass, return the cleaned URL
            return (parsed_url.scheme.lower() + "://" + 
                    domain.lower() + 
                    parsed_url.path + 
                    parsed_url.params + 
                    parsed_url.query + 
                    parsed_url.fragment)
        else:
            # If any rule fails, return an error
            return website_str  # return original uncleaned if invalid
            
    except ValueError:
        return "Error: URL contains invalid characters or is malformed"

AUDIT_CSV = os.path.join(CSV_FOLDER_PATH, "audit_uploads.csv")

AUDIT_COLUMNS = [
    "file_name", "file_row_number", "api_status", "api_message",
    "db_id", "processed_at"
]


def map_columns(row):
    mapped = {}
    # Manual mapping for required columns
    mapped['company'] = row.get('Company') or row.get('Company Name') or row.get('company') or row.get("organization_name")  or ''
    mapped['website'] = row.get('Website') or row.get('website') or row.get("organization_website_url") or ''
    mapped['website'] = clean_website(mapped['website'])  # Clean website                    # ✅ new
    mapped['owner_linkedin'] = row.get("Owner's LinkedIn") or row.get('LinkedIn URL') or row.get('owner_linkedin') or ''
    # Always set source to 'manual'
    mapped['source'] = 'manual'
    
    # Map other columns according to COLUMN_MAPPING
    for k, v in row.items():
        mapped_key = COLUMN_MAPPING.get(k.strip(), k.strip())
        if mapped_key not in mapped:  # Don't overwrite required columns
            # Apply appropriate cleaning based on field type
            if mapped_key == 'state':
                mapped[mapped_key] = standardize_state(v)
            elif mapped_key == 'employees':
                mapped[mapped_key] = clean_employees(v)
            elif mapped_key == 'revenue':
                mapped[mapped_key] = clean_revenue(v)
            elif mapped_key == 'year_founded':
                mapped[mapped_key] = clean_year(v)
            elif mapped_key in ['phone', 'owner_phone_number', 'company_phone']:
                mapped[mapped_key] = clean_phone(v)
            elif mapped_key in ['owner_email']:                                                   # ✅ new
                mapped[mapped_key] = clean_email(v)
            elif mapped_key in ['owner_linkedin', 'company_linkedin']:                            # ✅ new
                mapped[mapped_key] = clean_linkedin(v)
            else:
                # For other fields, just clean whitespace
                mapped[mapped_key] = str(v).strip() if v is not None else None
    
    
    return mapped

# ----------------------------------
# Main
# ----------------------------------

def import_leads_from_folder():
    files = [f for f in os.listdir(CSV_FOLDER_PATH)
             if f.endswith('.csv') and f.lower().startswith('part_20')]

    def sort_key(name):
        m = re.search(r'part_(\d+)', name, re.IGNORECASE)
        return int(m.group(1)) if m else 0
    files.sort(key=sort_key)

    logger.info("Found %s CSV files in %s", len(files), CSV_FOLDER_PATH)

    for file in files:
        file_path = os.path.join(CSV_FOLDER_PATH, file)
        logger.info("Processing file: %s", file)

        try:
            with open(file_path, 'r', encoding='utf-8') as fc:
                total_lines = sum(1 for _ in fc)
            total_rows = max(0, total_lines - 1)
            batches_total = (total_rows + BATCH_SIZE - 1) // BATCH_SIZE if total_rows > 0 else 0
            begin_file_audit(file, total_rows, batches_total)

            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                headers = [h.strip() for h in reader.fieldnames]

                for col in REQUIRED_COLUMNS:
                    if col not in headers and col not in COLUMN_MAPPING.values():
                        logger.warning("Skipping %s: missing required column %s", file, col)
                        update_file_audit(file, batches_done=0, rows_done=0, last_batch=0, status="skipped_missing_columns")
                        break
                else:
                    current_batch, meta_for_batch = [], []
                    stats = {
                        'total_leads_processed': 0, 'total_added_new': 0, 'total_updated': 0,
                        'total_no_change': 0, 'total_skipped_controller': 0,
                        'total_invalid_initial_check': 0, 'total_errors': 0
                    }
                    all_error_details = []
                    batch_num = 1

                    for row in reader:
                        mapped_row = map_columns(row)
                        current_batch.append(mapped_row)
                        meta_for_batch.append({
                            "file_name": file,
                            "file_row_number": reader.line_num
                        })

                        if len(current_batch) >= BATCH_SIZE:
                            success, result = send_batch_to_api(current_batch, batch_num, batches_total or "N/A")
                            audit_rows = []
                            per_row = result.get("per_row", []) if success else []
                            for i, meta in enumerate(meta_for_batch):
                                item = per_row[i] if i < len(per_row) else {}
                                audit_rows.append({
                                    "file_name": meta["file_name"],
                                    "file_row_number": meta["file_row_number"],
                                    "api_status": item.get("status", "error" if not success else "unknown"),
                                    "api_message": item.get("message"),
                                    "db_id": item.get("db_id"),
                                    "processed_at": datetime.datetime.utcnow().isoformat() + "Z",
                                })
                            append_audit_rows(audit_rows)
                            logger.info("Batch %s audit rows appended: %s", batch_num, len(audit_rows))

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
                            update_file_audit(
                                file,
                                batches_done=batch_num,
                                rows_done=stats['total_leads_processed'],
                                last_batch=batch_num
                            )
                            current_batch, meta_for_batch = [], []
                            batch_num += 1

                    if current_batch:
                        success, result = send_batch_to_api(current_batch, batch_num, batches_total or "N/A")
                        audit_rows = []
                        per_row = result.get("per_row", []) if success else []
                        for i, meta in enumerate(meta_for_batch):
                            item = per_row[i] if i < len(per_row) else {}
                            audit_rows.append({
                                "file_name": meta["file_name"],
                                "file_row_number": meta["file_row_number"],
                                "api_status": item.get("status", "error" if not success else "unknown"),
                                "api_message": item.get("message"),
                                "db_id": item.get("db_id"),
                                "processed_at": datetime.datetime.utcnow().isoformat() + "Z",
                            })
                        append_audit_rows(audit_rows)
                        logger.info("Final batch audit rows appended: %s", len(audit_rows))

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
                        update_file_audit(
                            file,
                            batches_done=batch_num,
                            rows_done=stats['total_leads_processed'],
                            last_batch=batch_num
                        )

                    final_status = "success" if stats['total_errors'] == 0 else "completed_with_errors"
                    update_file_audit(
                        file,
                        batches_done=batch_num,
                        rows_done=stats['total_leads_processed'],
                        last_batch=batch_num,
                        status=final_status
                    )

                    logger.info(
                        "Finished %s | processed=%s added=%s updated=%s errors=%s",
                        file, stats['total_leads_processed'],
                        stats['total_added_new'], stats['total_updated'], stats['total_errors']
                    )

        except Exception as e:
            logger.exception("Failed to process file %s: %s", file, e)
            update_file_audit(file, batches_done=0, rows_done=0, last_batch=0, status="failed")

if __name__ == "__main__":
    import_leads_from_folder()