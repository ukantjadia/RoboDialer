# 🤖 RoboDialer Setup Guide

**Complete setup guide for the AI-Powered RoboDialer System with auto-voicemail, call logging, and notes functionality.**

## 📋 Prerequisites

- **Python 3.8+**
- **Node.js 16+** 
- **PostgreSQL** (Railway or local)
- **Twilio Account** with verified phone number
- **Ngrok** (essential for webhooks)

## 🚀 Quick Setup (5 Steps)

### Step 1: Install Ngrok (REQUIRED)

**Windows:**
```powershell
winget install ngrok.ngrok
# Restart PowerShell after installation
```

**Mac/Linux:**
```bash
brew install ngrok  # Mac
# or visit https://ngrok.com/download
```

### Step 2: Clone & Navigate
```bash
git clone [your-repo]
cd LeadGenAI/backend-database/backend/services/backend_robodialer
```

### Step 3: Configure Environment

**Copy and edit the main environment file:**
```bash
cp .env.example .env
```

**Edit `.env` with your credentials:**
```env
# Twilio (Get from Twilio Console)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY_SID=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret
TWILIO_TWIML_APP_SID=APxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_CALLER_ID=+1234567890

# Database (Railway or local PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/database

# AI Services (Optional but recommended)
DEEPSEEK_API_KEY=your_deepseek_key
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key
GEMINI_API_KEY=your_gemini_key

# These will be updated after starting ngrok
NGROK_URL=https://your-ngrok-url.ngrok-free.dev
BASE_URL=https://your-ngrok-url.ngrok-free.dev
```

**Frontend environment:**
```bash
cd frontend
cp .env.example .env.local
# Edit .env.local with same values as above (with NEXT_PUBLIC_ prefixes)
```

### Step 4: Start Services (IN ORDER)

**1. Start Main Backend:**
```bash
# From: LeadGenAI/backend-database/backend/
cd ../../  # Go to main backend directory
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
python app.py
# Should show: "Running on http://127.0.0.1:8000"
```

**2. Start Ngrok (NEW TERMINAL):**
```bash
ngrok http 8000
# Copy the HTTPS URL: https://xxxxx.ngrok-free.app
```

**3. Update Environment Files:**
Update both `.env` and `frontend/.env.local` with your ngrok URL:
```env
NGROK_URL=https://your-actual-ngrok-url.ngrok-free.app
BASE_URL=https://your-actual-ngrok-url.ngrok-free.app
```

**4. Restart Backend:**
```bash
# In backend terminal, press Ctrl+C then:
python app.py
```

**5. Start Frontend (NEW TERMINAL):**
```bash
cd backend_robodialer/frontend
npm install
npm run dev
# Should show: "Ready on http://localhost:9002"
```

### Step 5: Configure Twilio Webhooks

1. Go to [Twilio Console](https://console.twilio.com/) → TwiML Apps
2. Find your TwiML App (from TWILIO_TWIML_APP_SID)
3. Set webhooks:
   - **Voice URL:** `https://your-ngrok-url.ngrok-free.app/api/twilio/voice`
   - **Status Callback:** `https://your-ngrok-url.ngrok-free.app/api/twilio/status`

## 🎯 Access Points

- **Frontend Dashboard:** http://localhost:9002
- **Backend API:** http://localhost:8000
- **Database Migration:** Auto-handled

## ✅ Verify Setup

**1. Backend Health Check:**
```bash
curl http://localhost:8000/api/v1/agents
# Should return JSON array of agents
```

**2. Frontend Access:**
- Go to http://localhost:9002
- Should see login page
- Login with any credentials (demo mode)

**3. Test Phone Call:**
- Upload CSV with test leads
- Click "Call" button
- Should initiate actual phone call

## 🔧 Key Features Working

### ✅ Core Functionality
- **Phone Calls:** Full Twilio integration with real calling
- **Call History:** Complete logs with timestamps and notes
- **Auto-Voicemail:** Sends voicemail when calls disconnect
- **Notes System:** Save and retrieve call notes
- **CSV Upload:** Import leads from CSV files
- **Agent Management:** Create and manage calling agents

### ✅ Database Features
- **Call Logs:** Full CRUD with lead_id support
- **Auto-Migration:** Database schema updates automatically
- **Notes Persistence:** Notes saved and retrieved properly
- **Lead Tracking:** Complete lead management system

## 🐛 Troubleshooting

### Problem: "Not valid" errors when calling
**Solution:** Ensure phone numbers are in E.164 format (+1234567890)

### Problem: Wrong numbers in call history
**Solution:** Database migration completed - this is fixed

### Problem: Can't save notes
**Solution:** PUT endpoint implemented - restart backend

### Problem: Twilio ConnectionError (31005)
**Solution:** Update ngrok URL in Twilio Console webhooks

### Problem: Frontend won't load
**Solution:** 
```bash
cd frontend
rm -rf .next node_modules
npm install
npm run dev
```

### Problem: Backend import errors
**Solution:** Run from correct directory: `LeadGenAI/backend-database/backend/`

## 📁 Project Structure

```
LeadGenAI/backend-database/backend/
├── app.py                          # 🚀 MAIN ENTRY POINT
├── requirements.txt                # Main backend dependencies
├── .env                           # Main backend environment
├── models/
│   ├── cold_call_agent_model.py   # Agent database model
│   └── cold_call_log_model.py     # Call log database model
└── services/backend_robodialer/   # RoboDialer service
    ├── .env                       # RoboDialer environment
    ├── requirements.txt           # RoboDialer dependencies
    ├── database/
    │   ├── app.py                # RoboDialer Flask blueprint
    │   └── main_db_bakend/
    │       ├── twilio_routes.py  # Twilio webhook handlers
    │       └── twilio_dialre.py  # Call logic
    └── frontend/                 # Next.js frontend
        ├── .env.local           # Frontend environment
        ├── package.json         # Frontend dependencies
        └── src/
            ├── app/page.tsx     # Main dashboard
            ├── contexts/call-context.tsx  # Call state management
            └── components/      # UI components
```

## 🔄 Important Notes

### Environment Files Hierarchy:
1. **Main Backend:** `backend-database/backend/.env` (database, core settings)
2. **RoboDialer Service:** `backend_robodialer/.env` (Twilio, AI services)
3. **Frontend:** `frontend/.env.local` (frontend-specific settings)

### Ngrok Important:
- **Restart ngrok = Update .env files + Restart backend**
- **Free plan:** URL changes every restart
- **Paid plan:** Get permanent domain

### Database:
- **Auto-migration:** Schema updates handled automatically
- **Railway:** Current production database
- **Local:** Can switch to local PostgreSQL if needed

## 🎉 Success Checklist

- [ ] Backend running on http://localhost:8000
- [ ] Frontend running on http://localhost:9002
- [ ] Ngrok tunnel active with HTTPS URL
- [ ] Environment files updated with ngrok URL
- [ ] Twilio webhooks configured
- [ ] Can login to frontend dashboard
- [ ] Can see agents list
- [ ] Can upload CSV and make test calls
- [ ] Call history shows correct numbers
- [ ] Notes can be saved and retrieved
- [ ] Auto-voicemail works on call disconnect

## 📞 Support

If you encounter issues:
1. Check all services are running (backend, frontend, ngrok)
2. Verify environment files have correct values
3. Ensure Twilio webhooks point to current ngrok URL
4. Check browser console for frontend errors
5. Check terminal logs for backend errors

---

**🎯 Ready to start making AI-powered calls with full automation!**