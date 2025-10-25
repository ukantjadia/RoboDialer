# RoboDialer Integration Setup Guide

## 🎯 Quick Summary

This RoboDialer system is integrated into the main Flask application. Here's the correct way to run it:

### 🚀 Correct Startup Process:

1. **Main Backend** (Terminal 1):
   ```bash
   cd LeadGenAI/backend-database/backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python app.py  # 🚀 This is the main entry point
   ```

2. **Ngrok Tunnel** (Terminal 2):
   ```bash
   ngrok http 8000
   # Copy the HTTPS URL
   ```

3. **Update Environment Variables**:
   - Edit `services/backend_robodialer/.env` with ngrok URL
   - Edit `services/backend_robodialer/frontend/.env.local` with ngrok URL

4. **Restart Backend** (Terminal 1):
   ```bash
   # Ctrl+C to stop, then restart
   python app.py
   ```

5. **Frontend** (Terminal 3):
   ```bash
   cd services/backend_robodialer/frontend
   npm install
   npm run dev
   ```

### 🏗️ Architecture Overview:

```
Main Flask App (app.py)
├── Registers RoboDialer Blueprint
├── Handles all routes (/api/v1/*, /api/twilio/*)
├── Connects to shared database
└── Serves at http://localhost:8000

RoboDialer Frontend (Next.js)
├── Runs independently at http://localhost:9002  
├── Makes API calls to main backend (port 8000)
└── Proxies requests through its own API routes
```

### ✅ Verification Steps:

1. **Backend Running**: `curl http://localhost:8000/api/v1/agents`
2. **Frontend Running**: Open `http://localhost:9002`
3. **Integration Working**: Frontend should show agent data

### 🔧 Environment Files:

- **Main Backend**: `backend-database/backend/.env` (database, core settings)
- **RoboDialer Service**: `services/backend_robodialer/.env` (Twilio, AI services)
- **Frontend**: `services/backend_robodialer/frontend/.env.local` (ngrok URLs)

### 🛠️ Common Issues:

- **Import Error**: Check RoboDialer blueprint import in main `app.py`
- **No Agents**: Ensure main backend is running, not just service
- **CORS Error**: Verify frontend URL in main backend CORS settings
- **Webhook Fail**: Update ngrok URL in RoboDialer `.env` file

This setup allows the RoboDialer to be a modular service within the larger application ecosystem while maintaining proper separation of concerns.