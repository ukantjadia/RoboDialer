# Growjo API Integration

This document describes the Growjo API integration for company and person enrichment.

## Setup

1. Add the following environment variables to your `.env` file:
```bash
GROWJO_EMAIL=your_email@example.com
GROWJO_PASSWORD=your_password
```

2. The `requests` library is already included in `requirements.txt`.

## API Endpoints

### 1. Initialize Growjo API
**Endpoint:** `POST /init-growjo`

Initializes the Growjo API by authenticating with the provided credentials and obtaining an access token.

**Request Body:** None required

**Response:**
```json
{
  "success": true,
  "message": "Growjo API initialized successfully",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL2FwaS5sZWFkNDExLmNvbS92MS9hdXRoZW50aWNhdGVfdXNlciIsImlhdCI6MTc1Mjk4MDI1MSwiZXhwIjoxNzUzMTUzMDUxLCJuYmYiOjE3NTI5ODAyNTEsImp0aSI6ImJpbjgzN3hXQ2lGZnZPMFMifQ.GSZf7g0m26Mik6SnBVxPj9Qoh0nVscMI9TkTUArA_JY"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message here"
}
```

### 2. Check Growjo Session Status
**Endpoint:** `GET /is-growjo-init`

Checks if the current Growjo session is still active by testing the token.

**Request Body:** None required

**Response:**
```json
{
  "initialized": true,
  "message": "Growjo session is active",
  "token": "your_access_token_here"
}
```

**Error Response:**
```json
{
  "initialized": false,
  "error": "Error message here"
}
```

### 3. Enrich Company (Existing)
**Endpoint:** `POST /growjo-enrich-company`

Enriches company information using Growjo API.

**Request Body:**
```json
{
  "company": "Company Name",
  "street": "123 Main St",
  "city": "New York",
  "state": "NY"
}
```

### 4. Enrich Person (Existing)
**Endpoint:** `POST /growjo-enrich-person`

Enriches person information using Growjo API.

**Request Body:**
```json
{
  "company": "Company Name",
  "person": "John Doe"
}
```

## Usage Flow

1. **Initialize the API:**
   ```bash
   curl -X POST http://localhost:5000/init-growjo
   ```

2. **Check session status:**
   ```bash
   curl -X GET http://localhost:5000/is-growjo-init
   ```

3. **Use enrichment endpoints:**
   ```bash
   curl -X POST http://localhost:5000/growjo-enrich-company \
     -H "Content-Type: application/json" \
     -d '{"company": "Example Corp", "city": "San Francisco", "state": "CA"}'
   ```

## Testing

Run the test script to verify the integration:

```bash
cd backend_phase2
python test_growjo_api.py
```

## Implementation Details

- The `GrowjoScraper` class manages authentication and token lifecycle
- Automatic token refresh when sessions expire
- Fallback responses when API data is unavailable
- Error handling for network issues and authentication failures

## API Response Format

The Growjo authentication API returns:
```json
{
  "status": "success",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

The implementation checks for `status: "success"` before extracting the token.

## Notes

- The current implementation includes fallback responses for when Growjo API data is not available
- Token management is handled automatically by the scraper class
- Session validation occurs before each API call to ensure fresh tokens
