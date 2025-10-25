# LeadGenAI
This project will be conducted over 3 main phases.

## Robodialer Feature Setup

### Prerequisites
- Python 3.x installed
- Node.js and npm installed
- Git installed

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Caprae-Capital-Partners/LeadGenAI.git
   cd LeadGenAI
   ```

2. **Switch to the Robodialer Branch**
   ```bash
   git checkout sandbox-database-robodialer
   git pull
   ```

3. **Set Up Python Virtual Environment**
   
   Navigate to the backend directory and create a virtual environment:
   ```bash
   cd backend-database/backend
   python -m venv venv
   ```

4. **Activate Virtual Environment**
   
   On Windows:
   ```bash
   venv\Scripts\activate
   ```
   
   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

5. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

6. **Configure Environment Variables**
   
   Set up the `.env` files in the appropriate directories before proceeding.

### Running the Application

You'll need **two separate terminals** for running the backend and frontend simultaneously.

#### Terminal 1: Backend Server

1. Navigate to the backend directory:
   ```bash
   cd backend-database/backend
   ```

2. Activate the virtual environment (if not already activated):
   ```bash
   venv\Scripts\activate
   ```

3. Run the backend server:
   ```bash
   python app.py
   ```

#### Terminal 2: Frontend Server

1. Navigate to the robodialer frontend directory:
   ```bash
   cd backend-database/backend/services/backend_robodialer/frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

### Accessing the Application

Once both servers are running, you can access the robodialer frontend through your browser at the URL provided by the npm development server (typically `http://localhost:3000` or similar).

---

## Robodialer API Endpoints Documentation

Base URL: `http://localhost:8000` (or your configured backend server)

### Authentication
Most endpoints require authentication. Ensure you include appropriate session cookies or authentication headers in your requests.

---

## Lead Management Endpoints

### Get All Leads
```http
GET /api/v1/leads
```

**Query Parameters:**
- `limit` (integer, optional): Maximum number of leads to return (default: 100)

**Response:**
```json
{
  "status": "success",
  "total": 100,
  "leads": [
    {
      "lead_id": "uuid",
      "company": "Company Name",
      "website": "https://example.com",
      "owner_email": "contact@example.com",
      "owner_phone_number": "+1234567890",
      "status": "new",
      ...
    }
  ]
}
```

**Status Codes:**
- `200`: Success
- `500`: Internal Server Error

---

### Get Single Lead
```http
GET /api/v1/leads/<lead_id>
```

**Path Parameters:**
- `lead_id` (string, required): Unique identifier of the lead

**Response:**
```json
{
  "status": "success",
  "lead": {
    "lead_id": "uuid",
    "company": "Company Name",
    "owner_first_name": "John",
    "owner_last_name": "Doe",
    "owner_email": "john@example.com",
    "owner_phone_number": "+1234567890",
    ...
  }
}
```

**Status Codes:**
- `200`: Success
- `404`: Lead not found

---

## Agent Management Endpoints

### Create Agent
```http
POST /api/v1/agents
```

**Request Body:**
```json
{
  "name": "Agent Name",
  "email": "agent@example.com",
  "phone": "+1234567890",
  "status": "active",
  "is_available": true,
  "total_calls": 0
}
```

**Required Fields:**
- `name` (string)
- `email` (string)
- `phone` (string)

**Optional Fields:**
- `status` (string, default: "active")
- `is_available` (boolean, default: true)
- `total_calls` (integer, default: 0)

**Response:**
```json
{
  "status": "success",
  "message": "Agent added.",
  "agent_id": 1
}
```

**Status Codes:**
- `201`: Agent created successfully
- `400`: Missing required fields
- `409`: Agent with email already exists
- `500`: Internal Server Error

---

### Get All Agents
```http
GET /api/v1/agents
```

**Response:**
```json
{
  "status": "success",
  "total": 5,
  "agents": [
    {
      "id": 1,
      "name": "Agent Name",
      "email": "agent@example.com",
      "phone": "+1234567890",
      "status": "active",
      "is_available": true,
      "total_calls": 150,
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-10-21T14:20:00"
    }
  ]
}
```

**Status Codes:**
- `200`: Success
- `500`: Internal Server Error

---

## Call Log Endpoints

### Create Call Log
```http
POST /api/v1/call_logs
```

**Request Body:**
```json
{
  "agent_id": 1,
  "lead_id": "uuid-optional",
  "phone_number": "+1234567890",
  "direction": "outgoing",
  "status": "completed",
  "action_taken": "call",
  "contact_name": "John Doe",
  "started_at": "2025-10-21T14:30:00Z",
  "ended_at": "2025-10-21T14:35:00Z",
  "duration": 300,
  "notes": "Discussed product features",
  "summary": "Positive conversation, interested in demo",
  "follow_up_required": true,
  "call_attempt_number": 1
}
```

**Required Fields:**
- `agent_id` (integer): ID of the agent making the call
- `phone_number` (string): Phone number called

**Optional Fields:**
- `lead_id` (string): Associated lead UUID
- `direction` (string, default: "outgoing"): "outgoing" or "incoming"
- `status` (string, default: "completed"): Call status
- `action_taken` (string, default: "call"): Action performed
- `contact_name` (string): Name of person contacted
- `started_at` (ISO 8601 timestamp): Call start time
- `ended_at` (ISO 8601 timestamp): Call end time
- `duration` (integer): Duration in seconds (auto-calculated if not provided)
- `notes` (string): Call notes
- `summary` (string): Call summary (merged with notes)
- `follow_up_required` (boolean, default: false)
- `call_attempt_number` (integer, default: 1)

**Response:**
```json
{
  "status": "success",
  "message": "Call log added.",
  "call_log": {
    "id": 123,
    "agent_id": 1,
    "phone_number": "+1234567890",
    "status": "completed",
    "duration": 300,
    ...
  }
}
```

**Status Codes:**
- `201`: Call log created successfully
- `200`: Call log already exists (idempotency)
- `400`: Missing required fields or invalid data
- `404`: Agent not found
- `500`: Internal Server Error

**Note:** The endpoint implements idempotency - duplicate call logs within a 10-second window are prevented.

---

### Get Call Logs
```http
GET /api/v1/get_call_logs
```

**Query Parameters:**
- `agent_id` (integer, optional): Filter by agent ID

**Response:**
```json
{
  "status": "success",
  "count": 50,
  "call_logs": [
    {
      "id": 123,
      "agent_id": 1,
      "lead_id": "uuid",
      "phone_number": "+1234567890",
      "direction": "outgoing",
      "status": "completed",
      "action_taken": "call",
      "contact_name": "John Doe",
      "started_at": "2025-10-21T14:30:00",
      "ended_at": "2025-10-21T14:35:00",
      "duration": 300,
      "notes": "Call notes",
      "follow_up_required": true,
      "created_at": "2025-10-21T14:35:05"
    }
  ]
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid agent_id
- `500`: Internal Server Error

---

### Update Call Log
```http
PUT /api/v1/call_logs/<call_log_id>
PATCH /api/v1/call_logs/<call_log_id>
```

**Path Parameters:**
- `call_log_id` (integer, required): ID of the call log to update

**Request Body:**
```json
{
  "notes": "Updated notes",
  "summary": "Call summary",
  "status": "completed",
  "action_taken": "voicemail",
  "contact_name": "John Doe",
  "follow_up_required": true,
  "follow_up_date": "2025-10-25T10:00:00Z"
}
```

**All fields are optional** - only provided fields will be updated.

**Response:**
```json
{
  "status": "success",
  "message": "Call log updated.",
  "call_log": {
    "id": 123,
    "notes": "Updated notes",
    "updated_at": "2025-10-21T15:00:00",
    ...
  }
}
```

**Status Codes:**
- `200`: Successfully updated
- `404`: Call log not found
- `500`: Internal Server Error

---

## Twilio Integration Endpoints

### Get Twilio Token
```http
GET /api/twilio/token
```

**Description:** Generates a Twilio access token for agent softphone connection.

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "identity": "agent_1_client_id"
}
```

**Status Codes:**
- `200`: Success
- `500`: Token generation failed

---

### Make Call
```http
POST /api/twilio/make_call
```

**Request Body:**
```json
{
  "agent_id": "1",
  "to": "+1234567890",
  "dialer_type": "manual",
  "lead_id": "uuid-optional"
}
```

**Required Fields:**
- `agent_id` (string): ID of the calling agent
- `to` (string): Customer phone number to dial
- `dialer_type` (string): "manual" or "auto"

**Optional Fields:**
- `lead_id` (string): Required when `dialer_type` is "auto"

**Response:**
```json
{
  "status": "success",
  "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "message": "Call initiated"
}
```

**Status Codes:**
- `200`: Call initiated successfully
- `400`: Missing or invalid required fields
- `500`: Call failed

---

### Send Voicemail
```http
POST /api/twilio/send_voicemail
```

**Request Body:**
```json
{
  "phone": "+1234567890",
  "script": "Hi, this is a voicemail message...",
  "agent_id": 1
}
```

**Required Fields:**
- `phone` (string): Recipient phone number
- `script` (string): Voicemail message text (will be converted to speech)

**Optional Fields:**
- `agent_id` (integer, default: 1): Agent sending the voicemail

**Response:**
```json
{
  "status": "success",
  "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "message": "Voicemail sent successfully",
  "call_log": {
    "id": 124,
    "phone_number": "+1234567890",
    "action_taken": "voicemail",
    ...
  }
}
```

**Status Codes:**
- `200`: Voicemail sent successfully
- `400`: Missing required fields
- `500`: Failed to send voicemail

**Note:** Automatically creates a call log entry when voicemail is sent.

---

### Get Call Transcript
```http
GET /api/twilio/get_transcript/<call_sid>
```

**Path Parameters:**
- `call_sid` (string, required): Twilio Call SID

**Description:** Retrieves call recordings and generates transcripts using speech-to-text.

**Response:**
```json
{
  "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "recordings": [
    {
      "recording_sid": "RExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "url": "https://api.twilio.com/...",
      "transcript": "Transcribed text from the call recording"
    }
  ]
}
```

**Status Codes:**
- `200`: Success
- `404`: No recordings found
- `503`: Transcription service unavailable

---

### Voice Webhook (TwiML)
```http
POST /api/twilio/voice
GET /api/twilio/voice
```

**Description:** Twilio webhook for generating voice TwiML responses.

**Query Parameters:**
- `To` (string): Destination number or room

**Response:** XML (TwiML)

---

### Join Conference Webhook
```http
POST /api/twilio/join
GET /api/twilio/join
```

**Description:** Connects customer to conference room.

**Query Parameters:**
- `Room` (string, required): Conference room name

**Response:** XML (TwiML)

---

### Call Status Webhook
```http
POST /api/twilio/call_status
```

**Description:** Twilio callback for call status updates (answered, completed, failed, etc.).

**Form Parameters:**
- `CallSid` (string): Twilio Call SID
- `CallStatus` (string): Current call status
- `Direction` (string): Call direction

**Response:**
```
200 OK
```

---

### Incoming Call Handler
```http
POST /api/twilio/incoming_call
```

**Description:** Handles incoming calls by routing to available agents.

**Form Parameters:**
- `CallSid` (string): Twilio Call SID

**Response:** XML (TwiML)

---

### Get Agent Status
```http
GET /api/twilio/private/agent_status/<agent_id>
```

**Path Parameters:**
- `agent_id` (string, required): Agent identifier

**Headers:**
- `X-Private-Key` (string, required): Private API key for authentication

**Response:**
```json
{
  "agent_id": "1",
  "status": "available",
  "current_calls": 0
}
```

**Status Codes:**
- `200`: Success
- `403`: Unauthorized (invalid private key)

---

### Serve Voicemail File
```http
GET /api/twilio/voicemails/<filename>
```

**Path Parameters:**
- `filename` (string, required): Voicemail audio file name

**Description:** Serves the locally saved voicemail audio file to Twilio.

**Response:** Audio file (WAV format)

**Status Codes:**
- `200`: Success
- `404`: File not found
- `500`: Internal Server Error

---

## Email Integration

### Send Missed Call Email
```http
POST /api/v1/send_email
```

**Request Body:**
```json
{
  "name": "Lead Name",
  "email": "lead@example.com"
}
```

**Required Fields:**
- `name` (string): Recipient's name
- `email` (string): Recipient's email address

**Response:**
```json
{
  "status": "success",
  "message": "Missed call email sent to lead@example.com"
}
```

**Status Codes:**
- `200`: Email sent successfully
- `400`: Missing required fields
- `500`: Email sending failed

---

## Health Check

### Service Health
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "robodialer"
}
```

**Status Codes:**
- `200`: Service is healthy

---

## Error Responses

All API endpoints return errors in the following format:

```json
{
  "status": "error",
  "message": "Descriptive error message"
}
```

### Common HTTP Status Codes
- `200`: Success
- `201`: Resource created
- `400`: Bad request (missing/invalid parameters)
- `403`: Forbidden (unauthorized access)
- `404`: Resource not found
- `409`: Conflict (duplicate resource)
- `500`: Internal server error
- `503`: Service unavailable

---

## Data Models

### Lead Object
```json
{
  "lead_id": "uuid",
  "company_id": "string",
  "company": "string",
  "website": "string",
  "industry": "string",
  "product_category": "string",
  "business_type": "string",
  "employees": "string",
  "revenue": "number",
  "year_founded": "integer",
  "street": "string",
  "city": "string",
  "state": "string",
  "country": "string",
  "owner_first_name": "string",
  "owner_last_name": "string",
  "owner_title": "string",
  "owner_email": "string",
  "owner_phone_number": "string",
  "owner_linkedin": "string",
  "company_phone": "string",
  "company_linkedin": "string",
  "source": "string",
  "status": "string",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### Agent Object
```json
{
  "id": "integer",
  "name": "string",
  "email": "string",
  "phone": "string",
  "status": "string",
  "is_available": "boolean",
  "total_calls": "integer",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### Call Log Object
```json
{
  "id": "integer",
  "agent_id": "integer",
  "lead_id": "string",
  "phone_number": "string",
  "direction": "string",
  "status": "string",
  "action_taken": "string",
  "contact_name": "string",
  "started_at": "timestamp",
  "ended_at": "timestamp",
  "duration": "integer",
  "notes": "string",
  "follow_up_required": "boolean",
  "follow_up_date": "timestamp",
  "call_attempt_number": "integer",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

---

## Notes

- **Timestamps:** All timestamps should be in ISO 8601 format (e.g., `2025-10-21T14:30:00Z`)
- **Phone Numbers:** Use E.164 format (e.g., `+1234567890`)
- **Idempotency:** Call log creation prevents duplicates within a 10-second window
- **CORS:** The API supports CORS for origins: `http://localhost:9002`, `http://localhost:3000`, `http://localhost:5173`
- **Database:** Uses PostgreSQL with SQLAlchemy ORM
