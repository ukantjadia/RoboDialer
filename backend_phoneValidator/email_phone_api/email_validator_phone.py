import os
import logging
import requests
import socket
from dotenv import load_dotenv
import sys
import pandas as pd
from io import StringIO, BytesIO
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Load env vars
load_dotenv()

class EmailValidator:
    def __init__(self):
        self.user_id = os.getenv("NEUTRINO_USER_ID")
        self.api_key = os.getenv("NEUTRINO_API_KEY")
        if not (self.user_id and self.api_key):
            logger.warning("Neutrino API credentials missing")
        self.validate_url = "https://neutrinoapi.net/email-validate"
        self.verify_url = "https://neutrinoapi.net/email-verify"

    def _call_api(self, url, params):
        headers = {
            "User-ID": self.user_id,
            "API-Key": self.api_key
        }
        try:
            resp = requests.post(url, data=params, headers=headers, timeout=15)
            if resp.status_code == 429 or "limit-exceeded" in resp.text.lower():
                logger.warning("Neutrino API free-tier quota exceeded. Falling back to basic checks.")
                return "quota_exceeded"
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Neutrino API request failed: {e}")
            return None

    def _basic_syntax_check(self, email):
        import re
        return re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email) is not None

    def _basic_domain_check(self, domain):
        """Fallback: simple domain check"""
        try:
            socket.gethostbyname(domain)
            return True
        except socket.gaierror:
            return False

    def validate_email(self, email, fix_typos=False, smtp_verify=True):
        email = email.strip().lower()

        # Step 1: Neutrino API - Validate
        val = self._call_api(self.validate_url, {"email": email, "fix-typos": fix_typos})
        
        if val == "quota_exceeded":  # Fallback path
            domain = email.split('@')[-1]
            return {
                "email": email,
                "is_personal": None,
                "smtp_status": None,
                "active": self._basic_syntax_check(email) and self._basic_domain_check(domain)
            }

        if not val:
            return {"email": email, "active": False}

        is_personal = val.get("is-personal", False)
        smtp_status = None
        active = False

        # Step 2: SMTP Verify (optional)
        if smtp_verify and val.get("valid"):
            ver = self._call_api(self.verify_url, {"email": val.get("email")})
            if ver and ver != "quota_exceeded":
                smtp_status = ver.get("smtp-status")
                active = bool(ver.get("verified"))
            elif ver == "quota_exceeded":  # Still fallback if quota exceeded at SMTP stage
                domain = email.split('@')[-1]
                active = self._basic_syntax_check(email) and self._basic_domain_check(domain)

        return {
            "email": val.get("email"),
            "is_personal": is_personal,
            "smtp_status": smtp_status,
            "active": active
        }
    
    def bulk_validate_from_file(self, file_content, filename, email_col="email"):
        try:
            # Read file based on extension
            if filename.endswith(".csv"):
                df = pd.read_csv(StringIO(file_content.decode("utf-8")))
            elif filename.endswith(".xlsx"):
                df = pd.read_excel(BytesIO(file_content))
            else:
                return {"error": "Unsupported file type. Use .csv or .xlsx"}

            if email_col not in df.columns:
                return {"error": f"Column '{email_col}' not found in the file"}

            results = []
            for _, row in df.iterrows():
                email = str(row[email_col])
                result = self.validate_email(email)
                results.append(result)

            return results

        except Exception as e:
            return {"error": str(e)}



class PhoneValidator:
    def __init__(self):
        self.user_id = os.getenv("NEUTRINO_USER_ID")
        self.api_key = os.getenv("NEUTRINO_API_KEY")
        self.base_url = "https://neutrinoapi.net"

    def phone_validate(self, number, country_code=""):
        url = f"{self.base_url}/phone-validate"
        payload = {
            "number": number,
            "country-code": country_code
        }
        headers = {
            "User-ID": self.user_id,
            "API-Key": self.api_key
        }
        try:
            response = requests.post(url, headers=headers, data=payload, timeout=10)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def bulk_validate_from_csv(self, file_content, phone_col="phone", country_col="country_code"):
        try:
            # Read CSV into DataFrame
            df = pd.read_csv(StringIO(file_content.decode("utf-8")))

            results = []
            for _, row in df.iterrows():
                number = str(row[phone_col])
                country = str(row[country_col]) if country_col and country_col in df.columns else ""
                result = self.phone_validate(number, country)
                results.append({
                    "phone": number,
                    "country": country,
                    "validation": result
                })

            return results
        except Exception as e:
            return {"error": str(e)}