#!/usr/bin/env python3
"""
Database migration to add missing score_given column to agents table
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import text

def migrate_agents_table():
    """Add missing score_given column to agents table"""
    
    try:
        from app import create_app
        from models.lead_model import db
        
        app = create_app()
        with app.app_context():
            print("Adding score_given column to agents table...")
            
            # Add the missing column
            db.session.execute(text("""
                ALTER TABLE agents 
                ADD COLUMN IF NOT EXISTS score_given FLOAT DEFAULT NULL;
            """))
            
            db.session.commit()
            print("✅ Successfully added score_given column")
            
            # Verify the column was added
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'agents' AND column_name = 'score_given';
            """))
            
            if result.fetchone():
                print("✅ Column verified in database")
                return True
            else:
                print("❌ Column not found after migration")
                return False
                
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    success = migrate_agents_table()
    if success:
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)