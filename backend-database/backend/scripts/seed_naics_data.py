import sys
import os
import pandas as pd
import numpy as np

# Add parent directory to path to run script independently
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.lead_model import db
from models.industry_naics_mapping_model import IndustryNAICSMappings
from sqlalchemy import inspect

def seed_naics_data():
    """
    Creates the 'industry_naics_mapping' table if it doesn't exist,
    then reads NAICS data from an Excel file and bulk inserts it.
    Includes a check to prevent running if the table already exists.
    """
    app = create_app()
    with app.app_context():
        print("Starting NAICS data seeding process...")
        
        inspector = inspect(db.engine)
        table_name = IndustryNAICSMappings.__tablename__

        # --- SAFETY CHECK & OVERWRITE PROMPT ---
        if inspector.has_table(table_name):
            print(f"--- WARNING ---")
            print(f"Table '{table_name}' already exists in the database.")
            
            print("\n--- Existing Data Preview ---")
            try:
                existing_df = pd.read_sql_table(table_name, db.engine)
                if not existing_df.empty:
                    # Display a limited number of columns for wider tables
                    pd.set_option('display.max_columns', 10)
                    if len(existing_df) > 10:
                        preview_df = pd.concat([existing_df.head(5), existing_df.tail(5)])
                        print(preview_df.to_string())
                    else:
                        print(existing_df.to_string())
                    print(f"\nFound {len(existing_df)} existing records.")
                else:
                    print("Table is empty.")
            except Exception as e:
                print(f"Could not read existing data: {e}")

            print(f"\nYou are about to DELETE this table and replace it with content from the Excel file.")
            confirm_delete = input("Are you sure you want to overwrite? Type 'yes' to proceed: ")

            if confirm_delete.lower() != 'yes':
                print("\nOperation cancelled by user.")
                return
            
            print(f"\nDropping table '{table_name}'...")
            IndustryNAICSMappings.__table__.drop(db.engine)
            print("Table dropped.")

        try:
            # 1. Load Excel file
            excel_path = os.path.join(os.path.dirname(__file__), 'industry_naics.xlsx')
            if not os.path.exists(excel_path):
                print(f"Error: Excel file not found at {excel_path}")
                print("Please make sure 'industry_naics.xlsx' is in the 'scripts' directory.")
                return

            df = pd.read_excel(excel_path, header=1)
            print(f"Loaded {len(df)} rows from Excel file.")

            df = pd.read_excel(excel_path, header=1)
            print(f"Loaded {len(df)} rows from Excel file.")

            # 2. Clean and prepare the data
            # Remove unwanted columns (including unnamed columns)
            columns_to_drop = ["Unnamed: 0", "No."]
            # Add any columns that start with "Unnamed:" to the drop list
            unnamed_cols = [col for col in df.columns if col.startswith("Unnamed:")]
            columns_to_drop.extend(unnamed_cols)
            
            for col in columns_to_drop:
                if col in df.columns:
                    df = df.drop(columns=[col])
                    print(f"Dropped column: {col}")

            # Map Excel columns to database column names (matching the model exactly)
            col_map = {
                "Exact Industry": "exact_industry",
                "Corrected Industry": "corrected_industry", 
                "Similar NAICS Industry": "similar_naics_industry_name",
                "Parent NAICS Industry Name": "parent_naics_industry_name",
                "Similar NAICS Industry Code": "similar_naics_industry_code",
                "Parent NAICS Industry Code": "parent_naics_industry_code"
            }
            
            # Check if all expected columns exist before renaming
            missing_excel_cols = [col for col in col_map.keys() if col not in df.columns]
            if missing_excel_cols:
                print(f"Error: Missing expected columns in Excel file: {missing_excel_cols}")
                print(f"Available columns: {list(df.columns)}")
                return
            
            df = df.rename(columns=col_map)
            
            # Only keep the columns we need (remove any extra columns)
            required_cols = list(col_map.values())
            df = df[required_cols]
            
            print(f"Final DataFrame shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            
            # Convert NaN to None and ensure proper data types
            df = df.replace({np.nan: None})
            
            # Convert NAICS codes to strings to match model
            df['similar_naics_industry_code'] = df['similar_naics_industry_code'].astype(str).replace('nan', None)
            df['parent_naics_industry_code'] = df['parent_naics_industry_code'].astype(str).replace('nan', None)
            
            data_to_insert = df.to_dict(orient='records')

            # 3. Show preview
            print("\n--- Data Preview ---")
            if len(data_to_insert) > 10:
                preview_df = pd.concat([df.head(5), df.tail(5)])
                print(preview_df.to_string())
            else:
                print(df.to_string())
            
            print("\n--- Confirmation ---")
            print(f"You are about to CREATE the '{table_name}' table")
            print(f"and INSERT {len(data_to_insert)} new records.")
            
            confirm = input("Are you sure you want to continue? Type 'yes' to proceed: ")

            if confirm.lower() != 'yes':
                print("\nOperation cancelled by user.")
                return

            # 4. Create the table and insert data
            print("\nProceeding with database operation...")
            print(f"Creating table '{table_name}'...")
            db.create_all()
            print("Table created.")

            print(f"Bulk inserting {len(data_to_insert)} records...")
            db.session.bulk_insert_mappings(IndustryNAICSMappings, data_to_insert)
            db.session.commit()
            print("NAICS data seeding complete.")

        except Exception as e:
            db.session.rollback()
            print(f"\nAn error occurred: {str(e)}")

if __name__ == '__main__':
    seed_naics_data()
