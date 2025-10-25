#!/usr/bin/env python3
"""
Database migration script to increase phone_number field length in call_logs table
From VARCHAR(20) to VARCHAR(100) to accommodate company names
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from models.lead_model import db
from app import create_app
import logging

def migrate_phone_number_field():
    """Migrate phone_number field from VARCHAR(20) to VARCHAR(100)"""
    
    # Create app context
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Starting phone_number field migration...")
            
            # Get the database engine
            engine = db.engine
            
            # Execute the ALTER TABLE command
            with engine.connect() as connection:
                # Start a transaction
                trans = connection.begin()
                
                try:
                    # Alter the phone_number column to increase its length
                    sql_command = text("""
                        ALTER TABLE call_logs 
                        ALTER COLUMN phone_number TYPE VARCHAR(100)
                    """)
                    
                    print("📝 Executing SQL: ALTER TABLE call_logs ALTER COLUMN phone_number TYPE VARCHAR(100)")
                    connection.execute(sql_command)
                    
                    # Commit the transaction
                    trans.commit()
                    print("✅ Successfully migrated phone_number field from VARCHAR(20) to VARCHAR(100)")
                    
                except Exception as e:
                    # Rollback on error
                    trans.rollback()
                    print(f"❌ Migration failed: {e}")
                    raise
                    
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            return False
            
    return True

if __name__ == "__main__":
    print("🚀 Database Migration: Increase phone_number field length")
    print("=" * 60)
    
    success = migrate_phone_number_field()
    
    if success:
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("📞 The phone_number field can now store up to 100 characters")
        print("🏢 Company names like 'Kartik Babu Enterprises' will now work")
    else:
        print("=" * 60)
        print("❌ Migration failed!")
        sys.exit(1)