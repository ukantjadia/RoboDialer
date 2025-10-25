import os
import random
import requests
import json
from dotenv import load_dotenv
from openai import OpenAI
from flask import Flask, request, jsonify

load_dotenv()
app = Flask(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GROWJO_EMAIL = os.getenv("GROWJO_EMAIL")
GROWJO_PASSWORD = os.getenv("GROWJO_PASSWORD")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1",
)

class GrowjoScraper:
    def __init__(self):
        self.token = None
        self.base_url = "https://api.lead411.com/v1"
        
    def init_growjo(self):
        """
        Initialize Growjo API by authenticating and getting a token
        """
        try:
            if not GROWJO_EMAIL or not GROWJO_PASSWORD:
                return {
                    "success": False,
                    "error": "GROWJO_EMAIL and GROWJO_PASSWORD must be set in environment variables"
                }
            
            # Authenticate with Growjo API
            auth_url = f"{self.base_url}/authenticate_user"
            auth_data = {
                "email": GROWJO_EMAIL,
                "password": GROWJO_PASSWORD
            }
            
            response = requests.post(auth_url, json=auth_data)
            
            # Debug: Print response details
            print(f"Growjo Auth Response Status: {response.status_code}")
            print(f"Growjo Auth Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                auth_response = response.json()
                if auth_response.get("status") == "success" and "token" in auth_response:
                    self.token = auth_response["token"]
                    return {
                        "success": True,
                        "message": "Growjo API initialized successfully",
                        "token": self.token
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Authentication failed: {auth_response.get('message', 'No token received')}"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Authentication failed with status {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to initialize Growjo API: {str(e)}"
            }
    
    def is_growjo_init(self):
        """
        Check if Growjo session is still alive by calling getCustomerDetails API
        """
        try:
            if not self.token:
                return {
                    "initialized": False,
                    "error": "No token available. Please initialize Growjo first."
                }
            
            # Test the token by calling getCustomerDetails API
            test_url = f"{self.base_url}/getCustomerDetails"
            headers = {"Authorization": f"Bearer {self.token}"}
            
            response = requests.get(test_url, headers=headers)
            
            if response.status_code == 200:
                return {
                    "initialized": True,
                    "message": "Growjo session is active",
                    "token": self.token
                }
            else:
                # Token might be expired, try to re-authenticate
                reauth_result = self.init_growjo()
                if reauth_result["success"]:
                    return {
                        "initialized": True,
                        "message": "Growjo session was expired but re-authenticated successfully",
                        "token": self.token
                    }
                else:
                    return {
                        "initialized": False,
                        "error": f"Session expired and re-authentication failed: {reauth_result['error']}"
                    }
                    
        except Exception as e:
            return {
                "initialized": False,
                "error": f"Failed to check Growjo initialization: {str(e)}"
            }

    def _ensure_token(self):
        """
        Ensure we have a valid token before making API calls
        """
        if not self.token:
            init_result = self.init_growjo()
            if not init_result["success"]:
                raise Exception(f"Failed to initialize Growjo: {init_result['error']}")
        
        # Check if token is still valid
        check_result = self.is_growjo_init()
        if not check_result["initialized"]:
            raise Exception(f"Growjo session not valid: {check_result['error']}")

   
    def deepseek_guess_website(self, company_name, street=None, city=None, state=None):
        import re
        import json
        location_parts = [part for part in [street, city, state] if part]
        location_context = ", ".join(location_parts)
        prompt = (
            f"You are an AI assistant. Given a company name, guess the most likely website domain (e.g., example.com). "
            f"Only respond with this JSON format:\n"
            f'{"domain": "..."}\n\n'
            f"Company name: {company_name}"
        )
        if location_context:
            prompt += f"\nLocation context: {location_context}"
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            text = (response.choices[0].message.content or "").strip()
            try:
                parsed = json.loads(text)
                raw_domain = parsed.get("domain", "not found")
            except json.JSONDecodeError:
                match = re.search(r'([\w\.-]+\.[a-z]{2,})', text, re.IGNORECASE)
                raw_domain = match.group(1) if match else "not found"
            website = re.sub(r"^https?://", "", raw_domain).rstrip("/")
            return {"website": website}
        except Exception as e:
            return {"website": "not found"}

    def _friendly_fallback(self, field_type):
        """
        Provide friendly fallback messages for missing data
        """
        fallbacks = {
            "revenue": "Revenue information not available",
            "location": "Location details not provided",
            "industry": "Industry classification not available",
            "interests": "Company specialties not listed",
            "employee_count": "Employee count not available",
            "decider_name": "Decision maker not identified",
            "decider_title": "Title information not available",
            "decider_email": "Email not publicly available",
            "decider_phone": "Phone number not listed",
            "decider_linkedin": "LinkedIn profile not found"
        }
        return fallbacks.get(field_type, "Information not available")

    def enrich_company(self, company_name, street=None, city=None, state=None):
        # This is a stub for company enrichment using LLM (no real Growjo API)
        website_info = self.deepseek_guess_website(company_name, street, city, state)
        # You can expand this with more LLM calls for revenue, industry, etc.
        return {
            "company": company_name,
            "website": website_info.get("website", "N/A"),
            "revenue": self._friendly_fallback("revenue"),
            "location": ", ".join(filter(None, [street, city, state])) or self._friendly_fallback("location"),
            "industry": self._friendly_fallback("industry"),
            "interests": self._friendly_fallback("interests"),
            "employee_count": self._friendly_fallback("employee_count"),
        }

    def enrich_person(self, company_name, person_name=None):
        # This is a stub for person enrichment using LLM (no real Growjo API)
        # You can expand this with more LLM calls for title, email, etc.
        return {
            "company": company_name,
            "person": person_name or self._friendly_fallback("decider_name"),
            "title": self._friendly_fallback("decider_title"),
            "email": self._friendly_fallback("decider_email"),
            "phone": self._friendly_fallback("decider_phone"),
            "linkedin": self._friendly_fallback("decider_linkedin"),
        }


