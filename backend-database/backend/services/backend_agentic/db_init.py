"""
Database initialization for agentic backend
"""
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Add path to access models
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

def init_db_connection():
    """Initialize database connection for agentic backend"""
    try:
        # Create a minimal Flask app for database context
        app = Flask(__name__)
        
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            # Fallback to default database configuration
            database_url = "postgresql://username:password@localhost/database_name"
            print("Warning: DATABASE_URL not set, using default")
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database
        from models.lead_model import db
        db.init_app(app)
        
        # Test connection
        with app.app_context():
            # Use text() for raw SQL in SQLAlchemy 2.x
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            print("✅ Database connection successful")
            return app, db
            
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return None, None

if __name__ == "__main__":
    app, db = init_db_connection()
    if app and db:
        print("Database initialization completed successfully")
    else:
        print("Database initialization failed")