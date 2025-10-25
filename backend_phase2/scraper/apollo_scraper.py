from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
import random

load_dotenv()
app = Flask(__name__)

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # Assuming you're using an LLM with an OpenAI-compatible API

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1",  # Replace with actual base URL if different
)

def infer_business_type(description):
    if not description or not description.strip():
        return "N/A"

    prompt = (
        "You are a classifier. Based only on the description below, respond with one of the following labels: B2B, B2C, or B2B2C. "
        "Respond only with the label and nothing else.\n\n"
        f'Description:\n"{description}"\n\nBusiness Type:'
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",  # or the model you're using
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        label = response.choices[0].message.content.strip().upper()
        if label in ["B2B", "B2C", "B2B2C"]:
            return label
        else:
            return "N/A"
    except Exception as e:
        print(f"[ERROR] Failed to classify business type: {e}")
        return "N/A"


def normalize(value: str | None) -> str:
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


def enrich_single_company(domain):
    """
    Call Apollo API and extract founded_year, linkedin_url, keywords,
    annual_revenue_printed, website_url, employee_count, industry,
    business_type — replacing any empty or missing value with "N/A".
    """
    url = "https://api.apollo.io/api/v1/organizations/enrich"
    headers = {
        "accept": "application/json",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": APOLLO_API_KEY,
    }
    params = {"domain": domain}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            org = response.json().get("organization", {})

            # Extract raw values (may be empty string or None)
            raw_founded_year         = org.get("founded_year", "")
            raw_linkedin_url         = org.get("linkedin_url", "")
            raw_keywords_list        = org.get("keywords", [])
            raw_annual_revenue       = org.get("annual_revenue_printed", "")
            raw_website_url          = org.get("website_url", "")
            raw_employee_count       = org.get("estimated_num_employees", "")
            raw_industry             = org.get("industry", "")
            raw_about                = org.get("short_description", "")

            # Trim or convert as needed
            founded_year     = str(raw_founded_year).strip()
            linkedin_url     = str(raw_linkedin_url).strip()
            annual_revenue   = str(raw_annual_revenue).strip()
            website_url      = str(raw_website_url).strip()
            employee_count   = str(raw_employee_count).strip()
            industry         = str(raw_industry).strip()
            about            = str(raw_about).strip()

            # Keywords: limit to 5 if list, otherwise fallback
            if isinstance(raw_keywords_list, list) and raw_keywords_list:
                keywords_trimmed = raw_keywords_list[:5]
                keywords_combined = ", ".join(kw.strip() for kw in keywords_trimmed if kw and kw.strip())
                keywords = keywords_combined.strip()
            else:
                keywords = ""

            # Business type via LLM
            business_type    = infer_business_type(about)

            # Apply "N/A" for each field that ended up empty
            return {
                "founded_year":         normalize(founded_year),
                "linkedin_url":         normalize(linkedin_url),
                "keywords":             normalize(keywords),
                "annual_revenue_printed": normalize(annual_revenue),
                "website_url":          normalize(website_url),
                "employee_count":       normalize(employee_count),
                "industry":             normalize(industry),
                "business_type":        normalize(business_type),
            }

        else:
            if response.status_code == 422:
                return {"error": f"Status 422 - Apollo service temporarily unavailable", "status_code": 422}
            elif response.status_code == 404:
                return {"error": "Company not found in Apollo database", "status_code": 404}
            elif response.status_code == 429:
                return {"error": "Rate limit exceeded - please try again later", "status_code": 429}
            else:
                return {"error": f"Apollo API error: Status {response.status_code}", "status_code": response.status_code}

    except Exception as e:
        return {"error": f"Apollo API request failed: {str(e)}", "status_code": 500}
