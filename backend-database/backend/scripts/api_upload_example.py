import requests
import json

# Replace with your actual server URL and authentication details
BASE_URL = "http://127.0.0.1:8000"  # Change to your actual server URL
API_ENDPOINT = f"{BASE_URL}/api/upload_leads"

# Sample data for lead upload - format must match database fields
sample_leads = [
    {
        "owner_first_name": "John",
        "owner_last_name": "Doe",
        "owner_email": "Doe.doe@example.com",
        "owner_phone_number": "9804892245",
        "phone": "9804899245",
        "company": "ABC Corp",
        "company_phone": "9804892245",
        "company_linkedin": "https://www.linkedin.com/in/john-doe",
        "owner_title": "CEO",
        "industry": "Technology",
        "website": "https://www.example.com",
        "city": "New York",
        "state": "NY",
        "source": "Ghaly"
    },
    {
        "owner_first_name": "Jane",
        "owner_last_name": "Smith",
        "owner_email": "Smith.smith@example.com", 
        "owner_phone_number": "9804892345",
        "company": "XYZ Inc",
        "company_phone": "9804892345",
        "company_linkedin": "https://www.linkedin.com/in/jane-smith",
        "owner_title": "CTO",
        "industry": "Finance",
        "website": "https://www.xyz.com",
        "city": "San Francisco",
        "state": "CA",
        "source": "Ghaly"
    }
]

def login_and_get_session_cookie(email, password):
    """
    Login to the system and get session cookie
    
    Args:
        email: Email for login
        password: Password for login
    
    Returns:
        Session cookie if login successful, None otherwise
    """
    login_url = f"{BASE_URL}/api/auth/login"
    
    session = requests.Session()
    login_data = {
        "email": email,
        "password": password
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"Attempting to login at: {login_url}")
        print(f"With credentials: email={email}")
        response = session.post(login_url, json=login_data, headers=headers)
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response content: {response.text}")
        
        if response.status_code == 200:
            cookies = session.cookies.get_dict()
            print(f"Got cookies: {cookies}")
            return cookies
        else:
            print(f"Login failed with status code: {response.status_code}")
            print(f"Response content: {response.text}")
            return None
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        print("Make sure the Flask server is running at", BASE_URL)
        return None
    except Exception as e:
        print(f"Unexpected error during login: {e}")
        return None

def upload_leads(leads_data, session_cookie=None):
    """
    Upload leads to the system via API
    
    Args:
        leads_data: List of lead dictionaries
        session_cookie: Session cookie for authentication
    
    Returns:
        Response from the API
    """
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Make the request to the API with session cookie
    if session_cookie:
        cookies = session_cookie
    else:
        cookies = {}
    
    response = requests.post(
        API_ENDPOINT,
        headers=headers,
        json=leads_data,
        cookies=cookies
    )
    
    return response

if __name__ == "__main__":
    # Replace with your actual credentials
    email = "developer@example.com"  # Changed to email
    password = "developer123"  # Update with your actual password
    
    print(f"Using server URL: {BASE_URL}")
    print("Attempting to login and get session cookie...")
    session_cookie = login_and_get_session_cookie(email, password)
    
    if session_cookie:
        print(f"Login successful, got session cookie: {session_cookie}")
        # Upload leads with the session cookie
        print("Uploading leads with session cookie...")
        response = upload_leads(sample_leads, session_cookie)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Text: {response.text}")
        
        # Try to parse JSON if possible
        try:
            json_response = response.json()
            print(f"JSON Response: {json_response}")
        except Exception as e:
            print(f"Could not parse JSON: {e}")
    else:
        print("Login failed, could not get session cookie")
    
    # Option 2: Using session cookie directly (if you have it)
    # Uncomment and update this if you want to try with a manual cookie
    """
    print("\nTrying with manual session cookie...")
    manual_session_cookie = {"session": "eyJfZnJlc2giOmZhbHNlfQ.aBYgkA.JJzpcxBl4qxKsjfXDSXURI2Yre8"}
    
    # Upload leads with manual session cookie
    response = upload_leads(sample_leads, manual_session_cookie)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    print(f"Response Text: {response.text}")
    
    # Try to parse JSON if possible
    try:
        json_response = response.json()
        print(f"JSON Response: {json_response}")
    except Exception as e:
        print(f"Could not parse JSON: {e}")
    """
    
    # The API will return a JSON response with the status and stats:
    # {
    #   "status": "success",
    #   "message": "Upload Complete! Added: 2, Skipped: 0, Errors: 0",
    #   "stats": {
    #     "added": 2,
    #     "skipped_duplicates": 0,
    #     "errors": 0
    #   }
    # } 