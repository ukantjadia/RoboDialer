import os
import time
import requests
from typing import Optional


# for local testing load GROWJO ENV
# from dotenv import load_dotenv
# load_dotenv(".env")


def token_growjo_api():
    """
    Get growjo token
    add .env file with GROWJO_EMAIL and GROWJO_PASSWORD
    """
    email = os.getenv("GROWJO_EMAIL")
    password = os.getenv("GROWJO_PASSWORD")

    if not email or not password:
        print("Error: GROWJO_EMAIL or GROWJO_PASSWORD not found in environment")
        return None

    url = "https://api.lead411.com/v1/authenticate_user"

    params = {"email": email, "password": password}

    try:
        response = requests.post(url, params=params)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Growjo API authentication successful!")
            # print(f"Response: {result}")

            if "token" in result:
                token = result["token"]
                return token
            else:
                print("ℹ️ No token found in response")
                return None

        else:
            print(f"❌ API call failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error making API call: {str(e)}")
        return None


def get_target_company_detail(token: str, target_company_id: int):
    """Get detailed information about a target company from Growjo API

    Args:
        token (str): Growjo API token
        company_id (int): Company ID of the target company

    Returns:
        dict: Company details
    """

    url = "https://api.lead411.com/v1/company/getCompanyInfo"
    params = {"token": token, "company_id": target_company_id}

    try:
        response = requests.post(url, params=params)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Growjo API getCompanyInfo successful!")
            company_data = result.get("company_data", {})
            return {
                "result": result,
                "sic_code": company_data.get("sic_code"),
                "city": company_data.get("city"),
                "name": company_data.get("company_name"),
            }

        else:
            print(f"❌ API call failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error making API call: {str(e)}")
        return None

def filter_company_id(token, SIC_Codes: int, city: str, range: int = 10):
    url = "https://api.lead411.com/v1/search/searchUsingJSON"
    params = {
        "token": token,
        "SIC_Codes": SIC_Codes,
        "city": city,
        "range": range,
        "limit": 10,
    }

    try:
        response = requests.post(url, params=params)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Growjo API searchUsingJSON successful!")
            company_ids = []
            for company in result.get("AllResults", []):
                company_id = company.get("company_id")
                if company_id:
                    company_ids.append(company_id)
            return company_ids
        else:
            print(f"❌ API call failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error making API call: {str(e)}")
        return None

def get_company_detail(token, company_id: list):
    url = "https://api.lead411.com/v1/company/getCompanyInfo"
    all_results = []
    failed_requests = []

    print(f"🔄 Processing {len(company_id)} company IDs...")

    for idx, single_company_id in enumerate(company_id, 1):
        params = {"token": token, "company_id": single_company_id}
        try:
            print(f"📤 Requesting company ID: {single_company_id} ({idx}/{len(company_id)})")
            response = requests.post(url, params=params, timeout=3)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success for company ID: {single_company_id}")
                result["requested_company_id"] = single_company_id
                all_results.append(result)
            else:
                print(f"❌ Failed for company ID: {single_company_id} - Status: {response.status_code}")
                failed_requests.append({
                    "company_id": single_company_id,
                    "status_code": response.status_code,
                    "error": response.text,
                })
        except requests.Timeout:
            print(f"⏰ Timeout for company ID: {single_company_id} (>{3}s)")
            failed_requests.append({
                "company_id": single_company_id,
                "status_code": None,
                "error": "Timeout > 3s",
            })
        except Exception as e:
            print(f"❌ Exception for company ID: {single_company_id} - Error: {str(e)}")
            failed_requests.append({"company_id": single_company_id, "status_code": None, "error": str(e)})
        
        if idx < len(company_id):
            time.sleep(0.5)

    print(f"📊 Processing complete!")
    print(f"✅ Successful requests: {len(all_results)}")
    print(f"❌ Failed requests: {len(failed_requests)}")
    return all_results