## ======= PRODUCTION VERSION =======
from flask import Flask, jsonify, request
import asyncio
import aiohttp
import logging
import socket
import re  # Import the regular expression module
from email_phone_api.email_validator_phone import EmailValidator, PhoneValidator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    return response

@app.route("/health", methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "phone-email-validator"}), 200

async def validate_email_async(email):
    loop = asyncio.get_event_loop()
    validator = EmailValidator()
    result = await loop.run_in_executor(None, validator.validate_email, email, False, True)
    return result

async def validate_phone_async(phone_number):
    loop = asyncio.get_event_loop()
    validator = PhoneValidator()
    result = await loop.run_in_executor(None, validator.phone_validate, phone_number)
    return result

@app.route("/validate_email", methods=['POST'])
async def check_mail_validity():
    # Bulk validation from file
    if "file" in request.files:
        file = request.files["file"]
        content = file.read()
        filename = file.filename
        email_validator = EmailValidator()
        try:
            result = email_validator.bulk_validate_from_file(content, filename)
            return jsonify({"bulk_email_results": result}), 200
        except Exception as e:
            logger.error(f"Bulk email validation failed: {e}")
            return jsonify({"error": "Failed bulk email validation"}), 500

    # JSON payload validation
    request_data = request.get_json()
    if not request_data:
        return jsonify({"error": "No data provided."}), 400

    # Check for bulk email validation
    if "emails" in request_data and isinstance(request_data["emails"], list):
        emails = request_data["emails"]
        if not emails:
            return jsonify({"error": "Email list is empty."}), 400
        
        email_validator = EmailValidator()
        results = []
        for email in emails:
            try:
                result = await validate_email_async(email)
                results.append(result)
            except Exception as e:
                logger.error(f"Error validating email {email}: {e}")
                results.append({"email": email, "active": False, "error": str(e)})
        
        return jsonify({"bulk_email_results": results}), 200

    # Single email validation
    email = request_data.get("email")
    print(email)    
    if not email:
        return jsonify({"error": "Email is missing from the request."}), 400

    try:
        result = await validate_email_async(email)
        print(result)
        return jsonify({"email_result": result}), 200
    except Exception as e:
        logger.error(f"Error validating email: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route("/validate_phone", methods=["POST"])
async def check_phone_validity():
    # Bulk validation from file
    if "file" in request.files:
        file = request.files["file"]
        content = file.read()
        phone_validator = PhoneValidator()
        try:
            result = phone_validator.bulk_validate_from_csv(content)
            return jsonify({"bulk_phone_results": result}), 200
        except Exception as e:
            logger.error(f"Bulk phone validation failed: {e}")
            return jsonify({"error": "Failed bulk phone validation"}), 500

    # JSON payload validation
    request_data = request.get_json()
    if not request_data:
        return jsonify({"error": "No data provided."}), 400

    # Check for bulk phone validation
    if "phones" in request_data and isinstance(request_data["phones"], list):
        phones = request_data["phones"]
        if not phones:
            return jsonify({"error": "Phone list is empty."}), 400
        
        phone_validator = PhoneValidator()
        results = []
        for phone in phones:
            try:
                # Sanitize the phone number
                sanitized_phone = re.sub(r'[^0-9]', '', str(phone))
                if len(sanitized_phone) == 10:
                    formatted_phone = f"+1-{sanitized_phone[:3]}-{sanitized_phone[3:6]}-{sanitized_phone[6:]}"
                else:
                    formatted_phone = sanitized_phone
                
                result = await validate_phone_async(formatted_phone)
                results.append({
                    "phone": phone,
                    "formatted_phone": formatted_phone,
                    "validation": result
                })
            except Exception as e:
                logger.error(f"Error validating phone {phone}: {e}")
                results.append({"phone": phone, "validation": {"error": str(e)}})
        
        return jsonify({"bulk_phone_results": results}), 200

    # Single phone validation
    phone_number = request_data.get("phone")

    if not phone_number:
        return jsonify({"error": "Phone number is missing from the request."}), 400

    # Sanitize the phone number to remove non-numeric characters
    sanitized_phone_number = re.sub(r'[^0-9]', '', phone_number)
    
    # Check if it's a 10-digit number and format it to '+1-XXX-XXX-XXXX'
    if len(sanitized_phone_number) == 10:
        formatted_phone_number = f"+1-{sanitized_phone_number[:3]}-{sanitized_phone_number[3:6]}-{sanitized_phone_number[6:]}"
    else:
        # If it's not a 10-digit number, use the sanitized version for validation
        formatted_phone_number = sanitized_phone_number

    try:
        result = await validate_phone_async(formatted_phone_number)
        return jsonify({"phone_result": result})
    except Exception as e:
        logger.error(f"Error validating phone number: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

if __name__ == "__main__":
    # Production settings - handled by nginx/gunicorn
    app.run(host='0.0.0.0', port=5002, debug=False)

## ======= LOCAL TESTING VERSION =======
# from flask import Flask, jsonify, request
# import asyncio
# import aiohttp
# import logging
# import socket
# import re  # Import the regular expression module
# from email_phone_api.email_validator_phone import EmailValidator, PhoneValidator

# # Setup logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# app = Flask(__name__)


# @app.after_request
# def add_cors_headers(response):
#     response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
#     response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
#     response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
#     response.headers['Access-Control-Allow-Credentials'] = 'true'
#     return response

# # Handle OPTIONS requests for CORS preflight
# @app.route("/validate_email", methods=['OPTIONS'])
# @app.route("/validate_phone", methods=['OPTIONS'])
# def handle_options():
#     response = jsonify({'status': 'ok'})
#     response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
#     response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
#     response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
#     response.headers['Access-Control-Allow-Credentials'] = 'true'
#     return response

# # General OPTIONS handler for any route
# @app.route("/", defaults={'path': ''}, methods=['OPTIONS'])
# @app.route("/<path:path>", methods=['OPTIONS'])
# def handle_all_options(path):
#     response = jsonify({'status': 'ok'})
#     response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
#     response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
#     response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
#     response.headers['Access-Control-Allow-Credentials'] = 'true'
#     return response

# async def validate_email_async(email):
#     loop = asyncio.get_event_loop()
#     validator = EmailValidator()
#     result = await loop.run_in_executor(None, validator.validate_email, email, False, True)
#     return result

# async def validate_phone_async(phone_number):
#     loop = asyncio.get_event_loop()
#     validator = PhoneValidator()
#     result = await loop.run_in_executor(None, validator.phone_validate, phone_number)
#     return result

# @app.route("/validate_email", methods=['POST'])
# async def check_mail_validity():
#     # Bulk validation from file
#     if "file" in request.files:
#         file = request.files["file"]
#         content = file.read()
#         filename = file.filename
#         email_validator = EmailValidator()
#         try:
#             result = email_validator.bulk_validate_from_file(content, filename)
#             return jsonify({"bulk_email_results": result}), 200
#         except Exception as e:
#             logger.error(f"Bulk email validation failed: {e}")
#             return jsonify({"error": "Failed bulk email validation"}), 500

#     # JSON payload validation
#     request_data = request.get_json()
#     if not request_data:
#         return jsonify({"error": "No data provided."}), 400

#     # Check for bulk email validation
#     if "emails" in request_data and isinstance(request_data["emails"], list):
#         emails = request_data["emails"]
#         if not emails:
#             return jsonify({"error": "Email list is empty."}), 400
        
#         email_validator = EmailValidator()
#         results = []
#         for email in emails:
#             try:
#                 result = await validate_email_async(email)
#                 results.append(result)
#             except Exception as e:
#                 logger.error(f"Error validating email {email}: {e}")
#                 results.append({"email": email, "active": False, "error": str(e)})
        
#         return jsonify({"bulk_email_results": results}), 200

#     # Single email validation
#     email = request_data.get("email")
#     print(email)    
#     if not email:
#         return jsonify({"error": "Email is missing from the request."}), 400

#     try:
#         result = await validate_email_async(email)
#         print(result)
#         return jsonify({"email_result": result}), 200
#     except Exception as e:
#         logger.error(f"Error validating email: {e}")
#         return jsonify({"error": "An internal server error occurred."}), 500

# @app.route("/validate_phone", methods=["POST"])
# async def check_phone_validity():
#     # Bulk validation from file
#     if "file" in request.files:
#         file = request.files["file"]
#         content = file.read()
#         phone_validator = PhoneValidator()
#         try:
#             result = phone_validator.bulk_validate_from_csv(content)
#             return jsonify({"bulk_phone_results": result}), 200
#         except Exception as e:
#             logger.error(f"Bulk phone validation failed: {e}")
#             return jsonify({"error": "Failed bulk phone validation"}), 500

#     # JSON payload validation
#     request_data = request.get_json()
#     if not request_data:
#         return jsonify({"error": "No data provided."}), 400

#     # Check for bulk phone validation
#     if "phones" in request_data and isinstance(request_data["phones"], list):
#         phones = request_data["phones"]
#         if not phones:
#             return jsonify({"error": "Phone list is empty."}), 400
        
#         phone_validator = PhoneValidator()
#         results = []
#         for phone in phones:
#             try:
#                 # Sanitize the phone number
#                 sanitized_phone = re.sub(r'[^0-9]', '', str(phone))
#                 if len(sanitized_phone) == 10:
#                     formatted_phone = f"+1-{sanitized_phone[:3]}-{sanitized_phone[3:6]}-{sanitized_phone[6:]}"
#                 else:
#                     formatted_phone = sanitized_phone
                
#                 result = await validate_phone_async(formatted_phone)
#                 results.append({
#                     "phone": phone,
#                     "formatted_phone": formatted_phone,
#                     "validation": result
#                 })
#             except Exception as e:
#                 logger.error(f"Error validating phone {phone}: {e}")
#                 results.append({"phone": phone, "validation": {"error": str(e)}})
        
#         return jsonify({"bulk_phone_results": results}), 200

#     # Single phone validation
#     phone_number = request_data.get("phone")

#     if not phone_number:
#         return jsonify({"error": "Phone number is missing from the request."}), 400

#     # Sanitize the phone number to remove non-numeric characters
#     sanitized_phone_number = re.sub(r'[^0-9]', '', phone_number)
    
#     # Check if it's a 10-digit number and format it to '+1-XXX-XXX-XXXX'
#     if len(sanitized_phone_number) == 10:
#         formatted_phone_number = f"+1-{sanitized_phone_number[:3]}-{sanitized_phone_number[3:6]}-{sanitized_phone_number[6:]}"
#     else:
#         # If it's not a 10-digit number, use the sanitized version for validation
#         formatted_phone_number = sanitized_phone_number

#     try:
#         result = await validate_phone_async(formatted_phone_number)
#         return jsonify({"phone_result": result})
#     except Exception as e:
#         logger.error(f"Error validating phone number: {e}")
#         return jsonify({"error": "An internal server error occurred."}), 500

# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5002, debug=True)
