import pandas as pd
import io
import re
from datetime import datetime
from models.lead_model import db, Lead
from controllers.lead_controller import LeadController
import chardet
from flask import flash
from flask import current_app
from controllers.contact_controller import ContactController

class UploadController:
    # Add field mapping dictionary at the start of the class
    FIELD_MAPPING = {
        # Legacy field mappings
        'title': 'owner_title',
        'linkedin_url': 'company_linkedin',
        'product_service_category': 'product_category',
        'employees_range': 'employees',
        'associated_members': 'employees',
        'rev_source': 'source',
        'owner_age': None,
        'additional_notes': None,

        # Case-sensitive field mappings with spaces
        'Company': 'company',
        'City': 'city',
        'State': 'state',
        'First Name': 'owner_first_name',
        'Last Name': 'owner_last_name',
        'Email': 'owner_email',
        'Title': 'owner_title',
        'Website': 'website',
        'LinkedIn URL': 'company_linkedin',
        'Industry': 'industry',
        'Revenue': 'revenue',
        'Product/Service Category': 'product_category',
        'Business Type (B2B, B2B2C)': 'business_type',
        'Employees range': 'employees',
        'Year Founded': 'year_founded',
        "Owner's LinkedIn": 'owner_linkedin',
        'Associated Members': 'employees',
        'Phone': 'phone',
        'Company Phone': 'company_phone',
        'Owner Phone': 'owner_phone_number',
        'Street': 'street',
        'BBB Rating': 'bbb_rating',

        # Fields to ignore
        'Score': None,
        'Email customization #1': None,
        'Subject Line #1': None,
        'Email Customization #2': None,
        'Subject Line #2': None,
        'LinkedIn Customization #1': None,
        'LinkedIn Customization #2': None,
        'Reasoning for r//y/g': None,
    }

    @staticmethod
    def map_field_name(field_name):
        """Map a field name to its database column name"""
        # First try exact match
        if field_name in UploadController.FIELD_MAPPING:
            return UploadController.FIELD_MAPPING[field_name]

        # Try case-insensitive match
        field_name_lower = field_name.lower()
        for key, value in UploadController.FIELD_MAPPING.items():
            if key.lower() == field_name_lower:
                return value

        # If no match found, return None
        return None

    @staticmethod
    def log_error(filename, row_number, data, reason):
        log_file = "upload_errors.log"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(log_file, "a", encoding='utf-8') as f:
            f.write(f"[{timestamp}] {filename} Row {row_number}: ")

            if "Success" in reason:
                company = data.get('company', 'Unknown')
                f.write(f"SUCCESS - Company: '{company}' - {reason}\n")
            elif "Skipped" in reason:
                company = data.get('company', 'Unknown')
                f.write(f"SKIPPED - {reason}\n")
            elif "Error" in reason:
                company = data.get('company', 'Unknown')
                f.write(f"ERROR - Company: '{company}' - {reason}\n")
                f.write(f"       Data: {data}\n")
            else:
                f.write(f"{reason}\n")
                f.write(f"Data: {data}\n")

    @staticmethod
    def write_log_separator(filename):
        log_file = "upload_errors.log"
        with open(log_file, "a", encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"New Upload Session - File: {filename} at {timestamp}\n")

    @staticmethod
    def clean_email(email):
        if pd.isna(email):
            return None
        return str(email).strip().lower()

    @staticmethod
    def clean_phone(phone):
        if pd.isna(phone):
            return None
        return re.sub(r'\D', '', str(phone))

    @staticmethod
    def clean_website(website):
        if pd.isna(website):
            return None
        return str(website).strip().lower()

    @staticmethod
    def clean_company(company):
        if pd.isna(company):
            return None
        return str(company).strip()

    @staticmethod
    def is_valid_email(email):
        if not email or pd.isna(email):
            return False
        EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
        return bool(EMAIL_REGEX.match(str(email).strip()))

    @staticmethod
    def is_valid_phone(phone):
        if not phone or pd.isna(phone):
            return False
        phone_str = re.sub(r'\D', '', str(phone))
        return phone_str.isdigit() and len(phone_str) >= 8

    @staticmethod
    def is_valid_website(website):
        if not website or pd.isna(website):
            return False
        return bool(website.strip())

    @staticmethod
    def is_valid_company(company):
        if not company or pd.isna(company):
            return False
        return bool(company.strip())

    @staticmethod
    def is_valid_row(name, email, phone):
        # Only validate company name, all other fields can be empty
        return True  # Remove validation since we want to allow empty fields

    @staticmethod
    def process_csv_file(file, name_col, email_col, phone_col, dynamic_fields=None, first_name_col=None, last_name_col=None):
        filename = file.filename
        UploadController.write_log_separator(filename)
        try:
            content = file.read()

            # Robust encoding detection and decoding
            if isinstance(content, bytes):
                detection = chardet.detect(content)
                detected_encoding = detection['encoding']
                encodings_to_try = [detected_encoding, 'utf-8', 'latin-1', 'windows-1252', 'ISO-8859-1']
                for encoding in encodings_to_try:
                    if not encoding:
                        continue
                    try:
                        content = content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise Exception("Could not decode the file with any common encoding")

            current_app.logger.info(f"[Upload] Starting upload for file: {filename}")

            df = pd.read_csv(io.StringIO(content))
            df.columns = df.columns.str.strip()

            # Explicitly convert potential phone number columns to string early
            if phone_col and phone_col in df.columns:
                df[phone_col] = df[phone_col].astype(str).str.replace('.0$', '', regex=True)
            if 'company_phone' in df.columns:
                df['company_phone'] = df['company_phone'].astype(str).str.replace('.0$', '', regex=True)
            if 'owner_phone_number' in df.columns:
                df['owner_phone_number'] = df['owner_phone_number'].astype(str).str.replace('.0$', '', regex=True)

            # Fill empty values with "-" for all columns
            df = df.fillna("-")

            # Only validate that the name column exists if provided
            if name_col and name_col not in df.columns:
                raise Exception(f"Missing required column: {name_col}")

            # Handle first_name and last_name columns if provided
            if first_name_col and first_name_col in df.columns:
                df['owner_first_name'] = df[first_name_col].apply(lambda x: str(x).strip() if str(x).strip() != "-" else "")
            else:
                df['owner_first_name'] = ""

            if last_name_col and last_name_col in df.columns:
                df['owner_last_name'] = df[last_name_col].apply(lambda x: str(x).strip() if str(x).strip() != "-" else "")
            else:
                df['owner_last_name'] = ""
                df['name'] = ""

            # Process name column if it exists
            if name_col and name_col in df.columns:
                df[name_col] = df[name_col].apply(lambda x: str(x).strip() if str(x).strip() != "-" else "")
                df['name'] = df[name_col]
                def split_name(name):
                    if not name or name == "-":
                        return "", ""
                    parts = name.strip().split()
                    if len(parts) == 0:
                        return "", ""
                    elif len(parts) == 1:
                        return parts[0], ""
                    else:
                        return parts[0], " ".join(parts[1:])
                df['owner_first_name'], df['owner_last_name'] = zip(*df['name'].map(split_name))
            else:
                if 'owner_first_name' not in df.columns:
                    df['owner_first_name'] = ""
                if 'owner_last_name' not in df.columns:
                    df['owner_last_name'] = ""
                df['name'] = ""

            # Always set name to first_name + last_name if name is empty
            df['name'] = df.apply(lambda row: row['name'] if row['name'] and row['name'] != "-" else f"{row.get('owner_first_name','')} {row.get('owner_last_name','')}".strip(), axis=1)

            # Process email and phone fields if they exist in the CSV
            df['owner_email'] = "" if email_col not in df.columns else df[email_col].apply(lambda x: UploadController.clean_email(x) if str(x).strip() != "-" else "")
            df['phone'] = "" if phone_col not in df.columns else df[phone_col].apply(lambda x: str(x).strip() if str(x).strip() != "-" else "")
            # Set company field - use name if company column doesn't exist
            # Normalize column names first
            df.columns = df.columns.str.lower()

            if 'company' not in df.columns:
                raise Exception("CSV file must contain a 'company' column.")
            else:
                df['company'] = df['company'].apply(lambda x: str(x).strip() if str(x).strip() != "-" else "")
            current_app.logger.info(f" this is the from {df}")

            # Instead of the old row loop, call the new upload_leads_and_contacts function
            added_new, skipped_duplicates, skipped_empty_company, errors = upload_leads_and_contacts(df, filename)
            # For compatibility, return the same tuple as before (added_new, updated, skipped_duplicates, skipped_empty_company, errors)
            # Since we don't track 'updated' in the new function, set updated=0
            updated = 0
            return added_new, skipped_duplicates, skipped_empty_company, errors

        except pd.errors.EmptyDataError:
            UploadController.log_error(filename, 0, {}, "The CSV file is empty")
            current_app.logger.error(f"[Upload] The CSV file is empty: {filename}")
            raise Exception("The CSV file is empty")
        except pd.errors.ParserError:
            UploadController.log_error(filename, 0, {}, "Invalid CSV format")
            current_app.logger.error(f"[Upload] Invalid CSV format: {filename}")
            raise Exception("Invalid CSV format")
        except Exception as e:
            print("sadfasdfasdfasdf")

            UploadController.log_error(filename, 0, {}, f"Error processing CSV: {str(e)}")
            current_app.logger.error(f"[Upload] Error processing CSV: {str(e)}")
            raise Exception(f"Error processing CSV: {str(e)}")

def upload_leads_and_contacts(df, filename='manual_upload.csv'):
    """
    Upload leads and contacts from a DataFrame. Does not modify existing code.
    """
    from models.lead_model import db, Lead
    from flask import current_app
    leads_added_count = 0
    leads_error_count = 0
    contacts_added_count = 0
    contacts_skipped_duplicate_count = 0
    contacts_error_count = 0
    contacts_updated_count = 0
    skipped_empty_company = 0
    skipped_details = []
    processed_contacts_in_batch = set()
    for idx, row in df.iterrows():
        # Log the raw data from the file/frontend
        current_app.logger.info(f"[Upload] Raw data from file for row {idx+2}: {row.to_dict()}")

        try:
            # Get company value and skip if empty
            company_value = row.get('company', '')
            # Normalize company_value to scalar
            if hasattr(company_value, 'to_list'):
                vals = company_value.to_list()
                company_value = vals[0] if vals else ''
            elif hasattr(company_value, 'iloc'):
                company_value = company_value.iloc[0] if not company_value.empty else ''
            elif isinstance(company_value, (list, tuple)) and len(company_value) == 1:
                company_value = company_value[0]
            elif isinstance(company_value, (list, tuple)) and len(company_value) == 0:
                company_value = ''
            company_value = str(company_value).strip()
            industry_value = str(row.get('industry', '')).strip()
            current_app.logger.info(f"[Upload] Processing row {idx+2}: company={company_value}, industry={industry_value}")
            if not company_value:
                skipped_empty_company += 1
                error_message = f"Row {idx+2}: Empty company value, skipped."
                skipped_details.append(error_message)
                UploadController.log_error(filename, idx + 2, row.to_dict(), f"Skipped (empty company): Company value is empty")
                current_app.logger.warning(f"[Upload] Skipped row {idx+2} due to empty company value.")
                continue  # Skip this row

            try:
                # Check if lead exists by company
                lead = Lead.query.filter_by(company=company_value, deleted=False).first()
                is_new_lead = False
                if not lead:
                    # Create new lead (primary contact info from this row)
                    lead_data = {
                        'search_keyword': {},
                        'source': 'manual',
                        'company': company_value,
                        'industry': industry_value,
                        'status': 'new'
                    }
                    # Copy all lead fields from row if present, using the same cleaning logic as main mapping
                    for field in Lead.__table__.columns.keys():
                        # Use the new, standardized DataFrame column names directly
                        if field in row and field not in lead_data:
                            value = row[field]
                            if hasattr(value, 'dtype') and str(type(value)).endswith("Series'>"):
                                value = value.astype(str).str.cat(sep=', ')
                            if value != "-":
                                if field in ['is_edited', 'deleted']:
                                    lead_data[field] = value

                                value = str(value).strip()
                                if field == 'employees':
                                    try:
                                        if '-' in value:
                                            value = int(value.split('-')[0].strip())
                                        else:
                                            value = int(value)
                                    except (ValueError, TypeError):
                                        value = None
                                elif field == 'revenue':
                                    try:
                                        value = float(value.replace('$', '').replace('M', '000000').replace('K', '000'))
                                    except (ValueError, TypeError):
                                        value = None
                                elif field == 'year_founded':
                                    try:
                                        value = str(int(float(value)))
                                    except (ValueError, TypeError):
                                        value = None

                                # --- NEW LOGIC: Handle first phone number for Lead table directly here ---
                                if field in ['phone', 'owner_phone_number', 'company_phone']:
                                    # Helper to extract and clean the first phone number
                                    def _get_first_phone_for_lead(raw_val):
                                        if hasattr(raw_val, 'to_list'):
                                            vals = raw_val.to_list()
                                            raw_val = vals[0] if vals else ''
                                        elif hasattr(raw_val, 'iloc'):
                                            raw_val = raw_val.iloc[0] if not raw_val.empty else ''
                                        elif isinstance(raw_val, (list, tuple)) and len(raw_val) == 1:
                                            raw_val = raw_val[0]
                                        elif isinstance(raw_val, (list, tuple)) and len(raw_val) == 0:
                                            raw_val = ''

                                        raw_val_str = str(raw_val).strip()
                                        if not raw_val_str or raw_val_str == '-':
                                            return None

                                        first_part = raw_val_str.split(',')[0].strip()
                                        return UploadController.clean_phone(first_part)

                                    cleaned_first_phone = _get_first_phone_for_lead(value)
                                    if cleaned_first_phone:
                                        lead_data[field] = cleaned_first_phone
                                    else:
                                        lead_data[field] = None # Ensure it's None if not valid
                                else:
                                    if value not in (None, '', 'nan', 'NaN', 'None'):
                                        lead_data[field] = value
                    lead = Lead(**lead_data)
                    db.session.add(lead)
                    db.session.flush()
                    is_new_lead = True
                    leads_added_count += 1 # Increment lead added count
                    current_app.logger.info(f"[Upload] Created new lead for company={company_value}. Data: {lead_data}")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"[Upload] Error creating or fetching lead for company={company_value}: {str(e)}")
                leads_error_count += 1 # Increment lead error count
                continue

            # Prepare contact data (handle both single and comma-separated multiple contacts)
            # Define all contact fields as expected by ContactController (these are the keys in contact_data)
            all_contact_fields = [
                'phone', 'owner phone', 'company phone', 'owner_first_name', 'owner_last_name',
                'owner title', 'owner linkedin', 'owner_email', 'city', 'state'
            ]
            phone_fields = ['phone', 'owner phone', 'company phone']

            # Extract base contact data (non-phone fields)
            base_contact_data = {}
            for field in all_contact_fields:
                if field not in phone_fields:
                    val = row.get(field, '')
                    # Normalize scalar values from row
                    if hasattr(val, 'to_list'):
                        vals = val.to_list()
                        val = vals[0] if vals else ''
                    elif hasattr(val, 'iloc'):
                        val = val.iloc[0] if not val.empty else ''
                    elif isinstance(val, (list, tuple)) and len(val) == 1:
                        val = val[0]
                    elif isinstance(val, (list, tuple)) and len(val) == 0:
                        val = ''
                    base_contact_data[field] = str(val).strip() if val is not None else ''

            # Collect all individual phone entries with their original column
            all_individual_phone_entries = [] # Stores (phone_value, original_column_name)

            for phone_field in phone_fields:
                val = row.get(phone_field, '')
                # Normalize scalar values from row before processing
                if hasattr(val, 'to_list'):
                    vals = val.to_list()
                    val = vals[0] if vals else ''
                elif hasattr(val, 'iloc'):
                    val = val.iloc[0] if not val.empty else ''
                elif isinstance(val, (list, tuple)) and len(val) == 1:
                    val = val[0]
                elif isinstance(val, (list, tuple)) and len(val) == 0:
                    val = ''

                if isinstance(val, str) and ',' in val:
                    individual_numbers = [v.strip() for v in val.split(',') if v.strip()]
                    for num in individual_numbers:
                        all_individual_phone_entries.append((UploadController.clean_phone(num), phone_field))
                elif val and str(val).strip() != '-' and str(val).strip() != '': # Handle single non-empty phone number
                    all_individual_phone_entries.append((UploadController.clean_phone(str(val).strip()), phone_field))

            # Determine contacts to create
            contacts_to_process = []
            if not all_individual_phone_entries:
                # No phone numbers found, create one contact with empty phone fields
                current_contact_data = base_contact_data.copy()
                for pf in phone_fields:
                    current_contact_data[pf] = '' # Ensure phone fields are empty
                contacts_to_process.append(current_contact_data)
            else:
                # For each individual phone number, create a new contact
                for phone_value, original_column_name in all_individual_phone_entries:
                    current_contact_data = base_contact_data.copy()
                    for pf in phone_fields:
                        current_contact_data[pf] = '' # Clear all phone fields first
                    current_contact_data[original_column_name] = UploadController.clean_phone(phone_value) # Set only the relevant phone field
                    contacts_to_process.append(current_contact_data)

            current_app.logger.info(f" this sithe contacnt to proces {contacts_to_process}")
            # Add all contacts (ContactController handles deduplication)
            # The 'is_primary' flag should only be true for the very first contact derived from this row.
            first_contact_processed = False
            for contact_data in contacts_to_process:
                owner_phone = str(contact_data.get('owner phone', '')).strip()
                owner_email = str(contact_data.get('owner_email', '')).strip()
                first_name = str(contact_data.get('owner_first_name', '')).strip()
                last_name = str(contact_data.get('last_name', '')).strip()
                contact_key = (lead.lead_id, owner_phone, owner_email, first_name, last_name)
                if contact_key in processed_contacts_in_batch:
                    continue

                processed_contacts_in_batch.add(contact_key)

                is_this_primary = is_new_lead and not first_contact_processed
                current_app.logger.info(f"[Upload] Attempting to add contact for lead_id={lead.lead_id}. Contact data: {contact_data}")
                try:
                    contact, created, reason = ContactController.add_contact(lead.lead_id, contact_data, is_primary=is_this_primary)
                    if created:
                        current_app.logger.info(f"[Upload] Contact added successfully for lead_id={lead.lead_id}, is_primary={is_this_primary}")
                        contacts_added_count += 1 # Increment contact added count
                    elif reason == 'updated':
                        contacts_updated_count += 1 # Increment the new update counter
                    elif reason == 'duplicate':
                        current_app.logger.info(f"[Upload] Duplicate contact skipped for lead_id={lead.lead_id}")
                        contacts_skipped_duplicate_count += 1 # Increment contact skipped count
                    else:
                        current_app.logger.warning(f"[Upload] Contact not added for lead_id={lead.lead_id}: {reason}")
                        contacts_error_count += 1 # Increment contact error count
                    first_contact_processed = True # Mark that the first contact has been processed
                except Exception as e:
                    current_app.logger.error(f"[Upload] Error adding contact for lead_id={lead.lead_id}: {str(e)}")
                    contacts_error_count += 1 # Increment contact error count
        except Exception as e:
            # This catches general errors during row processing (e.g., data parsing issues).
            # We'll associate these with lead errors for now, as lead creation is the first step for a row.
            leads_error_count += 1
            reason = f"Error processing row: {str(e)}"
            UploadController.log_error(filename, idx + 2, row.to_dict(), reason)
            skipped_details.append(f"Row {idx+2}: {reason}")
            current_app.logger.error(f"[Upload] {reason}")

    # Final log messages with separated counts
    current_app.logger.info(f"[Upload] Finished upload in Leads table: {leads_added_count} added, {leads_error_count} errors, {skipped_empty_company} skipped (empty company).")
    current_app.logger.info(f"[Upload] Finished upload in Contacts table: {contacts_added_count} added, {contacts_skipped_duplicate_count} duplicates, {contacts_error_count} errors.")

    total_errors = leads_error_count + contacts_error_count
    # Return values for compatibility with process_csv_file
    return (contacts_added_count, contacts_updated_count), contacts_skipped_duplicate_count, skipped_empty_company, total_errors