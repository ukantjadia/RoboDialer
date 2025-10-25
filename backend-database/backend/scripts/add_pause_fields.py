
"""
Database migration script to add pause-related fields to user_subscriptions table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.lead_model import db
from sqlalchemy import text

def add_pause_fields():
    """Add pause-related fields to user_subscriptions table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if fields already exist
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'user_subscriptions' 
                AND COLUMN_NAME IN ('is_paused', 'pause_end_date', 'original_plan_id', 'original_plan_name')
            """))
            existing_columns = [row[0] for row in result.fetchall()]
            
            # Add missing columns
            if 'is_paused' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN is_paused BOOLEAN DEFAULT FALSE"))
                print("Added is_paused column")
            
            if 'pause_end_date' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN pause_end_date DATETIME NULL"))
                print("Added pause_end_date column")
            
            if 'original_plan_id' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN original_plan_id INTEGER NULL"))
                print("Added original_plan_id column")
            
            if 'original_plan_name' not in existing_columns:
                db.session.execute(text("ALTER TABLE user_subscriptions ADD COLUMN original_plan_name VARCHAR(50) NULL"))
                print("Added original_plan_name column")
            
            db.session.commit()
            print("Successfully added pause fields to user_subscriptions table")
            
        except Exception as e:
            print(f"Error adding pause fields: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    add_pause_fields()
