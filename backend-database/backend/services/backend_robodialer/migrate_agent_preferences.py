#!/usr/bin/env python3
"""
Migration script to add agent preferences and archiving functionality
"""

import sys
import os

# Add the backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, '..', '..')
sys.path.append(backend_dir)

from app import create_app
from models.lead_model import db
from models.cold_call_agent_model import Agent, AgentPreferences

def migrate_database():
    """Run the database migration"""
    app = create_app()
    with app.app_context():
        try:
            print("🔄 Starting database migration...")
            
            # Create all tables (will create AgentPreferences table if it doesn't exist)
            db.create_all()
            db.session.commit()
            print("✅ AgentPreferences table created successfully")
            
            # Add is_archived column to existing agents if it doesn't exist
            try:
                # Check if is_archived column exists by trying to query it
                result = db.session.execute(db.text("SELECT is_archived FROM agents LIMIT 1")).fetchone()
                print("✅ is_archived column already exists")
            except Exception as e:
                # Column doesn't exist, rollback the failed transaction and add it
                db.session.rollback()
                print("⚡ Adding is_archived column to agents table...")
                db.session.execute(db.text("ALTER TABLE agents ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE"))
                db.session.commit()
                print("✅ is_archived column added successfully")
            
            print("🎉 Database migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    migrate_database()