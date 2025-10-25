import requests
import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
APOLLO_COMPANY_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_companies/search"


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


def _format_revenue(revenue: Optional[float]) -> str:
    """
    Format revenue as a clean string like "100M", "500M", "2K"
    """
    if not revenue or revenue <= 0:
        return "N/A"
    
    if revenue >= 1000000000:  # 1B+
        return f"{int(revenue / 1000000000)}B"
    elif revenue >= 1000000:  # 1M+
        return f"{int(revenue / 1000000)}M"
    elif revenue >= 1000:  # 1K+
        return f"{int(revenue / 1000)}K"
    else:
        return str(int(revenue))





def apollo_search_company(company_name: str, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """
    Search for companies by name using Apollo's Mixed Companies Search API.
    
    Args:
        company_name: The name of the company to search for
        page: Page number for pagination
        per_page: Number of results per page
    
    Returns:
        Dictionary containing the search results with essential company data
    """
    
    if not APOLLO_API_KEY:
        return {
            "error": "APOLLO_API_KEY not found in environment variables",
            "success": False
        }
    
    if not company_name or not company_name.strip():
        return {
            "error": "Company name is required",
            "success": False
        }
    
    headers = {
        "accept": "application/json",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": APOLLO_API_KEY
    }
    
    params = {
        "q_organization_name": company_name.strip(),
        "page": page,
        "per_page": per_page
    }
    
    try:
        response = requests.post(APOLLO_COMPANY_SEARCH_URL, headers=headers, json=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract only essential company data with table-compatible names
            companies = []
            for org in data.get("organizations", []):
                company_data = {
                    "name": org.get("name"),
                    "website_url": org.get("website_url"),
                    "founded_year": org.get("founded_year"),
                    "phone": org.get("phone"),
                    "linkedin_url": org.get("linkedin_url"),
                    "primary_domain": org.get("primary_domain")
                }
                companies.append(company_data)
            
            return {
                "success": True,
                "data": data,
                "companies": companies,
                "pagination": {
                    "page": data.get("pagination", {}).get("page", page),
                    "per_page": data.get("pagination", {}).get("per_page", per_page),
                    "total_entries": data.get("pagination", {}).get("total_entries", 0),
                    "total_pages": data.get("pagination", {}).get("total_pages", 0)
                }
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


def apollo_enrich_company(domain: str) -> Dict[str, Any]:
    """
    Enrich company data by domain using Apollo's Organization Enrich API.
    
    Args:
        domain: The domain of the company to enrich (e.g., "apollo.io", "microsoft.com")
    
    Returns:
        Dictionary containing enriched company data with only essential fields
    """
    
    if not APOLLO_API_KEY:
        return {
            "error": "APOLLO_API_KEY not found in environment variables",
            "success": False
        }
    
    if not domain or not domain.strip():
        return {
            "error": "Domain is required",
            "success": False
        }
    
    # Clean domain (remove http/https/www if present)
    clean_domain = domain.strip().lower()
    if clean_domain.startswith(('http://', 'https://')):
        clean_domain = clean_domain.split('//')[1]
    if clean_domain.startswith('www.'):
        clean_domain = clean_domain[4:]
    
    headers = {
        "accept": "application/json",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": APOLLO_API_KEY
    }
    
    params = {
        "domain": clean_domain
    }
    
    try:
        response = requests.post("https://api.apollo.io/api/v1/organizations/enrich", headers=headers, json=params)
        
        if response.status_code == 200:
            data = response.json()
            organization = data.get("organization", {})
            
            if not organization:
                return {
                    "success": False,
                    "error": "No company found with that domain",
                    "message": f"Apollo couldn't find any company matching domain '{clean_domain}'"
                }
            
            # Extract only essential company data points with table-compatible names
            enriched_data = {
                "name": organization.get("name"),
                "website_url": organization.get("website_url"),
                "founded_year": organization.get("founded_year"),
                "employees": organization.get("estimated_num_employees"),  # Renamed for table
                "industry": organization.get("industry"),
                "product_category": organization.get("industry"),  # Map industry to product_category
                "linkedin_url": organization.get("linkedin_url"),
                "phone": organization.get("phone"),
                "annual_revenue_printed": organization.get("annual_revenue_printed"),  # String format like "100M"
                "organization_revenue": organization.get("annual_revenue"),  # Raw number for calculations
                "revenue": _format_revenue(organization.get("annual_revenue")),  # Clean formatted revenue like "100M"
                "primary_domain": organization.get("primary_domain")
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


# Example usage functions
def example_apollo_search_company():
    """Example: Search for a company by name"""
    result = apollo_search_company("Apollo")
    print("Apollo search company result:", result)
    return result


def example_apollo_enrich_company():
    """Example: Enrich company data by domain"""
    result = apollo_enrich_company("apollo.io")
    print("Apollo enrich company result:", result)
    return result


if __name__ == "__main__":
    # Run examples
    example_apollo_search_company()
    example_apollo_enrich_company()
