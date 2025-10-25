# backend_phase2/api/routes/enrich.py

import os
import requests
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables FIRST, before any imports
current_file_dir = Path(__file__).parent
env_path = current_file_dir.parent.parent / '.env'
load_dotenv(env_path)

# Required fields for database and Growjo integration:
# - person name (for the db, growjo) - provided via name parameter
# - company name (db, growjo) - provided via organization_name parameter  
# - domain (apollo) - provided via q_organization_domains_list parameter for Apollo API
# At least one of organization_name or domain must be provided for Apollo API calls

# THEN do the imports after environment is loaded
from backend_phase2.scraper.apollo_scraper import enrich_single_company
from backend_phase2.scraper.apollo_people import find_all_people_for_domain, apollo_enrich_people, apollo_search_people
from backend_phase2.scraper.apollo_company import apollo_search_company, apollo_enrich_company

enrich_bp = Blueprint('enrich', __name__)

# === GROWJO APIS ===

@enrich_bp.route("/growjo/company/<int:company_id>", methods=["POST"])
def growjo_enrich_company_by_id(company_id):
    """
    Enrich company data using Growjo API with company_id
    """
    try:
        from backend_phase2.scraper.growjo_company import enrich_company_with_growjo
        
        result = enrich_company_with_growjo(company_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@enrich_bp.route("/growjo/people/<int:company_id>", methods=["POST"])
def growjo_enrich_people_by_company_id(company_id):
    """
    Enrich people data using Growjo API with company_id
    """
    try:
        from backend_phase2.scraper.growjo_people import enrich_people_with_growjo
        
        result = enrich_people_with_growjo(company_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === BUSINESS TYPE DECIDER API ===

@enrich_bp.route("/business-type-decider", methods=["POST"])
def business_type_decider():
    """
    Determine business type (B2B, B2C, B2B2C) using DeepSeek AI based on products/tags.
    
    Expected JSON payload:
    - products: String containing products, services, or tags to analyze
    
    Returns:
    - success: boolean
    - business_type: "B2B", "B2C", or "B2B2C"
    - confidence: confidence level (optional)
    """
    try:
        payload = request.get_json() or {}
        products = payload.get("products")
        
        if not products:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: products"
            }), 400
        
        # Get DeepSeek API key from environment
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            return jsonify({
                "success": False,
                "error": "DeepSeek API key not configured"
            }), 500
        
        # Prepare the prompt for DeepSeek
        prompt = f"""Based on these products/services: {products}

Determine if this company is B2B, B2C, or B2B2C.

B2B = Business-to-Business (sells to other businesses)
B2C = Business-to-Consumer (sells directly to end consumers)
B2B2C = Business-to-Business-to-Consumer (sells to businesses who then sell to consumers)

Only respond with the category: B2B, B2C, or B2B2C. No other text."""
        
        # Call DeepSeek API
        headers = {
            "Authorization": f"Bearer {deepseek_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Low temperature for consistent responses
            "max_tokens": 10     # We only need a short response
        }
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({
                "success": False,
                "error": f"DeepSeek API error: {response.status_code}",
                "details": response.text
            }), 500
        
        # Parse the response
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        
        # Validate the response
        valid_types = ["B2B", "B2C", "B2B2C"]
        business_type = None
        
        for valid_type in valid_types:
            if valid_type in content.upper():
                business_type = valid_type
                break
        
        if not business_type:
            # If AI response is unclear, make an educated guess based on keywords
            products_lower = products.lower()
            if any(keyword in products_lower for keyword in ["consulting", "enterprise", "b2b", "business", "corporate"]):
                business_type = "B2B"
            elif any(keyword in products_lower for keyword in ["consumer", "retail", "personal", "individual"]):
                business_type = "B2C"
            else:
                business_type = "B2B"  # Default to B2B for most tech companies
        
        return jsonify({
            "success": True,
            "business_type": business_type,
            "confidence": "high" if business_type in content else "estimated",
            "ai_response": content,
            "products_analyzed": products
        }), 200
        
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "DeepSeek API timeout"
        }), 500
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "error": f"DeepSeek API request failed: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Business type decider failed: {str(e)}"
        }), 500

# === APOLLO APIS ===





@enrich_bp.route("/apollo-search-company", methods=["POST"])
def apollo_search_company_endpoint():
    """
    Search for companies by name using Apollo's Mixed Companies Search API.
    
    Expected JSON payload:
    - company_name: Company name to search for
    - page: Page number (optional, default: 1)
    - per_page: Results per page (optional, default: 10)
    
    Returns:
    - success: boolean
    - companies: array of company objects with essential data
    - pagination: pagination information
    """
    try:
        payload = request.get_json() or {}
        
        # Extract parameters
        company_name = payload.get("company_name")
        page = payload.get("page", 1)
        per_page = payload.get("per_page", 10)
        
        if not company_name:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: company_name"
            }), 400
        
        # Call Apollo search company API
        result = apollo_search_company(company_name, page, per_page)
        
        if not result.get("success"):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to search for companies"
        }), 500


@enrich_bp.route("/apollo-enrich-company", methods=["POST"])
def apollo_enrich_company_endpoint():
    """
    Enrich company data by domain using Apollo's Organization Enrich API.
    
    Expected JSON payload:
    - domain: Company domain (e.g., "apollo.io", "microsoft.com")
    
    Returns:
    - success: boolean
    - data: enriched company data with essential fields
    - organization: same as data for compatibility
    """
    try:
        payload = request.get_json() or {}
        
        # Extract parameters
        domain = payload.get("domain")
        
        if not domain:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: domain"
            }), 400
        
        # Call Apollo enrich company API
        result = apollo_enrich_company(domain)
        
        if not result.get("success"):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to enrich company data"
        }), 500


@enrich_bp.route("/apollo-enrich-people", methods=["POST"])
def apollo_enrich_people_endpoint():
    """
    Enrich people data using Apollo's People Match API.
    
    Expected JSON payload:
    - name: Person name to search for (optional)
    - organization_name: Company/organization name (optional, if no domain provided)
    - domain: Company domain (optional, if no organization_name provided)
    
    At least one of organization_name or domain must be provided for the search to work.
    
    Returns:
    - success: boolean
    - data: enriched people data with essential fields
    """
    try:
        payload = request.get_json() or {}
        
        # Extract parameters
        name = payload.get("name")
        organization_name = payload.get("organization_name")
        domain = payload.get("domain")
        
        # Validate that at least one of organization_name or domain is provided
        if not organization_name and not domain:
            return jsonify({
                "success": False,
                "error": "At least one of organization_name or domain must be provided"
            }), 400
        
        # Call Apollo enrich people API
        result = apollo_enrich_people(name, organization_name, domain)
        
        if not result.get("success"):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to enrich people data"
        }), 500




@enrich_bp.route("/apollo-scrape-people-enhancement", methods=["POST"])
def apollo_scrape_people_enhancement():
    """
    - Call find_all_people_for_domain(...) to get all people for a domain.
    - Returns a list of people with their details.
    """
    try:
        payload = request.get_json()
        domain = payload.get("domain")
        if not domain:
            return jsonify({"error": "Missing domain"}), 400

        people = find_all_people_for_domain(domain.strip())
        
        # Check if we found any people
        if not people or len(people) == 0:
            return jsonify({
                "people": [],
                "message": f"No people found for domain '{domain}'",
                "suggestion": "This domain might not have any publicly available contact information"
            }), 200
        
        # Return the people array directly
        return jsonify({"people": people}), 200

    except Exception as e:
        return jsonify({
            "error": str(e),
            "message": "Failed to search for people",
            "suggestion": "Please try again later"
        }), 500


@enrich_bp.route("/apollo-search-people", methods=["POST"])
def apollo_search_people_endpoint():
    """
    Search for people using Apollo's Mixed People Search API.
    This endpoint returns multiple possible matches for the user to choose from.
    
    Expected JSON payload:
    - q_organization_domains_list: Company domain (REQUIRED)
    - page: Page number for pagination (optional, default: 1)
    - per_page: Results per page (optional, default: 10)
    
    Domain parameter is required as Apollo's API only searches by domain.
    
    Returns:
    - success: boolean
    - people: array of people objects with essential data
    - pagination: pagination information
    - total_results: total number of results found
    """
    try:
        payload = request.get_json() or {}
        
        # Extract parameters - use the correct Apollo API parameter name
        domain = payload.get("q_organization_domains_list")
        page = payload.get("page", 1)
        per_page = payload.get("per_page", 10)
        
        # Validate that domain is provided (it's now mandatory)
        if not domain or not domain.strip():
            return jsonify({
                "success": False,
                "error": "q_organization_domains_list parameter is required"
            }), 400
        
        # Call Apollo search people API
        result = apollo_search_people(domain, page, per_page)
        
        if not result.get("success"):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to search for people"
        }), 500
