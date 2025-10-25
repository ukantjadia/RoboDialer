"""
Database migration script to add new columns to call_logs table
Run this script from the backend directory: python migrate_call_logs.py
"""

from app import app
from models.lead_model import db
from sqlalchemy import text
import logging

def migrate_call_logs_table():
    """Add new columns to call_logs table"""
    
    with app.app_context():
        migrations = [
            # Add direction column
            "ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS direction VARCHAR(20) NOT NULL DEFAULT 'outgoing'",
            
            # Add status column  
            "ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'completed'",
            
            # Add action_taken column
            "ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS action_taken VARCHAR(50) NOT NULL DEFAULT 'call'",
            
            # Add contact_name column
            "ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS contact_name VARCHAR(255)",
        ]
        
        try:
            for migration in migrations:
                db.session.execute(text(migration))
                logging.info(f"Executed: {migration}")
            
            db.session.commit()
            logging.info("Database migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the migration
    migrate_call_logs_table()
    print("Migration completed!")