# Backend Phase 2 API Documentation

## Overview

Backend Phase 2 is a comprehensive data enrichment and scraping service that provides APIs for:
- **Growjo Integration**: Company and person enrichment using Growjo's business intelligence platform
- **Apollo Integration**: Advanced company and person search/enrichment using Apollo's B2B database
- **Data Processing**: Intelligent data merging, cleaning, and business classification

## Service Architecture

- **Framework**: Flask-based REST API
- **Port**: 5050
- **Base URL**: `http://localhost:5050` (development)
- **Authentication**: API key-based (Apollo), Session-based (Growjo)
- **Data Sources**: Apollo.io, Growjo, OpenAI/DeepSeek for business classification

## API Endpoints

### Health Check

#### GET `/health`
**Description**: Service health status check  
**Response**: 
```json
{
  "status": "ok"
}
```

---

## Growjo Integration APIs

### 1. Initialize Growjo Session
**Endpoint**: `POST /enrich/init-growjo`  
**Description**: Authenticates with Growjo and obtains access token  
**Request Body**: None required  
**Response**:
```json
{
  "success": true,
  "message": "Growjo API initialized successfully",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "Authentication failed"
}
```

### 2. Check Growjo Session Status
**Endpoint**: `GET /enrich/is-growjo-init`  
**Description**: Verifies if current Growjo session is active  
**Request Body**: None  
**Response**:
```json
{
  "initialized": true,
  "message": "Growjo session is active",
  "token": "your_access_token_here"
}
```

**Alternative**: `POST /enrich/is-growjo-init`  
**Description**: Validates a specific token from frontend  
**Request Body**:
```json
{
  "token": "your_token_here"
}
```

### 3. Enrich Company via Growjo
**Endpoint**: `POST /enrich/growjo-enrich-company`  
**Description**: Enriches company information using Growjo API  
**Request Body**:
```json
{
  "company": "Company Name",
  "street": "123 Main St",
  "city": "New York",
  "state": "NY"
}
```

**Required Fields**: `company`  
**Optional Fields**: `street`, `city`, `state`

### 4. Enrich Person via Growjo
**Endpoint**: `POST /enrich/growjo-enrich-person`  
**Description**: Enriches person information using Growjo API  
**Request Body**:
```json
{
  "company": "Company Name",
  "person": "John Doe"
}
```

**Required Fields**: `company`, `person`

---

## Apollo Integration APIs

### 1. Find Best Person for Domain
**Endpoint**: `POST /enrich/find-best-person-single`  
**Description**: Identifies the most relevant person for a given company domain  
**Request Body**:
```json
{
  "domain": "company.com"
}
```

**Required Fields**: `domain`

### 2. Scrape All People for Domain
**Endpoint**: `POST /enrich/apollo-scrape-people`  
**Description**: Retrieves all people associated with a company domain  
**Request Body**:
```json
{
  "domain": "company.com"
}
```

**Required Fields**: `domain`  
**Response**:
```json
{
  "people": [
    {
      "id": "person_id",
      "name": "John Doe",
      "title": "CEO",
      "email": "john@company.com"
    }
  ]
}
```

### 3. Scrape Single Company
**Endpoint**: `POST /enrich/apollo-scrape-single`  
**Description**: Enriches a single company by domain  
**Request Body**:
```json
{
  "domain": "company.com"
}
```

**Required Fields**: `domain`  
**Response**: Company enrichment data including:
- Founded year
- LinkedIn URL
- Keywords
- Annual revenue
- Website URL
- Employee count
- Industry
- Business type (B2B/B2C/B2B2C)

### 4. Enrich Person (Advanced)
**Endpoint**: `POST /enrich/apollo-enrich-person`  
**Description**: Advanced person enrichment with flexible search parameters  
**Request Body** (any combination of fields):
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "name": "John Doe",
  "email": "john@company.com",
  "hashed_email": "hashed_email_value",
  "organization_name": "Company Inc",
  "domain": "company.com",
  "person_id": "apollo_person_id",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "reveal_personal_emails": false,
  "reveal_phone_number": false,
  "webhook_url": "https://your-webhook.com/callback"
}
```

**Search Methods**:
- **By Name**: `first_name`, `last_name`, or `name`
- **By Email**: `email` or `hashed_email`
- **By Organization**: `organization_name` or `domain`
- **By ID**: `person_id`
- **By LinkedIn**: `linkedin_url`

### 5. Enrich Company (Advanced Search)
**Endpoint**: `POST /enrich/apollo-enrich-company`  
**Description**: Advanced company search with comprehensive filtering options  
**Request Body** (any combination of fields):
```json
{
  "q_organization_name": "Company Name",
  "organization_num_employees_ranges": ["1,10", "250,500"],
  "organization_locations": ["texas", "california"],
  "organization_not_locations": ["minnesota"],
  "revenue_range_min": 1000000,
  "revenue_range_max": 10000000,
  "currently_using_any_of_technology_uids": ["salesforce", "google_analytics"],
  "q_organization_keyword_tags": ["mining", "consulting"],
  "organization_ids": ["apollo_org_id"],
  "latest_funding_amount_range_min": 1000000,
  "latest_funding_amount_range_max": 10000000,
  "total_funding_range_min": 5000000,
  "total_funding_range_max": 50000000,
  "latest_funding_date_range_min": "2020-01-01",
  "latest_funding_date_range_max": "2024-12-31",
  "q_organization_job_titles": ["Software Engineer"],
  "organization_job_locations": ["San Francisco"],
  "organization_num_jobs_range_min": 1,
  "organization_num_jobs_range_max": 100,
  "organization_job_posted_at_range_min": "2024-01-01",
  "organization_job_posted_at_range_max": "2024-12-31",
  "page": 1,
  "per_page": 10
}
```

**Search Categories**:
- **Basic Info**: Company name, keywords
- **Size & Scale**: Employee count, revenue ranges
- **Location**: Geographic filtering (include/exclude)
- **Technology**: Tech stack usage
- **Funding**: Investment amounts and dates
- **Jobs**: Hiring information and postings
- **Pagination**: Page number and results per page

---

## Data Processing Features

### Business Type Classification
The service automatically classifies companies into business types:
- **B2B**: Business-to-Business
- **B2C**: Business-to-Consumer  
- **B2B2C**: Business-to-Business-to-Consumer
- **N/A**: Unable to classify

Classification is performed using AI models (DeepSeek) analyzing company descriptions.

### Data Normalization
All API responses include normalized data:
- Empty/null values converted to "N/A"
- Consistent formatting across all endpoints
- Standardized response structures

---

## Usage Flow Examples

### 1. Company Research Workflow
```bash
# 1. Search for companies in specific industry
curl -X POST http://localhost:5050/enrich/apollo-enrich-company \
  -H "Content-Type: application/json" \
  -d '{
    "q_organization_name": "tech",
    "organization_locations": ["california"],
    "organization_num_employees_ranges": ["50,200"],
    "currently_using_any_of_technology_uids": ["salesforce"]
  }'

# 2. Enrich specific company
curl -X POST http://localhost:5050/enrich/apollo-scrape-single \
  -H "Content-Type: application/json" \
  -d '{"domain": "company.com"}'

# 3. Find key people
curl -X POST http://localhost:5050/enrich/apollo-scrape-people \
  -H "Content-Type: application/json" \
  -d '{"domain": "company.com"}'
```

### 2. Lead Generation Workflow
```bash
# 1. Initialize Growjo
curl -X POST http://localhost:5050/enrich/init-growjo

# 2. Enrich company leads
curl -X POST http://localhost:5050/enrich/growjo-enrich-company \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Target Company",
    "city": "San Francisco",
    "state": "CA"
  }'

# 3. Enrich person leads
curl -X POST http://localhost:5050/enrich/growjo-enrich-person \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Target Company",
    "person": "John Smith"
  }'
```

### 3. Person Research Workflow
```bash
# 1. Find person by email
curl -X POST http://localhost:5050/enrich/apollo-enrich-person \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@company.com",
    "reveal_personal_emails": true,
    "reveal_phone_number": true
  }'

# 2. Find person by LinkedIn
curl -X POST http://localhost:5050/enrich/apollo-enrich-person \
  -H "Content-Type: application/json" \
  -d '{
    "linkedin_url": "https://linkedin.com/in/johndoe"
  }'
```

---

## Error Handling

All endpoints return consistent error responses:
```json
{
  "error": "Error description"
}
```

**HTTP Status Codes**:
- `200`: Success
- `400`: Bad Request (missing required fields)
- `500`: Internal Server Error

---

## Environment Variables

Required environment variables:
```bash
# Apollo API
APOLLO_API_KEY=your_apollo_api_key

# Growjo Credentials
GROWJO_EMAIL=your_email@example.com
GROWJO_PASSWORD=your_password

# AI Classification (Optional)
DEEPSEEK_API_KEY=your_deepseek_api_key
```

---

## Deployment

### Docker
```bash
# Build image
docker build -t backend-phase2 .

# Run container
docker run -p 5050:5050 backend-phase2
```

### Local Development
```bash
cd backend_phase2/api
python app.py
```

---

## Rate Limits & Considerations

- **Apollo API**: Subject to Apollo's rate limiting policies
- **Growjo**: Session-based authentication with token expiration
- **AI Classification**: Limited by DeepSeek API quotas
- **Concurrent Requests**: Thread-safe implementation for multiple simultaneous requests

---

## Support & Documentation

- **Growjo Integration**: See `growjo_api_docs.md` for detailed Growjo-specific documentation
- **Testing**: Use provided test files (`test_*.py`) for endpoint validation
- **Logging**: Comprehensive logging for debugging and monitoring
