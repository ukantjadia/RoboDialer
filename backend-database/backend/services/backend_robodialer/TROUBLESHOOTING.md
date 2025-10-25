# 🔧 RoboDialer Troubleshooting Guide

## 🚨 Quick Fixes for Common Issues

### 1. Backend Won't Start
**Error:** `ModuleNotFoundError` or import errors

**Solution:**
```bash
# Make sure you're in the right directory
cd LeadGenAI/backend-database/backend/

# Reinstall dependencies
pip install -r requirements.txt

# Try running from correct location
python app.py
```

### 2. Frontend Shows "No Agents Found"
**Error:** Empty agents list or API connection failed

**Solution:**
```bash
# Check if backend is running
curl http://localhost:8000/api/v1/agents

# If not running, start backend first
cd LeadGenAI/backend-database/backend/
python app.py

# Check frontend environment
cd services/backend_robodialer/frontend/
# Verify .env.local has: NEXT_PUBLIC_BASE_URL=http://localhost:8000
```

### 3. "Not Valid" Errors When Calling
**Error:** Phone number validation fails

**Solution:**
- Ensure phone numbers are in E.164 format: `+1234567890`
- Check CSV file has proper phone number column
- Verify Twilio credentials in `.env` file

### 4. Wrong Numbers in Call History
**Error:** Call history shows incorrect phone numbers

**Solution:**
```bash
# This issue was fixed with database migration
# If still seeing issues, restart backend:
cd LeadGenAI/backend-database/backend/
python app.py
```

### 5. Can't Save Notes
**Error:** Notes don't persist after refresh

**Solution:**
```bash
# Restart backend to ensure PUT endpoint is active
cd LeadGenAI/backend-database/backend/
python app.py

# Verify in browser console - should see successful PUT requests
```

### 6. Twilio ConnectionError (31005)
**Error:** Gateway connection failed

**Solution:**
1. **Start ngrok:** `ngrok http 8000`
2. **Copy ngrok URL** (e.g., `https://abc123.ngrok-free.app`)
3. **Update .env files:**
   ```env
   NGROK_URL=https://your-new-ngrok-url.ngrok-free.app
   BASE_URL=https://your-new-ngrok-url.ngrok-free.app
   ```
4. **Update Twilio Console:**
   - Go to TwiML Apps
   - Set Voice URL: `https://your-ngrok-url.ngrok-free.app/api/twilio/voice`
5. **Restart backend**

### 7. Auto-Voicemail Not Working
**Error:** No voicemail sent when call disconnects

**Solution:**
- Ensure ngrok is running and webhooks configured
- Check browser console for JavaScript errors
- Verify backend logs show voicemail requests

### 8. Frontend Won't Load
**Error:** Next.js compilation errors

**Solution:**
```bash
cd frontend/
rm -rf .next node_modules
npm install
npm run dev
```

### 9. Database Connection Errors
**Error:** Can't connect to PostgreSQL

**Solution:**
- Check `DATABASE_URL` in `.env` file
- Verify Railway database is accessible
- Test connection with database client

### 10. Call Logs Disappearing
**Error:** Call history empty after refresh

**Solution:**
- Ensure backend is running and database connected
- Check browser console for API errors
- Verify database migrations completed

## 🔍 Debug Commands

### Check Backend Health
```bash
curl http://localhost:8000/api/v1/agents
# Should return JSON array
```

### Check Frontend Connection
```bash
# In browser console:
fetch('/api/agents').then(r => r.json()).then(console.log)
# Should return agents data
```

### Check Ngrok Status
```bash
curl http://localhost:4040/api/tunnels
# Shows active ngrok tunnels
```

### Check Database Connection
```bash
# In Python shell from backend directory:
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
print(engine.execute('SELECT 1').fetchone())
```

## 📋 Service Status Checklist

- [ ] **Backend running:** http://localhost:8000 responds
- [ ] **Frontend running:** http://localhost:9002 loads
- [ ] **Ngrok active:** Shows forwarding URL
- [ ] **Database connected:** Backend logs show no DB errors
- [ ] **Twilio configured:** Webhooks point to ngrok URL

## 🚀 Restart Everything (Nuclear Option)

If nothing else works, restart all services:

```bash
# 1. Stop all services (Ctrl+C in each terminal)

# 2. Start backend
cd LeadGenAI/backend-database/backend/
python app.py

# 3. Start ngrok (new terminal)
ngrok http 8000

# 4. Update .env with new ngrok URL

# 5. Restart backend
# Ctrl+C, then: python app.py

# 6. Start frontend (new terminal)
cd services/backend_robodialer/frontend/
npm run dev
```

## 📞 Still Need Help?

### Check Logs
1. **Backend logs:** Look at terminal where `python app.py` is running
2. **Frontend logs:** Check browser console (F12)
3. **Ngrok logs:** Check ngrok terminal for webhook requests

### Common Log Messages
- **"Agent registered successfully"** ✅ Good
- **"Database connected"** ✅ Good  
- **"ImportError"** ❌ Check directory and dependencies
- **"Connection refused"** ❌ Check if services are running
- **"CORS error"** ❌ Check environment variables

### Environment Variable Check
```bash
# Check if .env is loaded correctly:
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('TWILIO_ACCOUNT_SID'))"
# Should print your Twilio SID, not None
```

---

**Most issues are solved by ensuring all services are running in the correct order and environment variables are properly configured!** 🎯