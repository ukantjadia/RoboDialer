#!/usr/bin/env python3
"""
Check what data exists in the user_lead_drafts table
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add path to access models
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

def check_database_data():
    """Check what data exists in the database"""
    try:
        print("🔍 Checking database data...")
        
        # Create a minimal Flask app
        app = Flask(__name__)
        
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not set")
            return False
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database
        db = SQLAlchemy(app)
        
        with app.app_context():
            # Check total records
            result = db.session.execute(text("SELECT COUNT(*) FROM user_lead_drafts"))
            total_count = result.scalar()
            print(f"📊 Total records in user_lead_drafts: {total_count}")
            
            if total_count > 0:
                # Check deleted records
                result = db.session.execute(text("SELECT COUNT(*) FROM user_lead_drafts WHERE is_deleted = true"))
                deleted_count = result.scalar()
                print(f"🗑️  Deleted records: {deleted_count}")
                
                # Check records with null draft_data
                result = db.session.execute(text("SELECT COUNT(*) FROM user_lead_drafts WHERE draft_data IS NULL"))
                null_data_count = result.scalar()
                print(f"📝 Records with null draft_data: {null_data_count}")
                
                # Check valid records
                result = db.session.execute(text("""
                    SELECT COUNT(*) FROM user_lead_drafts 
                    WHERE is_deleted = false AND draft_data IS NOT NULL
                """))
                valid_count = result.scalar()
                print(f"✅ Valid records (not deleted, has draft_data): {valid_count}")
                
                # Show sample of first few records
                result = db.session.execute(text("""
                    SELECT id, user_id, is_deleted, 
                           CASE WHEN draft_data IS NULL THEN 'NULL' ELSE 'HAS_DATA' END as data_status
                    FROM user_lead_drafts 
                    LIMIT 5
                """))
                records = result.fetchall()
                print("\n📋 Sample records:")
                for record in records:
                    print(f"   ID: {record[0]}, User: {record[1]}, Deleted: {record[2]}, Data: {record[3]}")
                
                # If we have valid records, show a sample draft_data
                if valid_count > 0:
                    result = db.session.execute(text("""
                        SELECT draft_data FROM user_lead_drafts 
                        WHERE is_deleted = false AND draft_data IS NOT NULL 
                        LIMIT 1
                    """))
                    sample = result.fetchone()
                    if sample and sample[0]:
                        print(f"\n🔍 Sample draft_data keys: {list(sample[0].keys())}")
                        # Show a few key-value pairs
                        sample_data = sample[0]
                        for i, (key, value) in enumerate(sample_data.items()):
                            if i >= 3:  # Show only first 3 items
                                break
                            print(f"   {key}: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}")
            
            else:
                print("📭 No records found in user_lead_drafts table")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database data: {str(e)}")
        return False

if __name__ == "__main__":
    check_database_data()