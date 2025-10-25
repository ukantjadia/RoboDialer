import os
import requests
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GROWJO_EMAIL = os.getenv("GROWJO_EMAIL")
GROWJO_PASSWORD = os.getenv("GROWJO_PASSWORD")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1",
)

def get_growjo_token():
    """Get authentication token from Growjo API"""
    try:
        if not GROWJO_EMAIL or not GROWJO_PASSWORD:
            return {
                "success": False,
                "error": "GROWJO_EMAIL and GROWJO_PASSWORD must be set in environment variables"
            }
        
        url = "https://api.lead411.com/v1/authenticate_user"
        params = {
            "email": GROWJO_EMAIL,
            "password": GROWJO_PASSWORD
        }
        
        response = requests.post(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            if 'token' in result:
                return {
                    "success": True,
                    "token": result['token']
                }
            else:
                return {
                    "success": False,
                    "error": "No token found in response"
                }
        else:
            return {
                "success": False,
                "error": f"API call failed with status code: {response.status_code}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error making API call: {str(e)}"
        }

def determine_business_type(product_category):
    """Use DeepSeek to determine business type from product category"""
    try:
        prompt = (
            f"Based on this product category, determine if this is B2B, B2C, or B2B2C. "
            f"Only respond with one of these three options.\n\n"
            f"Product category: {product_category}"
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        
        business_type = (response.choices[0].message.content or "").strip().upper()
        
        # Normalize the response
        if "B2B2C" in business_type:
            return "B2B2C"
        elif "B2B" in business_type:
            return "B2B"
        elif "B2C" in business_type:
            return "B2C"
        else:
            return "Unknown"
            
    except Exception as e:
        print(f"Error determining business type: {str(e)}")
        return "Unknown"

def enrich_company_with_growjo(company_id):
    """Enrich company data using Growjo API"""
    try:
        print(f"🔍 Starting enrichment for company ID: {company_id}")
        
        # Step 1: Get Growjo token
        print("🔐 Getting Growjo token...")
        token_result = get_growjo_token()
        if not token_result["success"]:
            return {
                "success": False,
                "error": f"Failed to get Growjo token: {token_result['error']}"
            }
        
        token = token_result["token"]
        print("✅ Token obtained successfully")
        
        # Step 2: Get company info from Growjo
        print("🏢 Fetching company info from Growjo API...")
        url = "https://api.lead411.com/v1/company/getCompanyInfo"
        params = {
            "token": token,
            "company_id": company_id
        }
        
        response = requests.post(url, params=params)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Company info API call failed with status code: {response.status_code}"
            }
        
        company_data = response.json()
        print("✅ Company data received from API")
        
        # Step 3: Extract relevant fields using ACTUAL API response structure
        print("📊 Processing company data...")
        
        # Get the main company data object
        company_info = company_data.get("company_data", {})
        
        enriched_data = {
            "company_id": company_id,
            "name": company_info.get("company_name", "N/A"),
            "website": company_info.get("URL", "N/A"),
            "phone": company_info.get("phone", "N/A"),
            "address": company_info.get("address1", "N/A"),
            "city": company_info.get("city", "N/A"),
            "state": company_info.get("region_code", "N/A"),
            "zip_code": company_info.get("zip", "N/A"),
            "country": company_info.get("country_code", "N/A"),
            "year_founded": company_info.get("founded", "N/A"),
            "revenue": company_info.get("yearly_revenue_text", "N/A"),
            "employees": company_info.get("number_of_employees_text", "N/A"),
            "industry": company_info.get("industries", "N/A"),
            "product_category": company_info.get("LI_specialties", "N/A"),  # LinkedIn specialties as product category
            "linkedin_url": company_info.get("linkedin_url", "N/A"),
            "twitter_url": company_info.get("twitter", "N/A"),
            "facebook_url": company_info.get("facebook_url", "N/A"),
            "bio": company_info.get("bio", "N/A"),
            "type": company_info.get("type", "N/A"),
            "sic_code": company_info.get("sic_code", "N/A"),
            "sic_description": company_info.get("sic_description", "N/A")
        }
        
        # Step 4: Use DeepSeek to determine business type from industry/tags
        print("🤖 Determining business type with AI...")
        industry_info = company_info.get("industries", "") or company_info.get("tags", "")
        if industry_info and industry_info != "N/A":
            business_type = determine_business_type(industry_info)
            enriched_data["business_type"] = business_type
        else:
            enriched_data["business_type"] = "N/A"
        
        print("✅ Company enrichment completed successfully")
        
        return {
            "success": True,
            "company": enriched_data
        }
        
    except Exception as e:
        print(f"❌ Error in enrich_company_with_growjo: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to enrich company with Growjo: {str(e)}"
        }

if __name__ == "__main__":
    # Test the function
    result = enrich_company_with_growjo(1762)
    print(json.dumps(result, indent=2))
