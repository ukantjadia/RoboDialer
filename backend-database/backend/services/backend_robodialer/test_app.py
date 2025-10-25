from flask import Flask
from flask_cors import CORS
import os
import sys

# Add the parent directories to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.lead_model import db
from database.db_init import init_db_connection
from database.app import robo_dailer_bp

def create_test_app():
    """Create a minimal Flask app for testing RoboDialer"""
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost/test_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize CORS
    CORS(app, origins=[
        "http://localhost:9002",
        "http://localhost:3000",
        "http://localhost:5173"
    ], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True)
    
    # Initialize database
    init_db_connection(app)
    
    # Register the robodialer blueprint
    app.register_blueprint(robo_dailer_bp)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {"status": "healthy", "service": "robodialer"}, 200
    
    return app

if __name__ == '__main__':
    app = create_test_app()
    print("Starting RoboDialer test server on port 8000...")
    app.run(debug=True, host='0.0.0.0', port=8000)