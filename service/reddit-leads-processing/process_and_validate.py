# process_and_validate.py
import pandas as pd
import os
import datetime
import logging
import re
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from collections import Counter
from urllib.parse import urlparse


# --- Helper Functions ---

def is_integer(val):
    """Checks if a value can be cleanly converted to an integer."""
    try:
        int(str(val).strip().split('.')[0]) # handles "35.0"
        return True
    except (ValueError, TypeError):
        return False

def clean_reason_text(text):
    """Cleans reason text to prevent CSV formatting issues."""
    if pd.isna(text):
        return ""
    cleaned = str(text).replace('\n', ' ').replace('\r', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def is_valid_website(url_str):
    """Checks if a string is a structurally valid URL."""
    try:
        url_str = str(url_str).strip()
        if not url_str.startswith(('http://', 'https://')):
            url_str = 'https://' + url_str
        
        result = urlparse(url_str)
        # A valid URL must have a scheme (http) and a domain (netloc) with a dot.
        return all([result.scheme, result.netloc, '.' in result.netloc])
    except (ValueError, AttributeError):
        return False
    

def is_valid_linkedin(url: str) -> bool:
    """Checks for a valid LinkedIn profile or company URL."""
    pattern = re.compile(
        r"^(https?://)?(www\.)?([a-z]{2}\.)?linkedin\.com/(in|company|pub|school|showcase)/.+", 
        re.IGNORECASE
    )
    return re.match(pattern, str(url)) is not None

def has_invalid_email(text: str) -> bool:
    """
    Checks a string for any invalid email addresses. 
    Can handle multiple emails separated by common delimiters.
    Returns True if any email is invalid.
    """
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    split_pattern = re.compile(r"[\s,;:/]+")
    emails = [e.strip() for e in split_pattern.split(str(text)) if e.strip()]
    if not emails:
        return False # No emails exist, so none are invalid.
    invalid_emails = [email for email in emails if not email_pattern.match(email)]
    return len(invalid_emails) > 0


def is_invalid_us_phone(text: str) -> bool:
    """
    Checks if a string is an invalid US-style phone number.
    Returns True if the format is invalid.
    """
    # This pattern is strict, expecting a 10-digit number with optional separators.
    phone_extract_pattern = re.compile(r"^(1[\s\-]*)?\(?(\d{3})\)?[-\s\.]?(\d{3})[-\s\.]?(\d{4})$")
    
    def normalize_dashes(text: str) -> str:
        # Replaces various dash characters with a standard hyphen.
        return re.sub(r"[‑–—−]", "-", str(text))
        
    return not phone_extract_pattern.match(normalize_dashes(text).strip())


def save_report_style_csv(individual_df, cluster_df, filepath):
    """
    Saves two DataFrames to a single CSV in a report-style format,
    one after the other, separated by a header.
    """
    # 1. Save the first DataFrame (individual errors) with its header
    individual_df.to_csv(filepath, index=False)

    # 2. Open the same file in append mode ('a') to add more content
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        # 3. Add a blank line for spacing
        f.write('\n')
        
        # 4. Add a title for the next section
        f.write('--- Error Clusters ---\n')

    # 5. Append the second DataFrame (clusters) if it's not empty
    if not cluster_df.empty:
        cluster_df.to_csv(filepath, mode='a', index=False, header=True)
    
    print(f"   - Consolidated Report:   {os.path.basename(filepath)}")


def validate_csv(csv_path, output_path, errors_only_path, flag_empty=False):
    """
    Validates a CSV file and returns the full DataFrame, an errors-only DataFrame,
    and a summary DataFrame of individual error counts.
    
    Args:
        csv_path (str): Path to the input CSV file.
        output_path (str): Path to save the full validated CSV.
        errors_only_path (str): Path to save the CSV with only invalid rows.
        flag_empty (bool): If True, flags empty values for optional fields as invalid.
    """
    print(f"Validating {csv_path} (flag_empty={flag_empty})...")
    df = pd.read_csv(csv_path, low_memory=False, dtype=str).fillna('')
    df["flag"] = "valid"
    df["reason"] = ""
    error_counter = Counter()

    # --- Constants ---
    VALID_US_STATES = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC', "PR", "VI", "GU", "AS", "MP"
    }
    
    # --- Row-wise Validation ---
    for i, row in df.iterrows():
        reasons = []

        # --- Essential Fields (always checked) ---
        if not row.get("Company", "").strip():
            reasons.append("Company missing")
            error_counter["Company missing"] += 1
            
        if not row.get("Industry", "").strip():
            reasons.append("Industry missing")
            error_counter["Industry missing"] += 1

        if not row.get("Website", "").strip():
            reasons.append("Website missing")
            error_counter["Website missing"] += 1

        # --- Optional Fields (checked for format if present, and for missing if flag_empty is True) ---
        
        # Helper function for repeated logic
        def validate_field(col_name, missing_reason, invalid_reason, validation_func):
            val = row.get(col_name, "").strip()
            if not val:
                if flag_empty:
                    reasons.append(missing_reason)
                    error_counter[missing_reason] += 1
            elif validation_func(val): # validation_func should return True if invalid
                reasons.append(invalid_reason)
                error_counter[invalid_reason] += 1
        
        # Website
        validate_field("Website", "Website missing", "Invalid Website", lambda v: not is_valid_website(v))
        
        # LinkedIn
        validate_field("Owner - LinkedIn Profile Link", "Owner LinkedIn missing", "Owner LinkedIn not valid LinkedIn URL", lambda v: not is_valid_linkedin(v))
        validate_field("Company - LinkedIn Profile Link", "Company LinkedIn missing", "Company LinkedIn not valid LinkedIn URL", lambda v: not is_valid_linkedin(v))
        
        # Email
        validate_field("Owner - Email", "Owner Email missing", "Invalid Owner Email(s)", has_invalid_email)
        
        # Phone
        validate_field("Company Phone", "Company Phone missing", "Company Phone invalid phone format", is_invalid_us_phone)
        validate_field("Owner - Work Phone", "Owner Phone missing", "Owner Phone invalid phone format", is_invalid_us_phone)
        validate_field("Phone", "Phone missing", "Phone invalid phone format", is_invalid_us_phone)
        
        # Employees
        val = row.get("Employees", "").strip()
        if not val:
            if flag_empty:
                reasons.append("Employees missing")
                error_counter["Employees missing"] += 1
        elif not is_integer(val):
            reasons.append("Employees not integer")
            error_counter["Employees not integer"] += 1
            
        # State
        val = row.get("State", "").strip()
        if not val:
            if flag_empty:
                reasons.append("State missing")
                error_counter["State missing"] += 1
        elif val.upper() not in VALID_US_STATES:
            reasons.append("Invalid State code")
            error_counter["Invalid State code"] += 1
        
        # Year Founded
        val = row.get("Year Founded", "").strip()
        if not val:
            if flag_empty:
                reasons.append("Year Founded missing")
                error_counter["Year Founded missing"] += 1
        else:
            year_val = val.split('.')[0]
            if not (is_integer(year_val) and 1000 <= int(year_val) <= datetime.now().year):
                reasons.append("Year Founded invalid")
                error_counter["Year Founded invalid"] += 1
        
        # Revenue (Format check only)
        val = row.get("Revenue", "").strip()
        if val:
            try:
                rev_val = float(str(val).replace(",", "").split()[0])
                if rev_val < 0:
                    reasons.append("Revenue invalid (<0)")
                    error_counter["Revenue invalid (<0)"] += 1
            except (ValueError, TypeError):
                reasons.append("Revenue not numeric")
                error_counter["Revenue not numeric"] += 1

        # --- Finalize Row ---
        if reasons:
            df.at[i, "flag"] = "invalid"
            df.at[i, "reason"] = clean_reason_text("; ".join(reasons))

    # --- Save Output Files ---
    df.to_csv(output_path, index=False, encoding='utf-8')
    errors_df = df[df['flag'] == 'invalid'].copy()
    errors_df.to_csv(errors_only_path, index=False, encoding='utf-8')
    print("✅ Validation completed successfully!")
    print(f"📁 Files saved:\n   - Complete dataset: {os.path.basename(output_path)}\n   - Errors only: {os.path.basename(errors_only_path)}")

    # --- Generate Console Summary ---
    total_rows = len(df)
    total_invalid = len(errors_df)
    individual_errors_list = []

    if error_counter:
        print(f"\n🔍 INDIVIDUAL ERROR COUNTS ({total_invalid} invalid rows)\n{'='*50}")
        sorted_errors = sorted(error_counter.items(), key=lambda x: x[1], reverse=True)
        for error, count in sorted_errors:
            percentage = (count / total_rows) * 100
            print(f"   • {error:<40} {count:>6,} ({percentage:>5.1f}%)")
            individual_errors_list.append({
                'Type': 'Individual Error',
                'Description': error,
                f'Count ({total_rows}/{total_invalid})': count,
                'Percentage of Total': round(percentage, 2)
            })
        print()

    # This is where the DataFrame is created
    individual_errors_summary_df = pd.DataFrame(individual_errors_list)
    
    return df, errors_df, individual_errors_summary_df

def error_clusters_report_ordered(df, output_path):
    """
    Analyzes error clusters, prints a report, and returns a standardized DataFrame.
    """
    total_rows = len(df)
    invalid = df[df['flag'] == 'invalid'].copy()
    if invalid.empty:
        print("\n🎉 No invalid rows found, skipping cluster report.")
        return pd.DataFrame()

    cluster_counts = (
        invalid.groupby('reason').size().reset_index(name='Count')
        .sort_values('Count', ascending=False).reset_index(drop=True)
    )
    
    total_invalid = len(invalid)
    cluster_counts['Percentage of Invalid'] = (cluster_counts['Count'] / total_invalid * 100).round(1)
    # cluster_counts.to_csv(output_path, index=False, encoding='utf-8')
    new_count_col_name = f'Count ({total_rows}/{total_invalid})'

    print(f"\n📋 TOP ERROR CLUSTERS (saved to {os.path.basename(output_path)})\n" + "=" * 60)
    print(cluster_counts.to_string(index=False))
    
    cluster_counts.rename(columns={
        'reason': 'Description',
        'Count': new_count_col_name
    }, inplace=True)
    cluster_counts.insert(0, 'Type', 'Error Cluster')
    return cluster_counts[['Type','Description', new_count_col_name, 'Percentage of Invalid']]





from bulk_copy import (clean_email, clean_employees, clean_linkedin, clean_phone, 
                       clean_revenue, clean_website, clean_year, standardize_state)






# --- File Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, 'data', 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'output')
LOG_DIR = os.path.join(BASE_DIR, 'data', 'logs')

# !! IMPORTANT: this is sheet id for google sheet !!
GOOGLE_SHEET_KEY = "1WKerK20EOlAE-FVGrA9HpE7o1LwNVZ7clmktbJsC33s"


# --- Setup Directories and Logging ---
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'processing.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Data Processing Functions ---

def normalize_data(df):
    """Applies all cleaning and normalization functions to the DataFrame."""
    logging.info("Starting data normalization...")
    df_cleaned = df.copy()

    cleaning_map = {
        "Owner Email": clean_email,
        "Owner Phone": clean_phone,
        "Company Phone": clean_phone,
        "Phone": clean_phone,
        "Employees": clean_employees,
        "Revenue": clean_revenue,
        "Year Founded": clean_year,
        "State": standardize_state,
        "Company LinkedIn": clean_linkedin,
        "Owner LinkedIn": clean_linkedin,
        "Website": clean_website
    }

    for column, function in cleaning_map.items():
        if column in df_cleaned.columns:
            df_cleaned[column] = df_cleaned[column].apply(function)
        else:
            logging.warning(f"Column '{column}' not found for normalization.")
            
    logging.info("Normalization complete.")
    return df_cleaned

def upload_weekly_reports_to_gsheets(clean_df, summary_df,error_df, sheet_key, week_number):
    """
    Uploads reports to Google Sheets with week-specific, dynamic tab names.
    """
    print("\n G-Sheet Upload Initiated... ")
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)

        sheet = client.open_by_key(sheet_key)
        
        # --- MODIFIED: Sheet names are now dynamic using the week_number ---
        clean_data_sheet_name = f"Final_Clean_Data_Week{week_number}"
        summary_sheet_name = f"Summary_Week{week_number}"
        invalid_only_sheet_name = f"Invalid_Only_Week{week_number}"

        def overwrite_sheet(sheet_obj, sheet_title, df_to_upload):
            print(f"  Uploading to '{sheet_title}' tab...")
            try:
                worksheet = sheet_obj.worksheet(sheet_title)
                sheet_obj.del_worksheet(worksheet)
            except gspread.exceptions.WorksheetNotFound:
                pass 
            
            worksheet = sheet_obj.add_worksheet(
                title=sheet_title, 
                rows=len(df_to_upload) + 1, 
                cols=len(df_to_upload.columns)
            )
            
            df_filled = df_to_upload.fillna("")
            
            worksheet.update([df_filled.columns.values.tolist()] + df_filled.values.tolist())
            print(f"  ✅ Success.")

        overwrite_sheet(sheet, clean_data_sheet_name, clean_df)
        overwrite_sheet(sheet, summary_sheet_name, summary_df)
        overwrite_sheet(sheet,invalid_only_sheet_name,error_df)
        
        print("✅ Google Sheets upload complete.")

    except FileNotFoundError:
        print(" G-Sheet ERROR: 'credentials.json' not found. Skipping upload. ")
    except Exception as e:
        print(f" G-Sheet ERROR: An error occurred: {e}. Skipping upload. ")

def process_single_file(input_filepath, output_dir):
    """Processes a single CSV: normalizes, validates, and saves all reports."""
    filename = os.path.basename(input_filepath)
    match = re.search(r'\d+', filename)
    if not match:
        logging.warning(f"SKIPPING: No week number in filename '{filename}'.")
        print(f"⚠️  Skipping: No week number found in '{filename}'.")
        return

    current_week = match.group(0)
    print(f"\n{'='*60}")
    print(f"🚀 Processing file: '{filename}' for Week {current_week}")
    logging.info(f"--- Processing started for {filename} (Week: {current_week}) ---")

    try:
        df = pd.read_csv(input_filepath, low_memory=False)
        logging.info(f"Loaded '{filename}' ({len(df)} rows).")
    except Exception as e:
        print(f"❌ Error reading '{filename}': {e}")
        logging.error(f"Failed to read '{filename}': {e}")
        return

    df_normalized = normalize_data(df.copy())
    print("✅ Normalization complete.")
    
    timestamp = datetime.now().strftime("%d_%m_%Y_%H%M%S")
    temp_path = os.path.join(output_dir, f"temp_norm_{current_week}_{timestamp}.csv")
    validated_path = os.path.join(output_dir, f"week_{current_week}_validated_{timestamp}.csv")
    errors_path = os.path.join(output_dir, f"week_{current_week}_errors_only_{timestamp}.csv")
    clean_path = os.path.join(output_dir, f"week_{current_week}_final_clean_{timestamp}.csv")
    cluster_path = os.path.join(output_dir, f"week_{current_week}_cluster_details_{timestamp}.csv")
    summary_path = os.path.join(output_dir, f"week_{current_week}_summary_report_{timestamp}.csv")

    df_normalized.to_csv(temp_path, index=False, encoding='utf-8')
    
    validated_df, errors_df, individual_df = validate_csv(
        csv_path=temp_path, output_path=validated_path, errors_only_path=errors_path
    )
    
    cluster_df = error_clusters_report_ordered(df=validated_df, output_path=cluster_path)

    print("\n📊 Creating Consolidated Summary Report...")
    save_report_style_csv(individual_df=individual_df, cluster_df=cluster_df, filepath=summary_path)

    # Combine summaries into a single DataFrame for easier upload
    consolidated_summary_df = pd.concat([individual_df, cluster_df], ignore_index=True)


    if 'flag' in validated_df.columns:
        clean_df = validated_df[validated_df['flag'] == 'valid'].copy()
        invalid_df=validated_df[validated_df['flag'] == 'invalid'].copy()
        invalid_df.drop(columns=['flag'], inplace=True, errors='ignore')
        clean_df.drop(columns=['flag', 'reason'], inplace=True, errors='ignore')
        clean_df.to_csv(clean_path, index=False, encoding='utf-8')
    
    # --- NEW: Call the upload function ---
    if not clean_df.empty:
        upload_weekly_reports_to_gsheets(
            clean_df=clean_df, 
            summary_df=consolidated_summary_df,
            sheet_key=GOOGLE_SHEET_KEY,
            week_number=current_week,
            error_df=invalid_df
        )

    print("\n--- Process Finished for this file ---")
    print(f"   - Final Clean Data:      {os.path.basename(clean_path)}")
    os.remove(temp_path)
    logging.info(f"--- Processing finished for file: {filename} ---")

def main():
    """Main function to find and process all CSV files."""
    print("Starting data processing script.")
    logging.info("="*50 + f"\nSCRIPT STARTED at {datetime.now()}\n" + "="*50)
    
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.csv')]
    if not files:
        print(f"No CSV files found in {INPUT_DIR}. Exiting.")
        return

    print(f"Found {len(files)} CSV file(s) to process.")
    for filename in files:
        process_single_file(os.path.join(INPUT_DIR, filename), OUTPUT_DIR)

    print(f"\n{'='*60}\n✅ All tasks completed for all files.")
    url = "https://docs.google.com/spreadsheets/d/1WKerK20EOlAE-FVGrA9HpE7o1LwNVZ7clmktbJsC33s/edit?usp=sharing"
    print(f'check the output on {url}')

    logging.info("="*50 + f"\nSCRIPT FINISHED at {datetime.now()}\n" + "="*50)

if __name__ == "__main__":
    main()