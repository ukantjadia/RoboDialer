"""
Minimal Flask app for RoboDialer testing
This bypasses the main app.py dependency issues
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Configure CORS
CORS(app, origins=[
    "http://localhost:9002",
    "https://nonstatutory-contextured-selina.ngrok-free.dev"
], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
   allow_headers=["Content-Type", "Authorization"],
   supports_credentials=True)

# Import the RoboDialer blueprint
try:
    from services.backend_robodialer.database.app import robo_dailer_bp
    app.register_blueprint(robo_dailer_bp)
    print("✅ RoboDialer blueprint registered successfully")
except Exception as e:
    print(f"❌ Error importing RoboDialer blueprint: {e}")

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "RoboDialer backend is running",
        "ngrok_url": os.getenv('NGROK_URL', 'Not configured')
    })

@app.route('/')
def home():
    return jsonify({
        "service": "RoboDialer Backend",
        "status": "running",
        "endpoints": [
            "/health",
            "/api/v1/leads",
            "/api/v1/agents", 
            "/api/v1/call_logs",
            "/robodialer/*"
        ]
    })

if __name__ == '__main__':
    print("🚀 Starting RoboDialer backend...")
    print(f"📡 Ngrok URL: {os.getenv('NGROK_URL', 'Not configured')}")
    app.run(debug=True, host='0.0.0.0', port=8000)