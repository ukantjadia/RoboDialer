import os
from flask import current_app
from dotenv import load_dotenv
from models.lead_model import db  # Always import the shared db

load_dotenv()

def init_db_connection(app):
    """
    Initialize database connection for agentic backend.
    """
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            database_url = "postgresql://username:password@localhost/database_name"
            app.logger.warning("Warning: DATABASE_URL not set, using default")
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        app.logger.info("Database configured successfully (connection deferred until first use).")
        return db
    except Exception as e:
        app.logger.critical(f"❌ Database configuration failed: {str(e)}", exc_info=True)
        raise RuntimeError("Database configuration failed.") from e