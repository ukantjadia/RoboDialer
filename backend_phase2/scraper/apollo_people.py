import requests
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# Required fields for database and Growjo integration:
# - person name (for the db, growjo) - provided via name parameter
# - company name (db, growjo) - provided via organization_name parameter  
# - domain (apollo) - provided via domain parameter
# At least one of organization_name or domain must be provided for Apollo API calls

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
APOLLO_PEOPLE_MATCH_URL = "https://api.apollo.io/api/v1/people/match"
APOLLO_MIXED_PEOPLE_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/search"


def normalize(value: Optional[str]) -> str:
    """
    Takes any raw value and:
      1) Strips it.
      2) If empty or in ["", "not", "found", "not found", "none"], returns "N/A".
      3) Otherwise returns the trimmed string.
    """
    if value is None:
        return "N/A"
    try:
        raw = str(value).strip()
        lower = raw.lower()
        if lower in ["", "not", "found", "not found", "none", "n/a", "na"]:
            return "N/A"
        return raw
    except:
        return "N/A"


def apollo_enrich_people(name: Optional[str] = None, organization_name: Optional[str] = None, domain: Optional[str] = None) -> Dict[str, Any]:
    """
    Enrich people data using Apollo's People Match API.
    
    Args:
        name: The name of the person to search for (optional)
        organization_name: The name of the company/organization (optional, if no domain provided)
        domain: The domain of the company (optional, if no organization_name provided)
    
    At least one of organization_name or domain must be provided for the search to work.
    
    Returns:
        Dictionary containing enriched people data with essential fields
    """
    
    if not APOLLO_API_KEY:
        return {
            "error": "APOLLO_API_KEY not found in environment variables",
            "success": False
        }
    
    # At least one of organization_name or domain must be provided
    if not organization_name and not domain:
        return {
            "error": "At least one of organization_name or domain must be provided",
            "success": False
        }
    
    headers = {
        "accept": "application/json",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "x-api-key": APOLLO_API_KEY
    }
    
    # Build parameters dict
    params = {}
    
    # Add name if provided (this is the main search parameter)
    if name and name.strip():
        # Split name into first and last name if it contains spaces
        name_parts = name.strip().split()
        if len(name_parts) >= 2:
            params["first_name"] = name_parts[0]
            params["last_name"] = " ".join(name_parts[1:])
        else:
            params["first_name"] = name.strip()
    
    # Add organization_name if provided (optional)
    if organization_name and organization_name.strip():
        params["organization_name"] = organization_name.strip()
    
    # Add domain if provided (optional)
    if domain and domain.strip():
        clean_domain = domain.strip().lower()
        if clean_domain.startswith(('http://', 'https://')):
            clean_domain = clean_domain.split('//')[1]
        if clean_domain.startswith('www.'):
            clean_domain = clean_domain[4:]
        params["domain"] = clean_domain
    
    # Ensure we have at least the name parameter for the API call
    if not params:
        return {
            "error": "At least a name must be provided for the search",
            "success": False
        }
    
    try:
        response = requests.post(APOLLO_PEOPLE_MATCH_URL, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            person = data.get("person", {})
            
            if not person:
                # Determine what we were searching by for the error message
                search_terms = []
                if name: search_terms.append(f"name '{name}'")
                if organization_name: search_terms.append(f"company '{organization_name}'")
                if domain: search_terms.append(f"domain '{domain}'")
                search_description = " and ".join(search_terms) if search_terms else "the provided criteria"
                
                return {
                    "success": False,
                    "error": "No person found",
                    "message": f"Apollo couldn't find any person matching {search_description}"
                }
            
            # Extract essential people data points
            # Handle name construction more intelligently
            first_name = person.get('first_name', '')
            last_name = person.get('last_name', '')
            
            # Build name intelligently - avoid "None" or empty parts
            if first_name and last_name:
                full_name = f"{first_name} {last_name}".strip()
            elif first_name:
                full_name = first_name.strip()
            elif last_name:
                full_name = last_name.strip()
            else:
                full_name = "Unknown"
            
            enriched_data = {
                "name": normalize(full_name),
                "title": normalize(person.get("title") or person.get("headline")),
                "company": normalize(organization_name or person.get("organization_name", "") or domain or "Unknown"),
                "phone": normalize(person.get("phone") or person.get("sanitized_phone")),
                "phone_number": normalize(person.get("phone") or person.get("sanitized_phone")),
                "email": normalize(person.get("email")),
                "linkedin": normalize(person.get("linkedin_url")),
                "linkedin_url": normalize(person.get("linkedin_url")),
                "location": normalize(person.get("location") or person.get("city") or person.get("state") or "N/A"),
                "address": normalize(person.get("address") or person.get("street_address") or "N/A")
            }
            
            return {
                "success": True,
                "data": enriched_data
            }
        else:
            return {
                "success": False,
                "error": f"API request failed with status {response.status_code}",
                "response": response.text
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}"
        }


def find_all_people_for_domain(domain: str) -> list:
    """
    Find all people for a given domain (kept for backward compatibility).
    This function is used by the existing /apollo-scrape-people-enhancement endpoint.
    """
    try:
        # Query Apollo search for all people
        params = {
            "person_titles[]": "",
            "person_seniorities[]": ["owner", "founder", "c_suite", "vp", "director", "manager"],
            "q_organization_domains_list[]": domain,
            "contact_email_status[]": "",
        }
        headers = {
            "accept": "application/json",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "x-api-key": APOLLO_API_KEY,
        }

        response = requests.post("https://api.apollo.io/api/v1/mixed_people/search", headers=headers, params=params)
        if response.status_code != 200:
            return []

        data = response.json()
        people = data.get("contacts", [])

        # If no people found, return empty array
        if not people:
            return []

        # Process each person
        all_people = []
        for person in people:
            person_result = {
                "name": f"{normalize(person.get('first_name'))} {normalize(person.get('last_name'))}".strip(),
                "title": normalize(person.get("title")),
                "email": normalize(person.get("email")),
                "phone": normalize(
                    person.get("organization", {}).get("primary_phone", {}).get("sanitized_number")
                ),
                "linkedin": normalize(person.get("linkedin_url")),
                "company": normalize(person.get("organization", {}).get("name")),
                "domain": domain,
                "profile_url": normalize(person.get("linkedin_url")),
            }

            all_people.append(person_result)

        return all_people

    except Exception as e:
        print(f"[ERROR] Error finding all people for domain {domain}: {str(e)}")
        return []


def apollo_search_people(domain: str, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """
    Search for people using Apollo's Mixed People Search API.
    This function returns multiple possible matches for the user to choose from.
    
    Args:
        domain: The domain of the company (REQUIRED)
        page: Page number for pagination (default: 1)
        per_page: Results per page (default: 10)
    
    Returns:
        Dictionary containing search results with people data and pagination info
    """
    
    if not APOLLO_API_KEY:
        return {
            "error": "APOLLO_API_KEY not found in environment variables",
            "success": False
        }
    
    # Domain is now mandatory
    if not domain or not domain.strip():
        return {
            "error": "Domain parameter is required",
            "success": False
        }
    
    headers = {
        "accept": "application/json",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "x-api-key": APOLLO_API_KEY
    }
    
    # Clean domain first
    clean_domain = domain.strip().lower()
    if clean_domain.startswith(('http://', 'https://')):
        clean_domain = clean_domain.split('//')[1]
    if clean_domain.startswith('www.'):
        clean_domain = clean_domain[4:]
    
    # We'll build the URL manually to match the curl request exactly
    
    try:
        # Build URL exactly like the curl request
        from urllib.parse import urlencode
        
        # Build query string manually to match curl exactly
        query_params = []
        query_params.append(f"q_organization_domains_list[]={clean_domain}")
        query_params.append("organization_num_employees_ranges[]=")  # Empty value like in curl
        query_params.append("person_titles[]=")
        query_params.append("contact_email_status[]=")
        
        # Add pagination parameters
        query_params.append(f"page={page}")
        query_params.append(f"per_page={per_page}")
        
        query_string = "&".join(query_params)
        full_url = f"{APOLLO_MIXED_PEOPLE_SEARCH_URL}?{query_string}"
        
        print(f"🔍 Full URL: {full_url}")
        print(f"🔍 Pagination: page={page}, per_page={per_page}")
        
        response = requests.post(full_url, headers=headers)
        
        print(f"🔍 Apollo API Response Status: {response.status_code}")
        print(f"🔍 Apollo API Response URL: {response.url}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"🔍 Apollo API Response Structure: {list(data.keys())}")  # Debug: Show response structure
            
            people = data.get("people", [])  # Changed from "contacts" to "people"
            pagination = data.get("pagination", {})
            
            print(f"🔍 Found {len(people)} people in response")  # Debug: Show count
            
            if people and len(people) > 0:
                print(f"🔍 First person structure: {list(people[0].keys())}")  # Debug: Show first person structure
            
            # Process each person to extract essential information
            people_results = []
            for person in people:
                # Extract organization info
                organization = person.get("organization", {})
                
                # Extract phone number - Apollo API doesn't provide phone in this response
                phone = "N/A"  # Phone not available in mixed_people/search response
                
                person_data = {
                    "id": person.get("id", ""),
                    "name": person.get("name", ""),  # Use the 'name' field directly
                    "title": person.get("title", ""),  # Use the 'title' field directly
                    "company": organization.get("name", ""),
                    "domain": organization.get("primary_domain", ""),
                    "email": person.get("email", ""),
                    "phone": phone,
                    "linkedin": person.get("linkedin_url", ""),
                    "location": person.get("formatted_address", ""),
                    "seniority": person.get("seniority", ""),
                    "department": person.get("departments", []),  # This is an array
                    "profile_picture": person.get("photo_url", ""),
                    "contact_status": person.get("email_status", ""),  # Use email_status instead
                    "email_status": person.get("email_status", "")
                }
                
                people_results.append(person_data)
            
            return {
                "success": True,
                "people": people_results,
                "pagination": {
                    "page": pagination.get("page", page),
                    "per_page": pagination.get("per_page", per_page),
                    "total": pagination.get("total_entries", len(people_results)),
                    "total_pages": pagination.get("total_pages", 1)
                },
                "total_results": len(people_results)
            }
            
        else:
            return {
                "success": False,
                "error": f"API request failed with status {response.status_code}",
                "response": response.text
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}"
        }


# Example usage functions
def example_apollo_enrich_people():
    """Example: Enrich people data by organization name"""
    result = apollo_enrich_people(organization_name="Apollo.io")
    print("Apollo enrich people result:", result)
    return result


def example_apollo_enrich_people_with_domain():
    """Example: Enrich people data by organization name and domain"""
    result = apollo_enrich_people(organization_name="Apollo.io", domain="apollo.io")
    print("Apollo enrich people with domain result:", result)
    return result


def example_apollo_enrich_people_with_name():
    """Example: Enrich people data by name, organization name, and domain"""
    result = apollo_enrich_people(name="John Smith", organization_name="Apollo.io", domain="apollo.io")
    print("Apollo enrich people with name result:", result)
    return result


def example_apollo_search_people():
    """Example: Search for people using the new search functionality"""
    result = apollo_search_people(domain="apollo.io", page=1, per_page=5)
    print("Apollo search people result:", result)
    return result


if __name__ == "__main__":
    # Run examples
    example_apollo_enrich_people()
    example_apollo_enrich_people_with_domain()
    example_apollo_enrich_people_with_name()
    example_apollo_search_people()
