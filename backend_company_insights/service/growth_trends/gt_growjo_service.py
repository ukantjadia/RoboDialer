import os
import time
import requests
from typing import Optional


# for local testing load GROWJO ENV
from dotenv import load_dotenv
load_dotenv(".env")


def gt_token_growjo_api():
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


def gt_get_company_detail(token: str, company_id: int):
    """Get detailed information about a target company from Growjo API

    Args:
        token (str): Growjo API token
        company_id (int): Company ID of the target company

    Returns:
        dict: Company details
    """

    url = "https://api.lead411.com/v1/company/getCompanyInfo"
    params = {"token": token, "company_id": company_id}

    try:
        response = requests.post(url, params=params)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Growjo API getCompanyInfo successful!")
            return result

        else:
            print(f"❌ API call failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error making API call: {str(e)}")
        return None
