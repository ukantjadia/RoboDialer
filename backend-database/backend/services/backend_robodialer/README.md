# 🤖 AI-Powered RoboDialer System - Enhanced with Enriched Leads

A complete AI-powered calling system with intelligent call handling, voicemail automation, real-time transcription, and comprehensive call logging. **NOW WITH ENRICHED LEADS INTEGRATION** for seamless calling of enriched leads from the main SaaSquatch Leads application.

## 🎯 NEW: Enriched Leads Integration

### ✨ What's New
- **Load Enriched Leads Button**: Directly load leads from your enriched leads database
- **Smart UI**: Only shows Call/Voicemail actions (Email hidden for enriched leads)  
- **Dual Mode Support**: Works standalone (demo) or integrated with main application
- **Automatic Phone Extraction**: Pulls phone numbers from enriched lead data
- **Seamless Integration**: Full compatibility with existing RoboDialer features

### 🚀 Quick Usage
1. Click **"Load Enriched Leads"** (above CSV upload option)
2. Select leads with phone numbers from the dialog
3. Start calling immediately - no CSV needed!

### 📚 Documentation
- **Complete Integration Guide**: See [ENRICHED_LEADS_INTEGRATION.md](./ENRICHED_LEADS_INTEGRATION.md)
- **API Endpoints**: `GET /api/v1/enriched_leads` and `GET /api/v1/enriched_leads/<draft_id>`
- **Test Data**: Run `python test_enriched_leads.py` for sample leads

## ⚡ Quick Start

**For testers and new users:** Follow the [**SETUP_GUIDE.md**](./SETUP_GUIDE.md) for detailed step-by-step instructions.

### Prerequisites
- Python 3.8+ and Node.js 16+
- Twilio account with verified phone number
- **Ngrok** (essential for webhooks)
- PostgreSQL database (Railway recommended)

### 5-Minute Setup
```bash
# 1. Clone and navigate
git clone [repo-url]
cd LeadGenAI/backend-database/backend/

# 2. Configure environment
cp services/backend_robodialer/.env.template services/backend_robodialer/.env
# Edit .env with your Twilio credentials

# 3. Start backend
python app.py

# 4. Start ngrok (new terminal)
ngrok http 8000
# Copy the https URL and update .env files

# 5. Restart backend, then start frontend
cd services/backend_robodialer/frontend/
npm install && npm run dev
```

**Access:** Frontend at http://localhost:9002, Backend at http://localhost:8000

## 🎯 Key Features

### ✅ Fully Working
- **Real Phone Calls** via Twilio integration
- **Call History & Notes** with database persistence  
- **Auto-Voicemail** when calls disconnect
- **CSV Lead Import** with proper phone validation
- **Agent Management** for multiple calling agents
- **Modern Next.js Dashboard** with login system

### 🔄 AI-Enhanced (Optional)
- **Intelligent Conversations** with DeepSeek LLM
- **Speech-to-Text** via Deepgram
- **Text-to-Speech** via Cartesia
- **Follow-up Emails** with AI-generated content

## 📁 Project Structure

```
LeadGenAI/backend-database/backend/
├── app.py                          # 🚀 MAIN ENTRY POINT
├── start_backend.bat/.sh           # Easy startup scripts
├── requirements.txt                # Backend dependencies
├── models/
│   ├── cold_call_agent_model.py   # Agent database model
│   └── cold_call_log_model.py     # Enhanced call logging
└── services/backend_robodialer/   # RoboDialer service
    ├── SETUP_GUIDE.md             # 📖 Detailed setup instructions
    ├── TESTING_CHECKLIST.md       # ✅ Complete testing guide
    ├── TROUBLESHOOTING.md          # 🔧 Common issues & fixes
    ├── .env.template               # Environment configuration
    ├── database/
    │   ├── app.py                 # RoboDialer Flask blueprint
    │   └── main_db_bakend/
    │       ├── twilio_routes.py   # Webhook handlers
    │       └── twilio_dialre.py   # Call logic
    └── frontend/                  # Next.js frontend
        ├── .env.template          # Frontend environment
        ├── start_frontend.bat     # Frontend startup script
        └── src/
            ├── app/page.tsx       # Main dashboard
            ├── contexts/call-context.tsx  # Call state
            └── components/        # UI components
```

## 🔧 Configuration

### Required Environment Variables
```env
# Twilio (Required)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY_SID=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret
TWILIO_TWIML_APP_SID=APxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_CALLER_ID=+1234567890

# Database (Required)
DATABASE_URL=postgresql://user:password@host:port/database

# Ngrok (Required for phone calls)
NGROK_URL=https://your-ngrok-url.ngrok-free.app
BASE_URL=https://your-ngrok-url.ngrok-free.app
```

### Optional AI Services
```env
DEEPSEEK_API_KEY=your_deepseek_key      # Conversational AI
DEEPGRAM_API_KEY=your_deepgram_key      # Speech-to-text
CARTESIA_API_KEY=your_cartesia_key      # Text-to-speech
GEMINI_API_KEY=your_gemini_key          # AI features
```

## 🚀 Recent Improvements

### ✅ Recently Fixed Issues
- **Phone number validation** - No more "not valid" errors
- **Call history accuracy** - Numbers display correctly
- **Notes persistence** - Full CRUD operations working
- **Auto-voicemail feature** - Triggers on call disconnect
- **Database migrations** - Schema properly updated
- **JavaScript errors** - Function ordering resolved

### 🏗️ Architecture Updates
- Enhanced CallLog model with lead_id support
- Improved frontend API integration
- Comprehensive error handling
- Auto-migration database scripts
- Modern Next.js 15 frontend structure

## 📋 Usage Workflow

1. **Setup & Start** services (backend → ngrok → frontend)
2. **Login** to dashboard at http://localhost:9002
3. **Create agents** for making calls
4. **Upload CSV** with lead phone numbers
5. **Make calls** through softphone interface
6. **Take notes** during and after calls
7. **Auto-voicemail** sent on disconnect
8. **Track results** in call history

## 🐛 Troubleshooting

**Common issues and quick fixes:**

- **Backend won't start:** Check you're in `backend-database/backend/` directory
- **No agents found:** Verify backend running on port 8000
- **Call failures:** Ensure ngrok active and Twilio webhooks configured
- **Notes not saving:** Restart backend to ensure PUT endpoint active

**See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed solutions.**

## 📋 Testing

**For comprehensive testing:** See [TESTING_CHECKLIST.md](./TESTING_CHECKLIST.md)

**Quick verification:**
```bash
# Backend health
curl http://localhost:8000/api/v1/agents

# Frontend access
# Visit: http://localhost:9002

# End-to-end test
# Upload CSV → Make call → Add notes → Verify in history
```

## 🔒 Production Notes

- **Never commit** real credentials in `.env` files
- **Use permanent webhooks** instead of ngrok for production
- **Implement proper authentication** for production deployment
- **Monitor Twilio usage** and costs
- **Rotate API keys** regularly

## 📞 Support & Documentation

- **Setup Issues:** [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- **Testing:** [TESTING_CHECKLIST.md](./TESTING_CHECKLIST.md)  
- **Troubleshooting:** [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- **Environment Config:** [.env.template](./.env.template)

## 🏆 Success Metrics

**The system is working correctly when:**
- ✅ Real phone calls connect successfully
- ✅ Call history shows accurate phone numbers and timestamps
- ✅ Notes save and persist across page refreshes
- ✅ Auto-voicemail triggers when calls disconnect
- ✅ CSV leads import and display properly
- ✅ No critical errors in browser console or backend logs

---

**🎯 Ready for production deployment with full AI-powered calling capabilities!**

A comprehensive AI-powered calling system with intelligent call handling, voicemail automation, and real-time transcription. Recently reorganized with improved frontend structure and enhanced routing.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL
- Twilio Account
- **Ngrok** (essential for webhook tunneling)

### 1. Install Ngrok (REQUIRED for full functionality)

**Windows (using winget):**
```bash
winget install ngrok.ngrok
# Restart terminal after installation
```

**Alternative (manual download):**
1. Download from https://ngrok.com/download
2. Extract to a folder in your PATH
3. Add to environment variables

**Mac/Linux:**
```bash
# Mac with Homebrew
brew install ngrok

# Linux
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

### 2. Setup Environment Variables

**Main Backend Environment (../../.env):**
The main backend `app.py` uses the `.env` file in the `backend-database/backend/` directory for database and core application settings.

**RoboDialer Service Environment (.env):**
```bash
cp .env.example .env
# Edit .env with your Twilio and AI service credentials
```

**Frontend Environment (.env.local):**
```bash
cd frontend
cp .env.example .env.local
# Edit .env.local with your ngrok URL and API keys
```

**Edit with your actual values** (see Configuration section below)

### 3. Start the System (IMPORTANT: Follow this order)

**Step 1 - Start Backend:**
```bash
cd LeadGenAI/backend-database/backend
# Activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Step 2 - Start Ngrok Tunnel (CRITICAL):**
```bash
# In a new terminal
ngrok http 8000
# Copy the HTTPS URL (e.g., https://abc123.ngrok-free.app)
```

**Step 3 - Update Environment Files:**
Update both `.env` and `frontend/.env.local` with your ngrok URL:
```env
BASE_URL=https://your-ngrok-url.ngrok-free.app
NGROK_URL=https://your-ngrok-url.ngrok-free.app
NEXT_PUBLIC_BASE_URL=https://your-ngrok-url.ngrok-free.app
```

**Step 4 - Restart Backend with new URLs:**
```bash
# Ctrl+C to stop, then restart
python app.py
```

**Step 5 - Start Frontend:**
```bash
cd backend_robodialer/frontend
npm install
npm run dev
```

### 4. Access the Application

- **Frontend Dashboard**: `http://localhost:9002`
- **Backend API**: `http://localhost:8000` (or your ngrok URL)
- **API Documentation**: `http://localhost:8000/docs`

## ⚠️ IMPORTANT: Ngrok Configuration

### Why Ngrok is Required
Twilio webhooks **cannot reach localhost**. Without ngrok:
- ❌ Phone calls will fail
- ❌ Voicemail won't work  
- ❌ Call transcription unavailable
- ❌ Real-time call status updates broken

### With Ngrok:
- ✅ Full phone calling functionality
- ✅ Twilio webhooks working
- ✅ Call recording and transcription
- ✅ Real-time call status updates
- ✅ Voicemail automation

## 🔧 Configuration

### Required API Keys and Credentials

**Twilio (Essential):**
```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_API_KEY_SID=your_api_key_sid
TWILIO_API_SECRET=your_api_secret
TWILIO_TWIML_APP_SID=your_twiml_app_sid
TWILIO_CALLER_ID=your_verified_phone_number
```

**Database:**
```env
DATABASE_URL=postgresql://user:password@host:port/database
```

**AI Services (Optional but recommended):**
```env
DEEPSEEK_API_KEY=your_deepseek_key
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key
GEMINI_API_KEY=your_gemini_key
```

**Ngrok URLs (Update after starting ngrok):**
```env
BASE_URL=https://your-ngrok-url.ngrok-free.app
NGROK_URL=https://your-ngrok-url.ngrok-free.app
NEXT_PUBLIC_BASE_URL=https://your-ngrok-url.ngrok-free.app
```

### Twilio TwiML App Configuration
In your Twilio Console, configure your TwiML App with:
- **Voice URL**: `https://your-ngrok-url.ngrok-free.app/api/twilio/voice`
- **Status Callback**: `https://your-ngrok-url.ngrok-free.app/api/twilio/call_status`

## 📋 Features Status

### ✅ Fully Working Features
- **Agent Management**: Create and manage calling agents
- **Call History**: Complete call logs with timestamps and notes
- **Frontend Dashboard**: Modern Next.js interface with login
- **API Communication**: All frontend↔backend routes functional
- **Token Generation**: Twilio access tokens for softphone
- **Call Logging**: Comprehensive call tracking and notes
- **Email Integration**: Post-call follow-up emails
- **CORS Configuration**: Proper cross-origin setup

### 🔄 Ngrok-Dependent Features
- **Live Phone Calls**: Requires ngrok for Twilio webhooks
- **Call Recording**: Needs public URL for Twilio callbacks
- **Voicemail**: Requires webhook accessibility
- **Real-time Status**: Depends on Twilio status callbacks

## 🏗️ Project Structure (Recently Reorganized)

```
LeadGenAI/
├── backend-database/backend/              # Main Flask backend application
│   ├── app.py                            # 🚀 MAIN ENTRY POINT - Run this file
│   ├── requirements.txt                  # Python dependencies
│   ├── .env                             # Main backend environment variables
│   ├── services/
│   │   └── backend_robodialer/          # RoboDialer service module
│   │       ├── database/                # RoboDialer backend logic
│   │       │   ├── app.py              # RoboDialer Flask blueprint
│   │       │   ├── db_init.py          # Database initialization  
│   │       │   └── main_db_bakend/     # Core RoboDialer services
│   │       │       ├── twilio_routes.py # Twilio webhook handlers
│   │       │       ├── twilio_dialre.py # Dialer engine logic
│   │       │       ├── email_backend.py # Email service
│   │       │       └── speech_to_text.py # Speech processing
│   │       ├── frontend/               # Next.js frontend (reorganized)
│   │       │   ├── src/
│   │       │   │   ├── app/           # App router and pages
│   │       │   │   │   ├── page.tsx   # Main dashboard
│   │       │   │   │   ├── login/     # Login page
│   │       │   │   │   └── api/       # API route proxies
│   │       │   │   ├── components/    # React components
│   │       │   │   │   ├── softphone.tsx # Main calling interface
│   │       │   │   │   ├── call-history-table.tsx
│   │       │   │   │   ├── post-call-sheet.tsx # Call notes form
│   │       │   │   │   └── ui/        # UI components
│   │       │   │   ├── contexts/      # React contexts for state
│   │       │   │   │   └── call-context.tsx # Main call state management
│   │       │   │   └── lib/           # Utilities and types
│   │       │   ├── .env.local         # Frontend environment
│   │       │   └── package.json       # Dependencies
│   │       ├── .env                   # RoboDialer service environment
│   │       ├── .env.example           # Environment template
│   │       ├── requirements.txt       # Python dependencies
│   │       ├── start.bat             # Windows startup script
│   │       ├── start.sh              # Unix startup script
│   │       └── README.md             # This file
│   ├── models/                       # Database models (shared)
│   ├── routes/                       # Other application routes
│   └── controllers/                  # Business logic controllers
```

### Key Architecture Points:
- **Main Backend**: `backend-database/backend/app.py` - This is what you run
- **RoboDialer Service**: Integrated as a Flask blueprint into the main app
- **Frontend**: Self-contained Next.js app within the RoboDialer service
- **Environment**: RoboDialer has its own `.env` but uses main backend database

## 🛠️ API Endpoints

### Working Endpoints
- `GET /api/v1/agents` - List all agents ✅
- `POST /api/v1/agents` - Create new agent ✅
- `GET /api/v1/get_call_logs` - Get call history ✅
- `POST /api/v1/call_logs` - Create call log ✅
- `GET /api/twilio/token` - Generate Twilio token ✅
- `POST /api/twilio/make_call` - Initiate call (needs ngrok) ⚠️
- `POST /api/twilio/send_voicemail` - Send voicemail (needs ngrok) ⚠️
- `POST /api/v1/send_email` - Send follow-up email ✅

### Frontend API Proxies
All frontend routes correctly proxy to backend:
- `GET /api/agents` → `GET /api/v1/agents`
- `GET /api/twilio/call_logs` → `GET /api/v1/get_call_logs`
- `POST /api/twilio/call_logs` → `POST /api/v1/call_logs`
- And more...

## 🚀 Recent Improvements

1. **Project Reorganization**: Moved from nested `RoboDialer/frontend/frontend_ui/` to clean `backend_robodialer/frontend/`
2. **Environment Configuration**: Fixed all environment variable paths and CORS settings
3. **API Route Mapping**: All frontend API routes correctly configured
4. **Documentation**: Comprehensive setup instructions with ngrok focus
5. **Error Resolution**: Fixed import paths and CORS configuration

## 🐛 Troubleshooting

### Ngrok Issues
```bash
# If ngrok command not found after installation
# Restart PowerShell/Terminal completely

# Check if ngrok is working
ngrok version

# Start tunnel
ngrok http 8000

# If tunnel dies, restart and update .env files
```

### Common Development Issues

**Backend won't start:**
- Make sure you're running `python app.py` from `backend-database/backend/` directory
- Check the main backend `.env` file has database configuration
- Verify all required Python packages are installed: `pip install -r requirements.txt`

**Frontend shows "no agents found":**
- Check if backend is running on port 8000: `curl http://localhost:8000/api/v1/agents`
- Verify NEXT_PUBLIC_BASE_URL in `frontend/.env.local` is correct
- Ensure main backend app.py is running (not just the RoboDialer service)

**Import errors in main app.py:**
- Check that RoboDialer blueprint import path is correct in main `app.py`
- Verify the path: `from services.backend_robodialer.database.app import robo_dailer_bp`
- Make sure all RoboDialer dependencies are installed

**Twilio call failures:**
- Ensure ngrok tunnel is active
- Update BASE_URL in backend .env
- Restart backend after URL changes
- Check Twilio TwiML App configuration

**CORS errors:**
- Verify localhost:9002 is in CORS origins
- Check environment variables are loaded
- Restart both frontend and backend

## 📞 Usage Workflow

1. **Start all services** (backend → ngrok → update env → restart → frontend)
2. **Access frontend** at `http://localhost:9002`
3. **Login** to the dashboard
4. **Manage agents** and view call history
5. **Make calls** through the softphone interface
6. **Take notes** during and after calls  
7. **Send follow-up emails** from call logs
8. **Monitor analytics** and call outcomes

## 🔒 Security & Production Notes

- **Never commit .env files** with real credentials
- **Ngrok URLs are temporary** - use permanent webhooks for production
- **Implement authentication** for production deployment
- **Use HTTPS** for all production webhook URLs
- **Rotate API keys** regularly

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. **Test with ngrok setup** to ensure webhooks work
4. Update documentation if needed
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

---

**🎯 Ready for production deployment with proper ngrok setup and comprehensive webhook functionality!**

## Features

### Core AI Calling System
- **AI-powered voice conversations** with investment leads
- **Real-time speech-to-text** using Deepgram for accurate transcription
- **Professional text-to-speech** using Cartesia for natural voice synthesis
- **Conversational AI** using DeepSeek for intelligent lead qualification
- **Professional voicemail delivery** with customizable scripts

### Lead Management Dashboard
- **Enhanced Streamlit dashboard** with professional UI/UX
- **Real-time lead management** with priority-based queue system
- **Auto-refresh functionality** (5-60 second intervals)
- **Call outcome logging** with detailed notes and status tracking
- **Lead status tracking**: New → Calling → Called/Connected/Interested/Dead
- **Priority-based lead selection** with star ratings
- **Quick lead addition** form for immediate entry

### API & Integration
- **RESTful API** for complete lead CRUD operations
- **WebSocket-based real-time communication** for live call updates
- **PostgreSQL database** with comprehensive lead and call history
- **Twilio integration** for professional telephony infrastructure

## Quick Start

### Prerequisites

- Docker and Docker Compose
- API keys for DeepSeek, Deepgram, Cartesia, and Twilio
- Python 3.11+ (for local development)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd RoboDialer
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys:
# - DEEPSEEK_API_KEY
# - DEEPGRAM_API_KEY  
# - CARTESIA_API_KEY
# - TWILIO_ACCOUNT_SID
# - TWILIO_AUTH_TOKEN
```

3. **Start the backend services**
```bash
docker-compose up --build -d
```

4. **Run database migrations**
```bash
# Run Alembic migrations to set up the database schema
docker exec -it robodialer-app-1 alembic upgrade head
```

5. **Launch the dashboard**
```bash
cd frontend
streamlit run enhanced_dashboard.py --server.port 8502
```

### Access Points

- **API Server**: `http://localhost:8080`
- **Dashboard**: `http://localhost:8501`
- **API Documentation**: `http://localhost:8080/docs`

### Health Check

```bash
curl http://localhost:8080/health
```

## Usage

### Dashboard Operations

1. **Start the Dashboard**
   - Navigate to `http://localhost:8501`
   - Select an active agent phone number
   - Enable auto-refresh for real-time updates

2. **Managing Leads**
   - Add leads via the "Quick Add Lead" form
   - Set priority levels (0-10) with star ratings
   - Filter leads by status: New, Calling, Called, etc.
   - View leads in the enhanced table with status emojis

3. **Making Calls**
   - Click "Start" to begin the dialer
   - System automatically selects next available lead
   - Click "Initiate Call" to start the conversation
   - Log call outcomes with professional voicemail scripts
   - Add detailed notes for each interaction

4. **Call History**
   - View all calls in the analytics table
   - Monitor AI confidence scores and lead status
   - Track conversation outcomes and patterns

### API Endpoints

#### Lead Management
- `GET /api/v1/leads` - List all leads
- `GET /api/v1/leads?status=New` - Filter leads by status
- `POST /api/v1/leads` - Create new lead
- `PUT /api/v1/leads/{id}/status` - Update lead status

#### Calling Operations
- `POST /api/v1/calls/initiate` - Start a call
- `GET /api/v1/conversations` - Get call history
- `GET /api/v1/agent-numbers` - List available agents

## Development

### Docker-Based Development (Recommended)

1. **Install dependencies for dashboard**
```bash
cd frontend && pip install -r requirements.txt
```

2. **Start all services with Docker**
```bash
docker-compose up --build -d
```

3. **Run database migrations**
```bash
docker exec -it robodialer-app-1 alembic upgrade head
```

4. **Run the dashboard**
```bash
cd frontend
streamlit run enhanced_dashboard.py --server.port 8502
```

5. **View logs (optional)**
```bash
# View backend logs
docker logs robodialer-app-1 -f

# View database logs  
docker logs robodialer-db-1 -f
```

### Local Development (Alternative)

1. **Install dependencies**
```bash
pip install -r requirements.txt
cd frontend && pip install -r requirements.txt
```

2. **Start database only**
```bash
docker-compose up db -d
```

3. **Run migrations locally**
```bash
alembic upgrade head
```

4. **Run the backend**
```bash
uvicorn core.server:app --reload --port 8080
```

5. **Run the dashboard**
```bash
cd frontend
streamlit run enhanced_dashboard.py --server.port 8501
```

### Testing

```bash
# Backend tests (run inside Docker container)
docker exec -it robodialer-app-1 pytest

# Test Twilio integration
docker exec -it robodialer-app-1 python tests/test_twilio_call.py

# Test API endpoints
curl -X POST "http://localhost:8080/api/v1/leads" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Lead", "phone_number": "+1234567890", "priority": 5}'

# Check database migration status
docker exec -it robodialer-app-1 alembic current
```

## Architecture

The CapraeCapital RoboDialer consists of:

### Backend Services
- **FastAPI Server** (Port 8080): RESTful API for lead management and call operations
- **PostgreSQL Database**: Persistent storage for leads, campaigns, and call history
- **Twilio Integration**: Professional telephony infrastructure for outbound calls

### AI Components
- **DeepSeek LLM**: Advanced conversational AI for intelligent lead qualification
- **Deepgram STT**: Real-time speech-to-text with high accuracy
- **Cartesia TTS**: Natural text-to-speech for professional voice synthesis

### Frontend Dashboard
- **Streamlit App** (Port 8502): Professional lead management interface
- **Auto-refresh**: Real-time updates every 5-60 seconds
- **Responsive Design**: Professional gradient UI with status indicators

### Data Flow
1. **Lead Management**: Dashboard → API → Database
2. **Call Initiation**: Dashboard → API → Twilio → AI Processing
3. **Voice Processing**: Twilio ↔ Deepgram STT ↔ DeepSeek ↔ Cartesia TTS
4. **Result Logging**: AI Analysis → Database → Dashboard Updates

## Configuration

### Environment Variables
```bash
# AI Services
DEEPSEEK_API_KEY=your_deepseek_key
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/robodialer

# Application
APP_ENV=development
LOG_LEVEL=INFO
```

### Professional Voicemail Scripts
The system includes three pre-configured voicemail scripts:
- **Professional**: Comprehensive investment opportunity message
- **Follow-Up**: Brief follow-up message for existing contacts
- **Brief**: Concise callback request

## Lead Status Workflow

```
New → Calling → [Connected|Called|Interested|Not_Interested|Dead]
  ↑                                    ↓
  └── (Can be reset) ←──────────────────┘
```

- **New**: Fresh lead ready for calling
- **Calling**: Currently being processed by dialer
- **Called**: Contact attempted (voicemail, busy, no answer)
- **Connected**: Successfully spoke with lead
- **Interested**: Lead expressed interest in investment opportunities
- **Not_Interested**: Lead declined interest
- **Dead**: Invalid/disconnected number

## Troubleshooting

### Common Issues

1. **"No leads available!" message**
   - Check if leads exist: `curl http://localhost:8080/api/v1/leads`
   - Reset stuck leads: Update any "Calling" status leads back to "New"
   - Verify database migrations: `docker exec -it robodialer-app-1 alembic current`

2. **Dashboard connection errors**
   - Verify backend is running: `docker ps` (should show robodialer-app-1)
   - Check API health: `curl http://localhost:8080/health`
   - View backend logs: `docker logs robodialer-app-1 -f`

3. **Database connection issues**
   - Ensure migrations are applied: `docker exec -it robodialer-app-1 alembic upgrade head`
   - Check database container: `docker logs robodialer-db-1 -f`
   - Restart services: `docker-compose restart`

4. **Twilio call failures**
   - Verify Twilio credentials in `.env`
   - Check agent phone number is verified in Twilio console
   - Ensure sufficient Twilio account balance
   - Test within container: `docker exec -it robodialer-app-1 python tests/test_twilio_call.py`

## License

This project is licensed under the MIT License.

---

**CapraeCapital RoboDialer** - Professional AI-Driven Investment Lead Generation Platform
*Powered by Twilio, Deepgram STT & DeepSeek LLM*
