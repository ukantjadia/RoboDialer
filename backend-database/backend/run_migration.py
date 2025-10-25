import os
import sys

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

try:
    from app import app
    from models.lead_model import db
    from sqlalchemy import text
    
    print("Running database migration...")
    
    with app.app_context():
        try:
            # Add direction column
            db.session.execute(text("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS direction VARCHAR(20) NOT NULL DEFAULT 'outgoing'"))
            print("✓ Added direction column")
            
            # Add status column
            db.session.execute(text("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'completed'"))
            print("✓ Added status column")
            
            # Add action_taken column
            db.session.execute(text("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS action_taken VARCHAR(50) NOT NULL DEFAULT 'call'"))
            print("✓ Added action_taken column")
            
            # Add contact_name column
            db.session.execute(text("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS contact_name VARCHAR(255)"))
            print("✓ Added contact_name column")
            
            db.session.commit()
            print("🎉 Database migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")
            
except Exception as e:
    print(f"❌ Failed to import modules: {e}")
    print("Make sure you're running this from the backend directory with the virtual environment activated")