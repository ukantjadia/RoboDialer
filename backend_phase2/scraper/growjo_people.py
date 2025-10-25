import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

GROWJO_EMAIL = os.getenv("GROWJO_EMAIL")
GROWJO_PASSWORD = os.getenv("GROWJO_PASSWORD")

def get_growjo_token():
    """Get authentication token from Growjo API"""
    try:
        url = "https://api.lead411.com/v1/authenticate_user"
        params = {
            "email": GROWJO_EMAIL,
            "password": GROWJO_PASSWORD
        }
        
        response = requests.post(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            if 'token' in result:
                return result['token']
            else:
                print("No token found in response")
                return None
        else:
            print(f"Authentication failed with status code: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error getting Growjo token: {str(e)}")
        return None

def get_company_employees(token, company_id):
    """Get list of company employees"""
    try:
        url = "https://api.lead411.com/v1/company/getCompanyEmployees"
        params = {
            "company_id": company_id,
            "token": token,
            "page": 1,
            "per_page": 25
        }
        
        response = requests.post(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"Failed to get company employees: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error getting company employees: {str(e)}")
        return None

def unlock_employee_record(token, employee_id):
    """Unlock employee record to access detailed information"""
    try:
        url = "https://api.lead411.com/v1/employee/unlock_employee_record"
        params = {
            "token": token,
            "employee_id": employee_id
        }
        
        response = requests.post(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to unlock employee: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error unlocking employee: {str(e)}")
        return None

def get_employee_details(token, employee_id):
    """Get detailed information for a specific employee"""
    try:
        url = "https://api.lead411.com/v1/employee/getEmployeeInformation"
        params = {
            "token": token,
            "employee_id": employee_id
        }
        
        response = requests.post(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            
            # Check if employee data is locked and needs unlocking
            if isinstance(result, dict) and result.get('status') == 'success' and 'Unlock API' in result.get('message', ''):
                print(f"Employee {employee_id} data is locked, attempting to unlock...")
                unlock_result = unlock_employee_record(token, employee_id)
                
                if unlock_result:
                    # Try to get employee details again after unlocking
                    import time
                    time.sleep(2)  # Wait a bit for unlock to process
                    retry_response = requests.post(url, params=params)
                    
                    if retry_response.status_code == 200:
                        return retry_response.json()
                    else:
                        return unlock_result  # Return unlock result if retry fails
                else:
                    return result  # Return original result if unlock fails
            
            return result
        else:
            print(f"Failed to get employee details: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error getting employee details: {str(e)}")
        return None

def enrich_people_with_growjo(company_id):
    """Main function to enrich people data using Growjo API"""
    try:
        # Get authentication token
        token = get_growjo_token()
        if not token:
            return {
                "success": False,
                "error": "Failed to authenticate with Growjo API"
            }
        
        # Get company employees list
        employees_response = get_company_employees(token, company_id)
        if not employees_response:
            return {
                "success": False,
                "error": "Failed to get company employees"
            }
        
        # Extract employee IDs from the response
        employee_ids = []
        if isinstance(employees_response, dict) and 'companyEmployeesData' in employees_response:
            company_data = employees_response['companyEmployeesData']
            if 'companyEmployees' in company_data and isinstance(company_data['companyEmployees'], list):
                employee_list = company_data['companyEmployees']
                
                # Extract employee IDs (limit to first 10 for performance)
                for employee in employee_list[:10]:
                    if isinstance(employee, dict) and 'employee_id' in employee:
                        employee_ids.append(employee['employee_id'])
        
        if not employee_ids:
            return {
                "success": False,
                "error": "No employees found for this company"
            }
        
        # Get details for each employee
        people = []
        for employee_id in employee_ids:
            details = get_employee_details(token, employee_id)
            if details and isinstance(details, dict):
                # Extract employee data
                employee_data = None
                if 'employee_data' in details:
                    employee_data = details['employee_data']
                elif 'employee_details' in details:
                    employee_data = details['employee_details']
                
                if employee_data and isinstance(employee_data, dict):
                    # Map to our standard format
                    person = {
                        "name": f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip(),
                        "first_name": employee_data.get('first_name', ''),
                        "last_name": employee_data.get('last_name', ''),
                        "title": employee_data.get('title', ''),
                        "email": employee_data.get('email', ''),
                        "phone": employee_data.get('phone', ''),
                        "phone_number": employee_data.get('empPhone1', ''),
                        "linkedin": employee_data.get('linkedin', ''),
                        "company": employee_data.get('company_name', ''),
                        "profile_url": employee_data.get('profile_url', ''),
                        "locality": employee_data.get('locality', ''),
                        "source": "Growjo"
                    }
                    
                    # Clean up empty values
                    person = {k: v for k, v in person.items() if v and v != 'N/A'}
                    people.append(person)
        
        return {
            "success": True,
            "data": {
                "people": people,
                "total_found": len(people),
                "company_id": company_id
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error enriching people: {str(e)}"
        }
