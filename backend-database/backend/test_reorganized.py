#!/usr/bin/env python3
"""
Test script for the reorganized backend_robodialer structure
"""

import sys
import os

# Add the backend directory to the Python path
backend_dir = os.path.abspath('.')
sys.path.insert(0, backend_dir)

print("🧪 Testing reorganized backend_robodialer structure...")

try:
    print("📦 Testing import: services.backend_robodialer.database.app")
    from services.backend_robodialer.database.app import robo_dailer_bp
    print("✅ Successfully imported robo_dailer_bp")
    
    print("📦 Testing import: services.backend_robodialer.database.db_init")
    from services.backend_robodialer.database.db_init import init_db_connection
    print("✅ Successfully imported init_db_connection")
    
    print("🎯 All imports successful! Reorganized structure is working.")
    
    # Test Flask app creation
    from flask import Flask
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app, origins=["http://localhost:9002"])
    
    # Configure basic settings
    app.config['SECRET_KEY'] = 'test-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:pxSCPAqSemXWprAzugNqlkrYOnwCfvmV@yamanote.proxy.rlwy.net:36486/railway'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    print("🚀 Initializing database connection...")
    init_db_connection(app)
    
    print("📋 Registering RoboDialer blueprint...")
    app.register_blueprint(robo_dailer_bp)
    
    @app.route('/health')
    def health():
        return {"status": "healthy", "message": "Reorganized backend_robodialer is working!"}
    
    print("✅ Test Flask app created successfully!")
    print("🌟 Starting test server on port 8000...")
    
    app.run(debug=True, host='0.0.0.0', port=8000)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()