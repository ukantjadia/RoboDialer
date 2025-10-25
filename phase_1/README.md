# Phase 1 Implementation
### TODO:
## Environment Setup
- Choose Tech Stack
- Initialize Git repo
- CI/CD Skeleton
- Provision hosting
- Project Structure

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

2. **Database Connection (Backend)**
   - PostgreSQL database for storing lead information
   - Flask-SQLAlchemy integration for ORM functionality
   - Data model for leads with appropriate fields

3. **Data Viewing**
   - Page to view all submitted leads in a table format
   - Quick verification of stored information

### File Structure:
```
/backend
  /models
    lead_model.py    # Database model for Lead
  /templates
    form.html        # Form for submitting leads
    leads.html       # View for displaying stored leads
  input_form.py             # Flask application with routes and database config
```

### Data Flow:
1. User submits form with lead information
2. Backend validates and processes form data
3. Lead data is stored in PostgreSQL database
4. User can view all submitted leads

This feature complements the automated lead generation capabilities by allowing manual entry of leads from other sources.

## Testing Instructions

### Prerequisites
- Python 3.8 or higher
- PostgreSQL database

### Database Setup
1. Create a PostgreSQL database named `lead_db`:
   ```
   createdb lead_db
   ```
2. Update the database connection string in `phase_1/backend/input_form.py` if needed:
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username@localhost:5432/lead_db'
   ```

### Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd LeadGenAI
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

### Running the Application
1. Navigate to the backend directory:
   ```
   cd phase_1/backend
   ```

2. Run the Flask application:
   ```
   python input_form.py
   ```

3. Access the application:
   - Web form: http://localhost:5000/
   - View leads: http://localhost:5000/view_leads

### Testing Features
1. **Adding Leads**:
   - Fill out the form at the home page with lead information
   - Submit the form to add the lead to the database
   - You should be redirected back to the form with a success message

2. **Viewing Leads**:
   - Navigate to http://localhost:5000/view_leads
   - All submitted leads will be displayed in a table
   - Use the search box to filter leads

3. **Editing Leads**:
   - From the leads view page, click the "Edit" button on any lead
   - Update the information and click "Update Lead"
   - You will be redirected back to the leads view with a success message

4. **Deleting Leads**:
   - From the leads view page, click the "Delete" button on any lead
   - Confirm the deletion
   - The lead will be removed from the database
