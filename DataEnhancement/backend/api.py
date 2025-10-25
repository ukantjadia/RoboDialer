from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import pandas as pd
import asyncio
import uuid
import logging
from scraper.revenueScraper import get_company_revenue_from_growjo
from scraper.websiteNameScraper import find_company_website
from scraper.apollo_scraper import enrich_single_company
from scraper.linkedinScraper.scraping.scraper import scrape_linkedin
from scraper.linkedinScraper.scraping.login import login_to_linkedin
from scraper.linkedinScraper.utils.chromeUtils import get_chrome_driver
from scraper.linkedinScraper.main import run_batches
from scraper.growjoScraper import GrowjoScraper
from security import generate_token, token_required, VALID_USERS
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__)
# Allow all origins for development; restrict in production
CORS(app)

# Load environment variables before importing modules that use them
load_dotenv()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    if VALID_USERS.get(username) != password:
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({
        "message": "Login successful",
        "token": generate_token(username),
        "username": username
    }), 200

# Protected Test Endpoint
@app.route('/api/protected-test', methods=['GET'])
@token_required
def protected_test():
    return jsonify({"message": "This is a protected route"}), 200

@app.route("/api/find-website", methods=["GET"])
@token_required
def get_website():
    company = request.args.get("company")
    if not company:
        return jsonify({"error": "Missing company parameter"}), 400

    website = find_company_website(company)
    print(website)
    if website:
        return jsonify({"company": company, "website": website})
    else:
        return jsonify({"error": "Website not found"}), 404

@app.route("/api/get-revenue", methods=["GET"])
@token_required
def get_revenue():
    company = request.args.get("company")
    if not company:
        return jsonify({"error": "Missing company parameter"}), 400

    data = get_company_revenue_from_growjo(company)
    return jsonify(data)

@app.route("/api/apollo-info", methods=["POST"])
@token_required
def get_apollo_info_batch():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        if isinstance(data, dict):
            data = [data]

        results = []
        for company in data:
            domain = company.get("domain")
            if domain:
                enriched = enrich_single_company(domain)
                results.append(enriched)
            else:
                results.append({"error": "Missing domain"})

        return jsonify(results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/linkedin-info-batch", methods=["POST"])
@token_required
def get_linkedin_info_batch():
    try:
        load_dotenv()
        data_list = request.get_json()

        if not isinstance(data_list, list):
            return jsonify({"error": "Expected a list of objects"}), 400

        # Convert and normalize DataFrame
        df = pd.DataFrame(data_list)
        df.rename(columns=lambda col: col.capitalize(), inplace=True)

        if df.empty or "Company" not in df.columns:
            return jsonify({"error": "Missing or empty 'Company' column"}), 400

        client_id = f"api_{uuid.uuid4().hex[:8]}"
        results = run_batches(df, client_id=client_id)

        return jsonify(results), 200

    except Exception as e:
        logging.error(f":fire: API Fatal error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/growjo", methods=["POST"])
def scrape():
    data = request.get_json()
    if not data or "company" not in data:
        return jsonify({"error": "Missing 'company' in request JSON"}), 400

    company = data["company"]
    headless = data.get("headless", True)

    scraper = GrowjoScraper(headless=headless)
    try:
        results = scraper.scrape_company(company)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        scraper.close()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
