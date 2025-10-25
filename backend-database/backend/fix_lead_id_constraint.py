#!/usr/bin/env python3
"""
Quick fix migration to make lead_id nullable in call_logs table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models.lead_model import db
from sqlalchemy import text

def fix_lead_id_nullable():
    """Make lead_id column nullable in call_logs table"""
    with app.app_context():
        try:
            # Check if lead_id column exists and if it's nullable
            result = db.session.execute(text("""
                SELECT column_name, is_nullable, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'call_logs' AND column_name = 'lead_id'
            """)).fetchone()
            
            if result:
                column_name, is_nullable, data_type = result
                print(f"Found lead_id column: nullable={is_nullable}, type={data_type}")
                
                if is_nullable == 'NO':
                    print("Making lead_id column nullable...")
                    db.session.execute(text("""
                        ALTER TABLE call_logs 
                        ALTER COLUMN lead_id DROP NOT NULL
                    """))
                    db.session.commit()
                    print("✅ lead_id column is now nullable")
                else:
                    print("✅ lead_id column is already nullable")
            else:
                print("❌ lead_id column does not exist")
                
        except Exception as e:
            print(f"❌ Error fixing lead_id column: {e}")
            db.session.rollback()

def main():
    print("🔧 Fixing lead_id column constraint...")
    fix_lead_id_nullable()

if __name__ == "__main__":
    main()