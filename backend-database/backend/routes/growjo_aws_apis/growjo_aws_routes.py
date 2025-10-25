from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from config.config import config
import re

# Create blueprint
growjo_aws_bp = Blueprint('growjo_aws', __name__, url_prefix='/api/growjo')

# Initialize DynamoDB from config
dynamodb = boto3.resource(
    'dynamodb',
    region_name=config.AWS_REGION,
)

table = dynamodb.Table(config.DYNAMODB_TABLE_NAME)

# 'company', 'industry', 'street', 'city', 'state','bbb_rating', 'company_phone', 'website', 'country'
# Define which fields from the Growjo source we want to return to clients
ALLOWED_GROWJO_FIELDS = {
    'company_id',
    'company_name',
    'Industry',
    'industry_loc',
    'city',
    'region_code',  # state/region
    'country_code',
    'zip',
    # 'zip_uk',
    'address1',
    'address2',
    'phone',
    'url',  # website
    # 'linkedin_url',
    # 'facebook_url',
    # 'twitter',
    # 'employee_number',
    # 'number_of_employees_range',
    # 'revenue_range',
}


def _filter_growjo_item_fields(item: dict) -> dict:
    """Return only the allowed subset of fields from a Growjo item."""
    if not isinstance(item, dict):
        return {}
    return {key: item.get(key) for key in ALLOWED_GROWJO_FIELDS if key in item}

@growjo_aws_bp.route('/companies', methods=['POST'])
def get_companies_by_batch():
    """
    Get companies by batch of company names

    Returns complete entries for each company name provided
    """
    try:
        data = request.get_json()

        if not data or 'company_names' not in data:
            return jsonify({
                'success': False,
                'message': 'Company names list is required',
                'timestamp': datetime.now().isoformat()
            }), 400

        company_names = data['company_names']

        if not company_names:
            return jsonify({
                'success': False,
                'message': 'Company names list cannot be empty',
                'timestamp': datetime.now().isoformat()
            }), 400

        if len(company_names) > 100:
            return jsonify({
                'success': False,
                'message': 'Maximum 100 company names allowed per request',
                'timestamp': datetime.now().isoformat()
            }), 400

        results = []

        for company_name in company_names:
            try:
                # Query by company_name (partition key)
                response = table.query(
                    KeyConditionExpression='company_name = :company_name',
                    ExpressionAttributeValues={
                        ':company_name': company_name
                    }
                )

                items = response.get('Items', [])
                filtered_items = [_filter_growjo_item_fields(i) for i in items]

                results.append({
                    'company_name': company_name,
                    'items': filtered_items,
                    'count': len(filtered_items)
                })

            except Exception as e:
                # If individual company query fails, add error info but continue
                results.append({
                    'company_name': company_name,
                    'items': [],
                    'count': 0
                })

        return jsonify({
            'success': True,
            'message': f'Successfully queried {len(company_names)} companies',
            'company_batch_results': results,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@growjo_aws_bp.route('/industry-location', methods=['POST'])
def get_companies_by_industry_location():
    """
    Get companies by industry_location using GSI

    Expected payload: {"industry":"Software & Internet Services","location":"Chicago Loop, IL, USA"}
    Returns complete entries for the specified industry_location
    """
    try:
        data = request.get_json()

        if not data or 'industry' not in data or 'location' not in data:
            return jsonify({
                'success': False,
                'message': 'Both industry and location are required',
                'timestamp': datetime.now().isoformat()
            }), 400

        industry = data['industry']
        location = data['location']

        if not industry or not location:
            return jsonify({
                'success': False,
                'message': 'Industry and location cannot be empty',
                'timestamp': datetime.now().isoformat()
            }), 400

        # Parse location string (e.g., "Chicago Loop, IL, USA")
        location_parts = [part.strip() for part in location.split(',')]

        if len(location_parts) < 2:
            return jsonify({
                'success': False,
                'message': 'Location must be in format: "City, State, Country"',
                'timestamp': datetime.now().isoformat()
            }), 400

        city = location_parts[0]
        state = location_parts[1] if len(location_parts) > 1 else ""
        country = location_parts[2] if len(location_parts) > 2 else ""

        # Convert country to country code (USA -> US)
        if country.upper() == "USA":
            country = "US"


        # Sanitize city name (replace spaces with underscores for multi-word cities)
        city_clean = city.replace(" ", "_")

        # Build industry_loc format matching your script: industry_country_region_city
        # Sanitize industry name using regex: replace & with /, clean spaces around /, then replace remaining spaces with underscores
        # Step 1: Replace & with /
        industry_clean = industry.replace("&", "/")

        # Step 2: Remove trailing and leading spaces around / using regex
        industry_clean = re.sub(r'\s*/\s*', '/', industry_clean)

        # Step 3: Replace remaining spaces with underscores (handles double spaces as single underscore)
        industry_clean = re.sub(r'\s+', '_', industry_clean)

        # Step 4: Remove any remaining special characters and clean up
        industry_clean = industry_clean.replace("#", "_").strip()

        # Build the industry_loc string in the format expected by your DynamoDB index
        industry_loc = f"{industry_clean}_{country}_{state}_{city_clean}"

        current_app.logger.info(f"Converted payload to industry_loc: {industry_loc}")

        try:
            # Query using GSI (industry_loc-company_id-index)
            response = table.query(
                IndexName='industry_loc-company_id-index',
                KeyConditionExpression='industry_loc = :industry_loc',
                ExpressionAttributeValues={
                    ':industry_loc': industry_loc
                }
            )

            items = response.get('Items', [])
            filtered_items = [_filter_growjo_item_fields(i) for i in items]

            return jsonify({
                'success': True,
                'message': f'Found {len(filtered_items)} companies for industry_location: {industry_loc}',
                'industry_location_results': {
                    'original_payload': {
                        'industry': industry,
                        'location': location
                    },
                    'converted_industry_loc': industry_loc,
                    'items': filtered_items,
                    'count': len(filtered_items)
                },
                'timestamp': datetime.now().isoformat()
            })

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            # Check if the GSI doesn't exist - this is a server configuration issue
            if 'does not have the specified index' in error_message:
                return jsonify({
                    'success': False,
                    'message': 'Server configuration error: Required database index not found',
                    'timestamp': datetime.now().isoformat()
                }), 500

            # Check if the industry location doesn't exist
            elif error_code == 'ResourceNotFoundException':
                return jsonify({
                    'success': False,
                    'message': f'Industry location "{industry_loc}" not found',
                    'timestamp': datetime.now().isoformat()
                }), 404

            # Check for validation errors
            elif error_code == 'ValidationException':
                return jsonify({
                    'success': False,
                    'message': f'Invalid industry location format: {industry_loc}',
                    'timestamp': datetime.now().isoformat()
                }), 400

            # Any other AWS errors should be treated as server errors
            else:
                return jsonify({
                    'success': False,
                    'message': 'Server error: Database query failed',
                    'timestamp': datetime.now().isoformat()
                }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@growjo_aws_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for DynamoDB connectivity"""
    try:
        # Test DynamoDB connection
        table_status = table.table_status
        item_count = table.item_count

        return jsonify({
            'success': True,
            'message': 'DynamoDB connection healthy',
            'data': {
                'table_status': table_status,
                'item_count': item_count,
                'table_name': table.name,
                'region': table.meta.client.meta.region_name,
                'config_source': 'config_file',
                'aws_region': config.AWS_REGION,
                'table_name_config': config.DYNAMODB_TABLE_NAME
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Health check failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


# -------------------------
# Non-route helper methods
# -------------------------
def growjo_query_companies_by_names(company_names):
    """Helper: query Growjo table for a list of company names. Returns filtered items per name.

    Returns list of dicts: [{company_name, items, count}, ...]
    """
    try:
        if not company_names:
            return []
        results = []
        for company_name in company_names:
            try:
                resp = table.query(
                    KeyConditionExpression='company_name = :company_name',
                    ExpressionAttributeValues={
                        ':company_name': company_name
                    }
                )
                items = resp.get('Items', [])
                filtered_items = [_filter_growjo_item_fields(i) for i in items]
                results.append({
                    'company_name': company_name,
                    'items': filtered_items,
                    'count': len(filtered_items)
                })
            except Exception:
                results.append({'company_name': company_name, 'items': [], 'count': 0})
        return results
    except Exception:
        return []


def growjo_query_by_industry_location(industry: str, location: str):
    """Helper: query by industry and location string "City, State, Country" via industry_loc GSI.

    Returns dict with converted key and filtered items, mimicking the route shape.
    """
    try:
        if not industry or not location:
            return {'converted_industry_loc': None, 'items': [], 'count': 0}

        parts = [part.strip() for part in location.split(',')]
        if len(parts) < 2:
            return {'converted_industry_loc': None, 'items': [], 'count': 0}

        city = parts[0]
        state = parts[1] if len(parts) > 1 else ''
        country = parts[2] if len(parts) > 2 else ''

        if country.upper() == 'USA':
            country = 'US'

        city_clean = city.replace(' ', '_')
        industry_clean = industry.replace('&', '/')
        industry_clean = re.sub(r'\s*/\s*', '/', industry_clean)
        industry_clean = re.sub(r'\s+', '_', industry_clean)
        industry_clean = industry_clean.replace('#', '_').strip()

        industry_loc = f"{industry_clean}_{country}_{state}_{city_clean}"

        resp = table.query(
            IndexName='industry_loc-company_id-index',
            KeyConditionExpression='industry_loc = :industry_loc',
            ExpressionAttributeValues={
                ':industry_loc': industry_loc
            }
        )
        items = resp.get('Items', [])
        filtered_items = [_filter_growjo_item_fields(i) for i in items]
        return {
            'converted_industry_loc': industry_loc,
            'items': filtered_items,
            'count': len(filtered_items)
        }
    except Exception:
        return {'converted_industry_loc': None, 'items': [], 'count': 0}