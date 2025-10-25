# =============================================================================
# PRODUCTION VERSION - NO CORS CONFIGURATION
# =============================================================================
from flask import Flask, request, jsonify
# from flask_cors import CORS  # CORS disabled for production
import logging
import time
from datetime import datetime, timezone
import os
from werkzeug.exceptions import BadRequest
import traceback
import sys
import asyncio
from pathlib import Path

# Get the backend_company_insights directory and add it to path
current_file = Path(__file__)
backend_dir = current_file.parent.parent
sys.path.insert(0, str(backend_dir))

from service.map_links.map_links_scraper import (
    GoogleMapsScraper,
)
from service.connected_people.get_connected_people import ConnectedPeopleService
from service.competitors.scoring_algorithm import run_competitor_pipeline
from service.competitors.growjo_service import (
    filter_company_id,
    get_company_detail,
    token_growjo_api,
    get_target_company_detail,
)

from service.growth_trends.gt_growjo_service import (
    gt_get_company_detail,
    gt_token_growjo_api,
)

from service.growth_trends.growth_trends_analysis import (analyze_growth_trends)

from dotenv import load_dotenv #for local testing using .env file
load_dotenv()

# DEBUG: Print environment loading information
import os
print(f"🔍 DEBUG: Flask app starting - Current working directory: {os.getcwd()}")
print(f"🔍 DEBUG: RAPIDAPI_KEY in environment: {'YES' if os.getenv('RAPIDAPI_KEY') else 'NO'}")
if os.getenv('RAPIDAPI_KEY'):
    rapid_key = os.getenv('RAPIDAPI_KEY')
    print(f"🔍 DEBUG: RAPIDAPI_KEY value: {rapid_key[:10]}...{rapid_key[-4:] if len(rapid_key) > 14 else 'SHORT'}")
else:
    print("🔍 DEBUG: RAPIDAPI_KEY not found in environment")

app = Flask(__name__)
# CORS(app)  # CORS disabled for production

# =============================================================================
# LOCAL TESTING VERSION - WITH CORS FOR LOCALHOST:3000 (COMMENTED OUT)
# =============================================================================
# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import logging
# import time
# from datetime import datetime, timezone
# import os
# from werkzeug.exceptions import BadRequest
# import traceback
# import sys
# import asyncio
# from pathlib import Path

# # Get the backend_company_insights directory and add it to path
# current_file = Path(__file__)
# backend_dir = current_file.parent.parent
# sys.path.insert(0, str(backend_dir))

# from service.map_links.map_links_scraper import (
#     GoogleMapsScraper,
# )
# from service.connected_people.get_connected_people import ConnectedPeopleService
# from service.competitors.scoring_algorithm import run_competitor_pipeline
# from service.competitors.growjo_service import (
#     filter_company_id,
#     get_company_detail,
#     token_growjo_api,
#     get_target_company_detail,
# )

# from service.growth_trends.gt_growjo_service import (
#     gt_get_company_detail,
#     gt_token_growjo_api,
# )

# from service.growth_trends.growth_trends_analysis import (analyze_growth_trends)

# from dotenv import load_dotenv #for local testing using .env file
# load_dotenv()

# # DEBUG: Print environment loading information
# import os
# print(f"🔍 DEBUG: Flask app starting - Current working directory: {os.getcwd()}")
# print(f"🔍 DEBUG: RAPIDAPI_KEY in environment: {'YES' if os.getenv('RAPIDAPI_KEY') else 'NO'}")
# if os.getenv('RAPIDAPI_KEY'):
#     rapid_key = os.getenv('RAPIDAPI_KEY')
#     print(f"🔍 DEBUG: RAPIDAPI_KEY value: {rapid_key[:10]}...{rapid_key[-4:] if len(rapid_key) > 14 else 'SHORT'}")
# else:
#     print("🔍 DEBUG: RAPIDAPI_KEY not found in environment")

# app = Flask(__name__)
# CORS(app)  # CORS enabled for localhost:3000

#=============================================================================
#=============================================================================


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


connected_people_service = ConnectedPeopleService(logger)


class ScraperService:
    """Service class to handle scraper operations"""

    @staticmethod
    def scrape_business(company_name, location):
        """
        Scrape business data from Google Maps

        Args:
            company_name (str): Name of the company to search
            location (str): Location to search in

        """
        scraper = None
        try:
            scraper = GoogleMapsScraper(headless=True)

            # Clear any previous data
            scraper.data = []

            # Run the scraper
            scraper.run_scraper(
                query=company_name,
                location=location,
            )

            return scraper.data

        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}")
            raise e
        finally:
            if scraper:
                try:
                    scraper.close()
                except Exception as cleanup_error:
                    logger.warning(f"Error during cleanup: {cleanup_error}")


def validate_scrape_request(data):
    """
    Validate the scrape request data

    Args:
        data (dict): Request data

    Returns:
        tuple: (company_name, location)

    """
    if not data:
        raise BadRequest("Request body is required")

    company_name = data.get("company_name", "").strip()
    if not company_name:
        raise BadRequest("company_name is required and cannot be empty")

    location = data.get("location", "").strip() or None
    return company_name, location


def validate_get_people_request(data):
    """
    Validate the get-connected-people request data from a JSON body
    """
    if not data:
        raise BadRequest("Request body is required")

    company_id = data.get("company_id")
    if not company_id:
        raise BadRequest("'company_id' is a required field in the request body")

    domain = data.get("domain")  # Domain is now optional for the fallback

    limit = data.get("limit")
    if limit is not None:
        if not isinstance(limit, int):
            raise BadRequest("limit must be an integer")
        if limit > 100:
            logger.warning(
                f"Requested limit {limit} exceeds max of 100. Setting limit to 100."
            )
            limit = 100

    return company_id, domain, limit


@app.route("/status", methods=["GET"])
def status_check():
    """Status check endpoint"""
    return (
        jsonify(
            {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
        ),
        200,
    )


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for nginx"""
    return (
        jsonify(
            {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
        ),
        200,
    )


@app.route("/get-map-links", methods=["POST"])
def scrape_business_endpoint():
    """
    Scrape business data from Google Maps

    Request Body:
    {
        "company_name": "string (required)",
        "location": "string (optional)",
    }

    Response:
    {
        "data": [...],
        "meta": {
            "count": 1,
            "execution_time": 25.5,
            "timestamp": "2025-08-13T23:00:00"
        }
    }
    """
    start_time = time.time()

    try:
        if not request.is_json:
            raise BadRequest("Content-Type must be application/json")

        request_data = request.get_json()
        company_name, location = validate_scrape_request(request_data)

        logger.info(f"Scraping request: {company_name} in {location}")

        business_data = ScraperService.scrape_business(
            company_name=company_name,
            location=location,
        )

        execution_time = round(time.time() - start_time, 2)

        # Build response
        response = {
            "data": business_data,
            "meta": {
                "count": len(business_data),
                "execution_time": execution_time,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "query": {
                    "company_name": company_name,
                    "location": location,
                },
            },
        }

        logger.info(
            f"Scraping completed: {len(business_data)} results in {execution_time}s"
        )
        return jsonify(response), 200

    except BadRequest as e:
        logger.warning(f"Bad request: {str(e)}")
        return (
            jsonify(
                {
                    "error": {"type": "validation_error", "message": str(e)},
                    "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
                }
            ),
            400,
        )

    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        logger.error(traceback.format_exc())

        return (
            jsonify(
                {
                    "error": {
                        "type": "internal_error",
                        "message": "An error occurred while processing your request",
                    },
                    "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
                }
            ),
            500,
        )


@app.route("/get-connected-people", methods=["POST"])
def get_connected_people_endpoint():
    """
    Get connected people data from Lead411, with Apollo.io as a fallback.

    Request Body:
    {
        "company_id": "integer (required)",
        "domain": "string (optional, for Apollo.io fallback)",
        "limit": "integer (optional)"
    }
    """
    start_time = time.time()

    try:
        if not request.is_json:
            raise BadRequest("Content-Type must be application/json")

        request_data = request.get_json()
        company_id, domain, limit = validate_get_people_request(request_data)

        logger.info(
            f"Request for connected people: company_id={company_id}, domain={domain}, limit={limit}"
        )

        people_data = connected_people_service.get_connected_people(
            company_id=company_id,
            domain=domain,
            limit=limit,
        )

        execution_time = round(time.time() - start_time, 2)

        # Build response
        response = {
            "data": people_data,
            "meta": {
                "count": len(people_data),
                "execution_time": execution_time,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "query": {
                    "company_id": company_id,
                    "domain": domain,
                    "limit": limit,
                },
            },
        }

        logger.info(
            f"Request completed: {len(people_data)} results in {execution_time}s"
        )
        return jsonify(response), 200

    except BadRequest as e:
        logger.warning(f"Bad request: {str(e)}")
        return (
            jsonify(
                {
                    "error": {"type": "validation_error", "message": str(e)},
                    "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
                }
            ),
            400,
        )

    except Exception as e:
        logger.error(f"Internal error: {str(e)}")
        logger.error(traceback.format_exc())

        return (
            jsonify(
                {
                    "error": {
                        "type": "internal_error",
                        "message": "An error occurred while processing your request",
                    },
                    "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
                }
            ),
            500,
        )


@app.route("/get-competitors", methods=["POST"])
def get_competitors():
    """
    Request Body:
    {
        "target_company_id": 8073,
        "range": 10,
        "top_n": 10
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        target_company_id = data.get("target_company_id")
        if not target_company_id:
            return jsonify({"error": "target_company_id is a required field"}), 400
        
        range_param = data.get("range", 10)
        top_n = data.get("top_n", 10)

        app.logger.info(f"🔐 Authenticating with Growjo API...")
        token = token_growjo_api()
        if not token:
            return jsonify({"error": "Failed to authenticate with Growjo API"}), 401

        target_company_detail = get_target_company_detail(
            token=token, target_company_id=target_company_id
        )
        if not target_company_detail:
            return jsonify({"error": "Failed to retrieve target company details"}), 404
        
        target_company_name = target_company_detail.get("name")
        target_company_city = target_company_detail.get("city")
        target_sic_code = target_company_detail.get("sic_code")
        
        if not all([target_company_name, target_company_city, target_sic_code]):
            return jsonify({"error": "Incomplete company data from Growjo (missing name, city, or sic_code)"}), 404

        app.logger.info(f"🔍 Searching companies in {target_company_city}")
        competitor_company_ids = filter_company_id(
            token=token,
            SIC_Codes=target_sic_code,
            city=target_company_city,
            range=range_param,
        )

        if not competitor_company_ids:
            return (
                jsonify({
                    "error": f"No companies found in {target_company_city} with SIC code {target_sic_code}"
                }),
                404,
            )

        app.logger.info(f"📋 Found {len(competitor_company_ids)} company IDs")

        app.logger.info(f"📤 Fetching company details...")
        competitor_company_details = get_company_detail(token, competitor_company_ids)
        if not competitor_company_details:
            return jsonify({"error": "Failed to fetch company details"}), 500

        app.logger.info(f"✅ Successfully fetched {len(competitor_company_details)} company details")
        
        all_company_details = [target_company_detail["result"]] + competitor_company_details
        formatted_data = {"company_details": all_company_details}

        app.logger.info(f"🔄 Running competitor analysis pipeline...")
        pipeline_result = run_competitor_pipeline(
            growjo_data=formatted_data,
            target_company_name=target_company_name,
            target_city=target_company_city,
            top_n=top_n,
        )

        if "error" in pipeline_result:
            return jsonify(pipeline_result), 404

        pipeline_result["metadata"] = {
            "total_companies_analyzed": len(competitor_company_details),
            "SIC_Code": target_sic_code,
            "search_range": range_param,
            "processing_time": datetime.now().isoformat(),
        }

        app.logger.info(f"✅ Analysis completed successfully!")
        return jsonify(pipeline_result), 200

    except Exception as e:
        app.logger.error(f"❌ Error in competitor analysis: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return (
        jsonify(
            {
                "error": {
                    "type": "not_found",
                    "message": "The requested endpoint was not found",
                },
                "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
            }
        ),
        404,
    )


@app.route("/get-growth-trends", methods=["POST"])
def growth():
    try:
        data = request.get_json()
        
        if not data or "results" not in data or not isinstance(data["results"], list):
            return jsonify({"error": "Payload must contain 'results' as a list"}), 400

        app.logger.info(f"Received growth-trends payload: {data}")
        
        company_name = data["results"][0]["company"]

        # Authenticate with Growjo API
        app.logger.info(f"🔐 Authenticating with Growjo API...")
        token = gt_token_growjo_api()

        company_id = data["results"][0].get("company_id")

        company_detail = gt_get_company_detail(token, company_id)

        data["results"][0]["company_detail"] = company_detail

        # Analyze growth trends
        app.logger.info(f"📈 Analyzing growth trends for {company_name}...")
        growth_analysis = asyncio.run(analyze_growth_trends(data))

        return (
            jsonify(
                growth_analysis
            ),
            200,
        )
    except Exception as e:
        app.logger.error(f"Error in /growth-trends: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return (
        jsonify(
            {
                "error": {
                    "type": "method_not_allowed",
                    "message": "The requested method is not allowed for this endpoint",
                },
                "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
            }
        ),
        405,
    )


@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return (
        jsonify(
            {
                "error": {
                    "type": "internal_error",
                    "message": "An internal server error occurred",
                },
                "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
            }
        ),
        500,
    )
    
    
# =============================================================================
# Company Review API Endpoint 
# =============================================================================
import asyncio
from service.company_review.company_reviews import process_company_data

@app.route('/get-company-reviews/', methods=['POST'])
def get_company_review():
    """
    Accepts a company's details, runs the full analysis, and returns
    the complete report in a single response.
    """
    data = request.get_json()
    if not data or 'company_name' not in data:
        return jsonify({"error": "company_name is a required field"}), 400

    # DEBUG: Log when the endpoint is called
    logger.info(f"🔍 DEBUG: Company reviews endpoint called for company: {data.get('company_name')}")
    logger.info(f"🔍 DEBUG: RAPIDAPI_KEY available: {'YES' if os.getenv('RAPIDAPI_KEY') else 'NO'}")
    if os.getenv('RAPIDAPI_KEY'):
        rapid_key = os.getenv('RAPIDAPI_KEY')
        logger.info(f"🔍 DEBUG: RAPIDAPI_KEY value: {rapid_key[:10]}...{rapid_key[-4:] if len(rapid_key) > 14 else 'SHORT'}")
    else:
        logger.info("🔍 DEBUG: RAPIDAPI_KEY not found in environment")

    try:
        final_report = asyncio.run(process_company_data(
            data.get('company_name'),
            data.get('location'),
            data.get('website')
        ))
        
        return jsonify(final_report), 200

    except Exception as e:
        logger.error(f"An error occurred in the company review process: {str(e)}")
        logger.error(traceback.format_exc())
        
        return jsonify({"error": "An internal error occurred during analysis."}), 500



if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    port = int(os.getenv("FLASK_PORT", 5003))
    host = os.getenv("FLASK_HOST", "0.0.0.0")

    logger.info(f"Starting Flask API on {host}:{port} (debug={debug})")

    app.run(host=host, port=port, debug=debug)
    
    
