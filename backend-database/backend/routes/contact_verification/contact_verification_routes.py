from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from controllers.contact_verification.contact_verification_controller import ContactVerificationController
import logging

logger = logging.getLogger(__name__)
contact_verification_bp = Blueprint('contact_verification_bp', __name__)

# ==================== LEAD-ASSOCIATED ROUTES (EXISTING) ====================

@contact_verification_bp.route('/api/contact_verification/email', methods=['POST'])
@login_required
def store_email_verification():
    """
    POST /api/contact_verification/email - Store email verification data for a lead

    Expected payload:
    {
        "lead_id": "string",
        "email": "string",
        "verification_data": "object"
    }
    """
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))
    current_app.logger.info(f'[Contact Verification] POST /api/contact_verification/email - User: {username} (ID: {user_id})')

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['lead_id', 'email', 'verification_data']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        lead_id = data.get('lead_id')
        email = data.get('email')
        verification_data = data.get('verification_data')

        # Store email verification
        success, message = ContactVerificationController.store_email_verification(
            lead_id=lead_id,
            email=email,
            verification_data=verification_data
        )

        if success:
            current_app.logger.info(f'[Contact Verification] Successfully stored email verification for lead: {lead_id}')
            return jsonify({"success": True, "message": message}), 200
        else:
            current_app.logger.error(f'[Contact Verification] Failed to store email verification: {message}')
            return jsonify({"error": message}), 400

    except Exception as e:
        current_app.logger.error(f'[Contact Verification] Unexpected error in store_email_verification: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@contact_verification_bp.route('/api/contact_verification/phone', methods=['POST'])
@login_required
def store_phone_verification():
    """
    POST /api/contact_verification/phone - Store phone verification data for a lead

    Expected payload:
    {
        "lead_id": "string",
        "phone": "string",
        "verification_data": "object"
    }
    """
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))
    current_app.logger.info(f'[Contact Verification] POST /api/contact_verification/phone - User: {username} (ID: {user_id})')

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['lead_id', 'phone', 'verification_data']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        lead_id = data.get('lead_id')
        phone = data.get('phone')
        verification_data = data.get('verification_data')

        # Store phone verification
        success, message = ContactVerificationController.store_phone_verification(
            lead_id=lead_id,
            phone=phone,
            verification_data=verification_data
        )

        if success:
            current_app.logger.info(f'[Contact Verification] Successfully stored phone verification for lead: {lead_id}')
            return jsonify({"success": True, "message": message}), 200
        else:
            current_app.logger.error(f'[Contact Verification] Failed to store phone verification: {message}')
            return jsonify({"error": message}), 400

    except Exception as e:
        current_app.logger.error(f'[Contact Verification] Unexpected error in store_phone_verification: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@contact_verification_bp.route('/api/contact_verification/<string:lead_id>', methods=['GET'])
@login_required
def get_verification(lead_id):
    """
    GET /api/contact_verification/<lead_id>?contact_type=email&contact_value=john@example.com
    Get verification for a specific contact (lead-associated)
    """
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))

    contact_type = request.args.get('contact_type')
    contact_value = request.args.get('contact_value')

    current_app.logger.info(f'[Contact Verification] GET /api/contact_verification/{lead_id} - User: {username} (ID: {user_id})')

    try:
        # Validate query parameters
        if not contact_type:
            return jsonify({"error": "contact_type parameter is required"}), 400
        if not contact_value:
            return jsonify({"error": "contact_value parameter is required"}), 400

        # Get verification
        success, message, data, found = ContactVerificationController.get_verification(
            lead_id=lead_id,
            contact_type=contact_type,
            contact_value=contact_value
        )

        if not success:
            return jsonify({"error": message}), 400

        response = {
            "success": True,
            "message": message,
            "found": found,
            "data": data
        }

        current_app.logger.info(f'[Contact Verification] Retrieved verification for lead: {lead_id}, found: {found}')
        return jsonify(response), 200

    except Exception as e:
        current_app.logger.error(f'[Contact Verification] Unexpected error in get_verification: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@contact_verification_bp.route('/api/contact_verification/history/<string:lead_id>', methods=['GET'])
@login_required
def get_verification_history(lead_id):
    """
    GET /api/contact_verification/history/<lead_id>
    Get verification history for a lead (lead-associated only)
    """
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))
    current_app.logger.info(f'[Contact Verification] GET /api/contact_verification/history/{lead_id} - User: {username} (ID: {user_id})')

    try:
        # Get verification history
        success, message, data = ContactVerificationController.get_verification_history(lead_id)

        if not success:
            return jsonify({"error": message}), 400

        response = {
            "success": True,
            "message": message,
            "lead_id": lead_id,
            "history": data
        }

        current_app.logger.info(f'[Contact Verification] Retrieved verification history for lead: {lead_id}')
        return jsonify(response), 200

    except Exception as e:
        current_app.logger.error(f'[Contact Verification] Unexpected error in get_verification_history: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

# ==================== STANDALONE ROUTES (NEW) ====================

@contact_verification_bp.route('/api/contact_verification/standalone/email', methods=['POST'])
@login_required
def store_standalone_email_verification():
    """
    POST /api/contact_verification/standalone/email - Store standalone email verification data

    Expected payload:
    {
        "email": "string",
        "verification_data": "object"
    }
    """
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))
    current_app.logger.info(f'[Contact Verification] POST /api/contact_verification/standalone/email - User: {username} (ID: {user_id})')

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['email', 'verification_data']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        email = data.get('email')
        verification_data = data.get('verification_data')

        # Store standalone email verification
        success, message = ContactVerificationController.store_standalone_email_verification(
            user_id=user_id,
            email=email,
            verification_data=verification_data
        )

        if success:
            current_app.logger.info(f'[Contact Verification] Successfully stored standalone email verification for user: {user_id}')
            return jsonify({"success": True, "message": message}), 200
        else:
            current_app.logger.error(f'[Contact Verification] Failed to store standalone email verification: {message}')
            return jsonify({"error": message}), 400

    except Exception as e:
        current_app.logger.error(f'[Contact Verification] Unexpected error in store_standalone_email_verification: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@contact_verification_bp.route('/api/contact_verification/standalone/phone', methods=['POST'])
@login_required
def store_standalone_phone_verification():
    """
    POST /api/contact_verification/standalone/phone - Store standalone phone verification data

    Expected payload:
    {
        "phone": "string",
        "verification_data": "object"
    }
    """
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))
    current_app.logger.info(f'[Contact Verification] POST /api/contact_verification/standalone/phone - User: {username} (ID: {user_id})')

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['phone', 'verification_data']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        phone = data.get('phone')
        verification_data = data.get('verification_data')

        # Store standalone phone verification
        success, message = ContactVerificationController.store_standalone_phone_verification(
            user_id=user_id,
            phone=phone,
            verification_data=verification_data
        )

        if success:
            current_app.logger.info(f'[Contact Verification] Successfully stored standalone phone verification for user: {user_id}')
            return jsonify({"success": True, "message": message}), 200
        else:
            current_app.logger.error(f'[Contact Verification] Failed to store standalone phone verification: {message}')
            return jsonify({"error": message}), 400

    except Exception as e:
        current_app.logger.error(f'[Contact Verification] Unexpected error in store_standalone_phone_verification: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@contact_verification_bp.route('/api/contact_verification/standalone/lookup', methods=['GET'])
@login_required
def get_standalone_verification():
    """
    GET /api/contact_verification/standalone/lookup?contact_type=email&contact_value=john@example.com
    Get standalone verification for a specific contact
    """
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))

    contact_type = request.args.get('contact_type')
    contact_value = request.args.get('contact_value')

    current_app.logger.info(f'[Contact Verification] GET /api/contact_verification/standalone/lookup - User: {username} (ID: {user_id})')

    try:
        # Validate query parameters
        if not contact_type:
            return jsonify({"error": "contact_type parameter is required"}), 400
        if not contact_value:
            return jsonify({"error": "contact_value parameter is required"}), 400

        # Get standalone verification
        success, message, data, found = ContactVerificationController.get_standalone_verification(
            user_id=user_id,
            contact_type=contact_type,
            contact_value=contact_value
        )

        if not success:
            return jsonify({"error": message}), 400

        response = {
            "success": True,
            "message": message,
            "found": found,
            "data": data
        }

        current_app.logger.info(f'[Contact Verification] Retrieved standalone verification for user: {user_id}, found: {found}')
        return jsonify(response), 200

    except Exception as e:
        current_app.logger.error(f'[Contact Verification] Unexpected error in get_standalone_verification: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@contact_verification_bp.route('/api/contact_verification/standalone/history', methods=['GET'])
@login_required
def get_standalone_verification_history():
    """
    GET /api/contact_verification/standalone/history
    Get standalone verification history for the current user
    """
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))
    current_app.logger.info(f'[Contact Verification] GET /api/contact_verification/standalone/history - User: {username} (ID: {user_id})')

    try:
        # Get standalone verification history
        success, message, data = ContactVerificationController.get_standalone_verification_history(user_id)

        if not success:
            return jsonify({"error": message}), 400

        response = {
            "success": True,
            "message": message,
            "user_id": str(user_id),
            "history": data
        }

        current_app.logger.info(f'[Contact Verification] Retrieved standalone verification history for user: {user_id}')
        return jsonify(response), 200

    except Exception as e:
        current_app.logger.error(f'[Contact Verification] Unexpected error in get_standalone_verification_history: {str(e)}', exc_info=True)
        return jsonify({"error": "Internal server error"}), 500