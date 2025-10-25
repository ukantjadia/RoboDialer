import requests
import json
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
# Get the directory where this file is located and look for .env there
import pathlib
current_dir = pathlib.Path(__file__).parent.parent
env_path = current_dir / '.env'
load_dotenv(env_path)

# --- Configuration & Mappings ---

STATE_MAP = {
    "AB": "Alberta", "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "AS": "American Samoa",
    "AZ": "Arizona", "BC": "British Columbia", "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DC": "Washington D.C.", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "GU": "Guam",
    "HI": "Hawaii", "IA": "Iowa", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "MA": "Massachusetts", "MB": "Manitoba", "MD": "Maryland",
    "ME": "Maine", "MI": "Michigan", "MN": "Minnesota", "MO": "Missouri", "MP": "Northern Mariana Islands",
    "MS": "Mississippi", "MT": "Montana", "NB": "New Brunswick", "NC": "North Carolina", "ND": "North Dakota",
    "NE": "Nebraska", "NH": "New Hampshire", "NJ": "New Jersey", "NL": "Newfoundland and Labrador",
    "NM": "New Mexico", "NS": "Nouvelle-Écosse", "NT": "Northwest Territories", "NU": "Nunavut",
    "NV": "Nevada", "NY": "New York", "OH": "Ohio", "OK": "Oklahoma", "ON": "Ontario", "OR": "Oregon",
    "PA": "Pennsylvania", "PE": "Prince Edward Island", "PR": "Puerto Rico", "PW": "Palau", "QC": "Quebec",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "SK": "Saskatchewan",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VA": "Virginia", "VI": "Virgin Islands",
    "VT": "Vermont", "WA": "Washington", "WI": "Wisconsin", "WV": "West Virginia", "WY": "Wyoming", "YT": "Yukon"
}

class ApolloService:
    """Service to fetch contact data from Apollo.io"""
    def __init__(self, logger):
        self.logger = logger
        self.api_key = os.getenv('APOLLO_API_KEY')
        self.api_url = "https://api.apollo.io/api/v1/mixed_people/search"
        if not self.api_key:
            self.logger.warning("APOLLO_API_KEY environment variable not set.")

    def _format_apollo_person(self, person_data):
        """Formats a single person's data from Apollo to our standard format."""
        return {
            "first_name": person_data.get('first_name'),
            "last_name": person_data.get('last_name'),
            "title": person_data.get('title'),
            "email": None, # Email is not reliably returned by default
            "city": person_data.get('city'),
            "state": person_data.get('state'),
            "phone_numbers": [], # Phone numbers are not reliably returned for the person
            "social_media": {
                "linkedin_url": person_data.get('linkedin_url'),
                "twitter_url": person_data.get('twitter_url'),
                "facebook_url": person_data.get('facebook_url')
            }
        }

    def get_people_by_domain(self, domain, limit=None):
        """Fetches people from Apollo based on a company domain."""
        if not self.api_key:
            self.logger.error("Cannot fetch from Apollo, API key is missing.")
            return []

        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        }
        
        params = {
            "q_organization_domains_list[]": [domain],
            "page": 1,
            "per_page": limit if limit is not None else 100 # Default to 100 if no limit is provided
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, params=params)
            self.logger.info(f"Apollo API Response: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            
            people_found = data.get('people', [])
            self.logger.info(f"Found {len(people_found)} people from Apollo for domain '{domain}'.")
            
            return [self._format_apollo_person(p) for p in people_found]

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Apollo API HTTP Error: {e} - Response: {e.response.text}")
            return []
        except Exception as e:
            self.logger.error(f"An unknown error occurred with Apollo API: {e}")
            return []

class Lead411Service:
    """Service class to handle fetching connected people from Lead411"""
    def __init__(self, logger):
        self.logger = logger
        self.base_url = "https://api.lead411.com/v1"
        self.email = os.getenv('GROWJO_EMAIL')
        self.password = os.getenv('GROWJO_PASSWORD')
        self.api_token = None



        if not self.email or not self.password:
            self.logger.warning("GROWJO_EMAIL or GROWJO_PASSWORD environment variables not set.")

    def _get_access_token(self):
        self.logger.info("Attempting to get Lead411 access token...")
        url = f"{self.base_url}/authenticate_user"
        
        # Use JSON body instead of query parameters
        credentials = {'email': self.email, 'password': self.password}
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.post(url, json=credentials, headers=headers)
            
            response.raise_for_status()
            data = response.json()
            if 'token' in data:
                self.logger.info("Successfully obtained Lead411 access token.")
                self.api_token = data['token']
                return self.api_token
            else:
                self.logger.error(f"Token not found in response: {data}")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"An error occurred during Lead411 authentication: {e}")
            raise e

    def _get_company_employees(self, company_id, per_page=None):
        self.logger.info(f"Getting Lead411 employees for company ID: {company_id}...")
        url = f"{self.base_url}/company/getCompanyEmployees"
        params = {'token': self.api_token, 'company_id': company_id}
        if per_page:
            params['per_page'] = per_page
        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get('companyEmployeesData', {}).get('companyEmployees'):
                employees = data['companyEmployeesData']['companyEmployees']
                self.logger.info(f"Found {len(employees)} employee records from Lead411.")
                return employees
            return []
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            self.logger.error(f"An error occurred while getting Lead411 employees: {e}")
            raise e

    def _unlock_employee_record(self, employee_id):
        self.logger.info(f"Unlocking Lead411 contact info for employee ID: {employee_id}...")
        url = f"{self.base_url}/employee/unlock_employee_record"
        params = {'token': self.api_token, 'employee_id': employee_id}
        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            self.logger.error(f"An error occurred while unlocking Lead411 record for ID {employee_id}: {e}")
            raise e

    def get_connected_people(self, company_id, limit=None):
        if not self.api_token:
            self._get_access_token()
            if not self.api_token:
                raise Exception("Failed to authenticate with Lead411 API")
        
        employees = self._get_company_employees(company_id, limit)
        if not employees:
            return []

        formatted_employee_data = []
        for employee in employees:
            emp_id = employee.get('employee_id')
            if not emp_id:
                continue
            
            try:
                unlocked_info = self._unlock_employee_record(emp_id)
            except Exception as e:
                self.logger.error(f"Could not unlock record for employee {emp_id}: {e}")
                unlocked_info = None

            phone_numbers = []
            if unlocked_info and isinstance(unlocked_info.get('employeePhoneData'), list):
                for phone_data in unlocked_info['employeePhoneData']:
                    phone_numbers.append({
                        "number": phone_data.get('phone'),
                        "type": phone_data.get('line_type')
                    })

            state_code = employee.get('region_code')
            state_name = STATE_MAP.get(state_code, state_code)

            formatted_data = {
                "first_name": employee.get('first_name'),
                "last_name": employee.get('last_name'),
                "title": employee.get('employee_title'),
                "email": unlocked_info.get('email') if unlocked_info else None,
                "city": employee.get('city'),
                "state": state_name,
                "phone_numbers": phone_numbers,
                "social_media": {
                    "linkedin_url": employee.get('employee_linkedin'),
                    "twitter_url": employee.get('employee_twitter'),
                    "facebook_url": employee.get('employee_facebook')
                }
            }
            formatted_employee_data.append(formatted_data)
        
        return formatted_employee_data

class ConnectedPeopleService:
    """Orchestrator service to fetch data from multiple sources."""
    def __init__(self, logger):
        self.logger = logger
        self.lead411_service = Lead411Service(logger)
        self.apollo_service = ApolloService(logger)

    def get_connected_people(self, company_id, domain=None, limit=None):
        # Primary data source is always Lead411
        self.logger.info("Using Lead411 as the primary data source.")
        final_results = self.lead411_service.get_connected_people(company_id, limit)
        
        # Determine if a fallback to Apollo is needed
        should_fallback = False
        if domain:
            if limit is not None:
                if len(final_results) < limit:
                    should_fallback = True
            else: # If no limit is set, always try to supplement
                should_fallback = True

        if should_fallback:
            self.logger.info(f"Lead411 returned {len(final_results)} results. Checking Apollo for supplementary data.")
            
            # Determine how many more contacts to fetch from Apollo
            apollo_limit = (limit - len(final_results)) if limit is not None else 100
            
            if apollo_limit > 0:
                apollo_results = self.apollo_service.get_people_by_domain(domain, apollo_limit)

                if apollo_results:
                    # Deduplicate results before combining them
                    existing_linkedin_urls = {
                        p['social_media']['linkedin_url'] 
                        for p in final_results 
                        if p.get('social_media', {}).get('linkedin_url')
                    }
                    
                    for person in apollo_results:
                        # Stop if we've reached the desired limit
                        if limit is not None and len(final_results) >= limit:
                            break
                            
                        linkedin_url = person.get('social_media', {}).get('linkedin_url')
                        if linkedin_url and linkedin_url not in existing_linkedin_urls:
                            final_results.append(person)
                            existing_linkedin_urls.add(linkedin_url)
                            self.logger.info(f"Added unique person from Apollo: {person.get('first_name')} {person.get('last_name')}")

        return final_results
