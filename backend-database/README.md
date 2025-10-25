# Phase 1 Implementation
### TODO:
## Environment Setup
- Choose Tech Stack
- Initialize Git repo
- CI/CD Skeleton
- Provision hosting
- Project Structures

## Lead Ingestion
- Create web form
- CSV parser & upload
- Field mapping
- Backend ingestion route

## Web Form & Database Feature

A new feature has been added to provide manual lead entry through a web form interface with database storage.

### Components:

1. **Web Form (Frontend just only for Testing)**
   - Simple form to collect lead information (name, email, phone, company)
   - HTML templates with CSS styling for clean UI
   - Form validation for required fields

2. **CSV Upload Feature**
   - Upload leads in bulk via CSV files
   - Field mapping for CSV columns
   - Data validation and cleaning
   - Duplicate detection
   - Support for all lead fields:
     - Basic contact info (name, email, phone)
     - Company details (name, website, industry)
     - Location (city, state)
     - Additional fields (title, business type, notes)

3. **Database Connection (Backend)**
   - PostgreSQL database for storing lead information
   - Flask-SQLAlchemy integration for ORM functionality
   - Data model for leads with appropriate fields

4. **Data Viewing**
   - Page to view all submitted leads in a table format
   - Quick verification of stored information
   - Edit and delete functionality

### File Structure:
```
/backend
  /models
    lead_model.py    # Database model for Lead
  /controllers
    lead_controller.py  # Business logic for lead operations
    upload_controller.py # CSV upload processing
  /routes
    lead_routes.py   # API routes for lead operations
  /templates
    form.html        # Form for submitting leads
    upload.html      # CSV upload interface
    leads.html       # View for displaying stored leads
  /config
    config.py        # Configuration settings
  app.py            # Main Flask application
```

### Data Flow:
1. User submits form with lead information or uploads CSV file
2. Backend validates and processes form data
3. Lead data is stored in PostgreSQL database
4. User can view all submitted leads

This feature complements the automated lead generation capabilities by allowing manual entry of leads from other sources.

## Testing Instructions

### Prerequisites
- Python 3.8 or higher
- PostgreSQL database
- pandas (for CSV processing)

### Database Setup
1. Create a PostgreSQL database named `lead_db`:
   ```
   createdb lead_db
   ```
2. Update the database connection string in `backend/config/config.py` if needed:
   ```python
   SQLALCHEMY_DATABASE_URI = 'postgresql://username@localhost:5432/lead_db'
   ```

### Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd LeadGen
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r backend/requirements.txt
   pip install pandas==1.3.3
   ```

### Running the Application
There are several ways to run the application:

1. Using Flask directly (recommended):
   ```
   # Set the Flask application
   # On Windows PowerShell:
   $env:FLASK_APP = "backend/app.py"
   
   # On Windows Command Prompt:
   set FLASK_APP=backend/app.py
   
   # On Linux/Mac:
   export FLASK_APP=backend/app.py
   
   # Run Flask
   flask run --port 8000
   ```

2. Using Python directly:
   ```
   # From the project root directory
   python backend/app.py
   ```

The application will be available at `http://localhost:8000`.

### Troubleshooting

#### Module Import Issues
If you encounter the error: `ImportError: attempted relative import with no known parent package`, this is typically due to Python's module resolution when using relative imports (imports starting with a dot `.`). Here are the solutions:

1. **Set PYTHONPATH** (Recommended for development):
   - The PYTHONPATH should point to your project root directory
   - This allows Python to correctly resolve relative imports
   ```
   # On Windows PowerShell:
   $env:PYTHONPATH = "."
   
   # On Windows Command Prompt:
   set PYTHONPATH=.
   
   # On Linux/Mac:
   export PYTHONPATH=.
   ```

2. **Use Python Module Syntax**:
   - Run the application as a module using the `-m` flag
   - This ensures proper package resolution
   ```
   python -m backend.app
   ```

#### Common Issues:
1. Make sure you're in the project root directory when running the application
2. Ensure your virtual environment is activated
3. Verify that all required packages are installed
4. Check that the database connection string is correct
5. Make sure PostgreSQL is running and accessible

For any other issues, please check the application logs or create an issue in the repository.

### CSV Upload Format
The CSV file should contain the following columns (column names can be mapped during upload):
- Name (required)
- Email (required)
- Phone (required)
- Company
- Website
- City
- State
- Title
- Industry
- Business Type
- Notes

# LeadGen API Documentation

This document provides an overview of all available API endpoints in the LeadGen system.

## Base URL
All API endpoints are prefixed with: `https://data.capraeleadseekers.site`

## Authentication

### Login
- **URL**: `https://data.capraeleadseekers.site/api/auth/login`
- **Method**: `POST`
- **Description**: Authenticate user and get access token
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "your_password"
  }
  ```
- **Success Response**:
  ```json
  {
    "message": "Login successful",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "name": "John Doe",
      "role": "admin"
    },
    "token": "jwt_token_here"
  }
  ```

### Register
- **URL**: `https://data.capraeleadseekers.site/api/auth/register`
- **Method**: `POST`
- **Description**: Create a new user account
- **Request Body**:
  ```json
  {
    "email": "newuser@example.com",
    "password": "your_password",
    "name": "New User",
    "role": "user"
  }
  ```
- **Success Response**:
  ```json
  {
    "message": "Registration successful",
    "user": {
      "id": 2,
      "email": "newuser@example.com",
      "name": "New User",
      "role": "user"
    },
    "token": "jwt_token_here"
  }
  ```

### Get Current User
- **URL**: `https://data.capraeleadseekers.site/api/auth/me`
- **Method**: `GET`
- **Description**: Get information about the currently logged in user
- **Headers**: Authorization with Bearer token
- **Success Response**:
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "role": "admin"
  }
  ```

### Logout
- **URL**: `https://data.capraeleadseekers.site/api/auth/logout`
- **Method**: `POST`
- **Description**: Logout the current user
- **Headers**: Authorization with Bearer token
- **Success Response**:
  ```json
  {
    "message": "Logout successful"
  }
  ```

## Leads

### Get All Leads
- **URL**: `https://data.capraeleadseekers.site/api/leads`
- **Method**: `GET`
- **Description**: Get a paginated list of all leads with optional filtering
- **Headers**: Authorization with Bearer token
- **Query Parameters**:
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 10)
  - `search`: Search term for company, owner name, or email
  - `company`: Filter by company name
  - `status`: Filter by status
  - `source`: Filter by source
- **Success Response**:
  ```json
  {
    "total": 100,
    "pages": 10,
    "current_page": 1,
    "per_page": 10,
    "leads": [
      {
        "lead_id": 1,
        "company": "Acme Inc",
        "owner_name": "John Doe",
        "owner_email": "john@acme.com",
        "status": "New",
        "created_at": "2023-06-15T10:30:00"
      },
      ...
    ]
  }
  ```

### Get Lead by ID
- **URL**: `https://data.capraeleadseekers.site/api/leads/{lead_id}`
- **Method**: `GET`
- **Description**: Get details of a specific lead
- **Headers**: Authorization with Bearer token
- **Success Response**:
  ```json
  {
    "lead_id": 1,
    "company": "Acme Inc",
    "owner_name": "John Doe",
    "owner_email": "john@acme.com",
    "phone": "123-456-7890",
    "website": "https://acme.com",
    "status": "New",
    "created_at": "2023-06-15T10:30:00",
    "source": "Website",
    "notes": "Interested in our products"
  }
  ```

### Create Lead
- **URL**: `https://data.capraeleadseekers.site/api/leads`
- **Method**: `POST`
- **Description**: Create a new lead (Admin and Developer only)
- **Headers**: Authorization with Bearer token
- **Request Body**:
  ```json
  {
    "company": "New Company",
    "owner_name": "Jane Smith",
    "owner_email": "jane@newcompany.com",
    "phone": "123-456-7890",
    "website": "https://newcompany.com",
    "status": "New",
    "source": "LinkedIn"
  }
  ```
- **Success Response**:
  ```json
  {
    "message": "Lead created successfully",
    "lead": {
      "lead_id": 5,
      "company": "New Company",
      "owner_name": "Jane Smith",
      "owner_email": "jane@newcompany.com",
      "status": "New"
    }
  }
  ```

### Update Lead
- **URL**: `https://data.capraeleadseekers.site/api/leads/{lead_id}`
- **Method**: `PUT`
- **Description**: Update lead details (Admin and Developer only)
- **Headers**: Authorization with Bearer token
- **Request Body**:
  ```json
  {
    "company": "Updated Company Name",
    "status": "Contacted",
    "notes": "Called on June 15th"
  }
  ```
- **Success Response**:
  ```json
  {
    "message": "Lead updated successfully",
    "lead": {
      "lead_id": 5,
      "company": "Updated Company Name",
      "owner_name": "Jane Smith",
      "owner_email": "jane@newcompany.com",
      "status": "Contacted",
      "notes": "Called on June 15th"
    }
  }
  ```

### Update Lead Status
- **URL**: `https://data.capraeleadseekers.site/api/leads/{lead_id}/status`
- **Method**: `PUT`
- **Description**: Update just the status of a lead (All roles)
- **Headers**: Authorization with Bearer token
- **Request Body**:
  ```json
  {
    "status": "Qualified"
  }
  ```
- **Success Response**:
  ```json
  {
    "message": "Status updated successfully",
    "lead": {
      "lead_id": 5,
      "company": "Updated Company Name",
      "status": "Qualified"
    }
  }
  ```

### Delete Lead
- **URL**: `https://data.capraeleadseekers.site/api/leads/{lead_id}`
- **Method**: `DELETE`
- **Description**: Soft delete a lead (Admin and Developer only)
- **Headers**: Authorization with Bearer token
- **Success Response**:
  ```json
  {
    "message": "Lead successfully deleted"
  }
  ```

### Upload Multiple Leads
- **URL**: `https://data.capraeleadseekers.site/api/upload_leads`
- **Method**: `POST`
- **Description**: Upload multiple leads at once
- **Headers**: Authorization with Bearer token
- **Request Body**:
  ```json
  [
    {
      "company": "Company A",
      "owner_email": "contact@companya.com",
      "phone": "123-456-7890",
      "source": "LinkedIn"
    },
    {
      "company": "Company B",
      "owner_email": "contact@companyb.com",
      "phone": "987-654-3210",
      "source": "Website"
    }
  ]
  ```
- **Success Response**:
  ```json
  {
    "status": "success",
    "message": "Upload Complete! Added: 2, Skipped: 0, Errors: 0",
    "stats": {
      "added": 2,
      "skipped_duplicates": 0,
      "errors": 0,
      "invalid_indices": []
    }
  }
  ```

## Sources

### Get All Sources
- **URL**: `https://data.capraeleadseekers.site/api/sources`
- **Method**: `GET`
- **Description**: Get a list of all available lead sources
- **Headers**: Authorization with Bearer token
- **Success Response**:
  ```json
  {
    "total": 5,
    "sources": [
      "Facebook",
      "Google",
      "LinkedIn",
      "Website",
      "Word of Mouth"
    ]
  }
  ```

### Add New Source
- **URL**: `https://data.capraeleadseekers.site/api/sources`
- **Method**: `POST`
- **Description**: Add a new lead source (Admin and Developer only)
- **Headers**: Authorization with Bearer token
- **Request Body**:
  ```json
  {
    "name": "Twitter"
  }
  ```
- **Success Response**:
  ```json
  {
    "message": "Source added successfully",
    "source": "Twitter"
  }
  ```

## Statistics

### Get Summary Statistics
- **URL**: `https://data.capraeleadseekers.site/api/stats/summary`
- **Method**: `GET`
- **Description**: Get lead count summary statistics
- **Headers**: Authorization with Bearer token
- **Query Parameters**:
  - `days`: Time period in days (default: 30)
- **Success Response**:
  ```json
  {
    "total_leads": 100,
    "by_date": {
      "2023-06-01": 5,
      "2023-06-02": 7,
      "2023-06-03": 3
    },
    "by_source": {
      "LinkedIn": 35,
      "Website": 25,
      "Google": 15,
      "Facebook": 15,
      "Word of Mouth": 10
    },
    "by_status": {
      "New": 30,
      "Contacted": 25,
      "Qualified": 20,
      "Proposal": 15,
      "Closed": 10
    }
  }
  ```

### Get Top Sources
- **URL**: `https://data.capraeleadseekers.site/api/stats/top-sources`
- **Method**: `GET`
- **Description**: Get top performing lead sources
- **Headers**: Authorization with Bearer token
- **Query Parameters**:
  - `days`: Time period in days (optional)
  - `limit`: Maximum number of sources to return (default: 5)
- **Success Response**:
  ```json
  {
    "top_sources": [
      {
        "source": "LinkedIn",
        "count": 35
      },
      {
        "source": "Website",
        "count": 25
      },
      {
        "source": "Google",
        "count": 15
      },
      {
        "source": "Facebook",
        "count": 15
      },
      {
        "source": "Word of Mouth",
        "count": 10
      }
    ]
  }
  ```

## Additional Endpoints

### Restore Lead
- **URL**: `https://data.capraeleadseekers.site/leads/{lead_id}/restore`
- **Method**: `POST`

### Restore Multiple Leads
- **URL**: `https://data.capraeleadseekers.site/leads/restore-multiple`
- **Method**: `POST`

### View Deleted Leads
- **URL**: `https://data.capraeleadseekers.site/leads/deleted`
- **Method**: `GET`

### Permanent Delete Lead
- **URL**: `https://data.capraeleadseekers.site/leads/{lead_id}/permanent-delete`
- **Method**: `POST`

### Delete Multiple Leads
- **URL**: `https://data.capraeleadseekers.site/leads/delete-multiple`
- **Method**: `POST`

### Export Leads
- **URL**: `https://data.capraeleadseekers.site/export_leads`
- **Method**: `POST`

### Upload CSV Leads
- **URL**: `https://data.capraeleadseekers.site/upload`
- **Method**: `POST`

### Submit Single Lead
- **URL**: `https://data.capraeleadseekers.site/submit`
- **Method**: `POST`

## Notes
1. All endpoints require authentication (`@login_required`)
2. Some endpoints require specific roles (`admin` or `developer`)
3. For API endpoints, include the Authorization header with Bearer token
4. The application is accessible at: `https://data.capraeleadseekers.site`
5. For HTML template endpoints, the response will be a web page
6. For API endpoints, the response will be in JSON format
7. All delete operations are soft deletes by default (except permanent delete)
8. File uploads (CSV) have format and data validation requirements
9. Export supports both CSV and Excel formats
10. Some endpoints support batch operations for efficiency
