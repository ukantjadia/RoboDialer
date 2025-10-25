# Enriched Leads Integration for RoboDialer

## Overview
This integration adds the ability to load enriched leads from the main SaaSquatch Leads application directly into the RoboDialer system for calling, without requiring email addresses. This allows users to call leads that have been enriched with company information and phone numbers.

## Features Added

### 🎯 **Core Functionality**
- **Load Enriched Leads Button**: Added above the CSV upload option in the RoboDialer interface
- **Automatic Phone Number Extraction**: Extracts phone numbers from JSONB `draft_data` field
- **Dual Mode Support**: Works both in standalone mode (demo) and integrated mode (with user authentication)
- **Conditional UI Elements**: Only shows Call and Voicemail actions (Email hidden since enriched leads don't contain email addresses)

### 🔧 **Backend API Endpoints**

#### 1. Get Enriched Leads (Paginated)
```
GET /api/v1/enriched_leads
```
**Parameters:**
- `limit` (optional): Number of leads per page (default: 100, max: 100)
- `offset` (optional): Pagination offset (default: 0)
- `status` (optional): Lead status filter (default: 'pending')
- `phase` (optional): Lead phase filter (default: 'approved')

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "lead_id": "test_lead_001",
      "draft_id": "uuid-here",
      "company": "Tech Innovators Inc",
      "phone_number": "+1-555-0123",
      "contact_name": "John Smith",
      "industry": "Software",
      "revenue": "$2M-5M",
      "city": "San Francisco",
      "state": "CA",
      "website": "https://techinnovators.com",
      "created_at": "2025-10-21T16:30:55.749212",
      "source": "enriched_data"
    }
  ],
  "total_count": 3,
  "count": 3,
  "has_more": false,
  "user_id": "973dfe46-3ec8-5785-f5f9-5af5ba3906ee",
  "mode": "integrated"
}
```

#### 2. Get Single Enriched Lead
```
GET /api/v1/enriched_leads/<draft_id>
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "lead_id": "test_lead_001",
    "draft_id": "uuid-here",
    "company": "Tech Innovators Inc",
    "phone_number": "+1-555-0123",
    "contact_name": "John Smith",
    "full_data": { /* complete draft_data JSONB */ },
    "mode": "integrated"
  }
}
```

### 🎨 **Frontend Changes**

#### 1. Updated ChoiceView Component
- Added "Load Enriched Leads" button above CSV upload
- Updated button hierarchy: Dial Number → Load Enriched Leads → Upload CSV File

#### 2. Enhanced Softphone Component
- Added `handleLoadEnrichedLeads()` function
- Proper error handling for authentication and network issues
- Data transformation to match existing Lead type interface
- Integration with existing leads dialog and calling functionality

#### 3. Leads Dialog Improvements
- Email button automatically disabled/hidden when no email available
- Proper handling of enriched vs CSV leads
- Maintained compatibility with existing call and voicemail functionality

## Integration with Main Application (SaaSquatch Leads)

### 🔄 **Authentication Flow**

#### Standalone Mode (Development/Demo)
- No authentication required
- Returns all enriched leads in database
- Indicated by `"mode": "standalone"` in API response
- Used for development and testing

#### Integrated Mode (Production)
- Requires Flask-Login session from main application
- Filters leads by authenticated user's `user_id`
- Indicated by `"mode": "integrated"` in API response
- Used when RoboDialer is embedded in main application

### 🗄️ **Database Integration**

#### Required Tables
- `user_lead_drafts`: Contains enriched lead data
- `users`: For user authentication (integrated mode)

#### Key Fields Used
- `user_lead_drafts.draft_data` (JSONB): Contains company info and phone numbers
- `user_lead_drafts.user_id`: For user-specific filtering
- `user_lead_drafts.status`: Lead status ('pending', 'in_progress', 'completed', 'archived')
- `user_lead_drafts.phase`: Lead phase ('draft', 'review', 'approved', 'rejected')
- `user_lead_drafts.is_deleted`: Soft delete flag

#### Phone Number Extraction
The system extracts phone numbers from the JSONB `draft_data` field in this priority order:
1. `companyPhone`
2. `phone`
3. `phone_number`

## Setup Instructions

### 🛠️ **Backend Setup**

1. **Install Dependencies** (already included in existing requirements)
   ```bash
   pip install flask flask-login sqlalchemy psycopg2
   ```

2. **Database Models**
   - Ensure `UserLeadDraft` model is imported and available
   - Verify database connection to main application database

3. **Environment Variables**
   ```bash
   # Database connection should point to main application DB
   DATABASE_URL=postgresql://user:pass@host:5432/saasquatch_leads_db
   ```

### 🌐 **Frontend Setup**

1. **Dependencies** (already included)
   - Next.js 15.3.3
   - Tailwind CSS
   - Lucide React icons

2. **API Configuration**
   ```typescript
   // Update API base URL if needed
   const API_BASE_URL = 'http://localhost:8001/api/v1';
   ```

### 🚀 **Deployment Modes**

#### Development (Standalone)
```bash
# Start RoboDialer backend
cd backend-database/backend
python app.py

# Start RoboDialer frontend
cd services/backend_robodialer/frontend
npm run dev
```

#### Production (Integrated)
1. Deploy RoboDialer as part of main application
2. Register RoboDialer blueprint in main Flask app
3. Ensure shared database connection
4. Configure authentication context

## Testing

### 🧪 **Test Data Creation**
Use the provided test script to create sample enriched leads:

```bash
cd backend-database/backend
python services/backend_robodialer/test_enriched_leads.py
```

This creates 3 sample companies with phone numbers for testing.

### 🔍 **API Testing**
```bash
# Test enriched leads endpoint
curl -X GET "http://localhost:8001/api/v1/enriched_leads"

# Expected response: 200 OK with leads data
```

### 🖱️ **Frontend Testing**
1. Open RoboDialer interface
2. Click "Load Enriched Leads" button
3. Verify leads appear in dialog
4. Confirm Call and Voicemail buttons are enabled
5. Verify Email button is disabled/hidden

## Configuration Options

### 🎛️ **Backend Configuration**
```python
# In app.py - customize query parameters
DEFAULT_STATUS = 'pending'      # Default lead status
DEFAULT_PHASE = 'approved'      # Default lead phase  
MAX_LEADS_PER_PAGE = 100       # Maximum pagination limit
```

### 🎨 **Frontend Configuration**
```typescript
// In softphone.tsx - customize API calls
const ENRICHED_LEADS_ENDPOINT = '/api/v1/enriched_leads';
const INCLUDE_CREDENTIALS = true;  // For cross-origin auth
```

## Troubleshooting

### 🚨 **Common Issues**

#### 1. "No Enriched Leads Found"
- **Cause**: No approved leads with phone numbers in database
- **Solution**: Create test data or check lead approval status

#### 2. "Authentication Required"
- **Cause**: Running in integrated mode without proper session
- **Solution**: Login to main application first, or use standalone mode

#### 3. "Failed to Fetch Enriched Leads"
- **Cause**: Backend not running or API endpoint not available
- **Solution**: Verify backend is running on correct port (8001)

#### 4. Email Button Still Showing
- **Cause**: Lead data contains email field
- **Solution**: Verify data transformation excludes email fields

### 📊 **Debug Information**
```javascript
// Check API response in browser console
console.log('API Response:', response);
console.log('Transformed Leads:', enrichedLeads);
console.log('Mode:', data.mode); // 'standalone' or 'integrated'
```

## Security Considerations

### 🔒 **User Data Protection**
- **Integrated Mode**: Only shows leads belonging to authenticated user
- **Standalone Mode**: Shows all leads (use only for development)
- **Phone Number Masking**: Consider masking phone numbers in UI if required
- **CORS Configuration**: Properly configured for main application domain

### 🛡️ **API Security**
- Input validation on all parameters
- Proper error handling without information disclosure
- Database query optimization to prevent performance issues
- Pagination limits to prevent resource exhaustion

## Performance Optimization

### ⚡ **Database Performance**
- Indexed queries on `user_id`, `status`, `phase`, `is_deleted`
- JSONB field indexing for phone number extraction
- Pagination to limit result sets

### 🚀 **Frontend Performance**
- Lazy loading of lead data
- Efficient state management with localStorage persistence
- Optimized re-renders with proper React patterns

## Maintenance

### 🔄 **Regular Tasks**
- Monitor API response times
- Check for orphaned draft records
- Update test data as needed
- Review error logs for issues

### 📈 **Monitoring Endpoints**
```bash
# Health check
GET /api/v1/enriched_leads?limit=1

# User-specific stats
GET /api/v1/enriched_leads?limit=0  # Returns count only
```

## Version History

### v1.0.0 (Current)
- ✅ Basic enriched leads loading
- ✅ Dual-mode authentication support
- ✅ Phone number extraction from JSONB
- ✅ Conditional UI elements
- ✅ Integration with existing calling functionality

### Future Enhancements
- 🔄 Real-time lead updates via WebSocket
- 📊 Lead calling analytics
- 🔍 Advanced filtering and search
- 📱 Mobile-responsive improvements
- 🎯 Lead scoring integration

---

## Support

For integration support or questions about this functionality:

1. **Technical Issues**: Check the troubleshooting section above
2. **Database Issues**: Verify connection to main application database
3. **Authentication Issues**: Ensure proper Flask-Login session context
4. **UI Issues**: Check browser console for JavaScript errors

**Author**: AI Assistant  
**Last Updated**: October 23, 2025  
**Version**: 1.0.0