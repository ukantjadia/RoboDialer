from models.contact_verification.contact_verification_model import ContactVerification, db
from models.lead_model import Lead
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class ContactVerificationController:
    """Controller for handling contact verification operations"""

    @staticmethod
    def _normalize_phone_for_compare(phone_value):
        """Return only digits for robust phone comparisons (ignores '+', spaces, dashes, etc)."""
        if phone_value is None:
            return ''
        value_str = str(phone_value)
        return ''.join(ch for ch in value_str if ch.isdigit())

    # ==================== LEAD-ASSOCIATED METHODS (EXISTING) ====================

    @staticmethod
    def store_email_verification(lead_id, email, verification_data):
        """
        Store email verification data for a lead
        Returns: (success, message)
        """
        current_app.logger.info(f'[Contact Verification Controller] Storing email verification for lead: {lead_id}, email: {email}')

        try:
            # Validate lead exists
            lead = Lead.query.filter_by(lead_id=lead_id, deleted=False).first()
            if not lead:
                current_app.logger.warning(f'[Contact Verification Controller] Lead not found: {lead_id}')
                return False, "Lead not found"

            # Validate email
            if not email:
                current_app.logger.warning(f'[Contact Verification Controller] Email is required')
                return False, "Email is required"

            # Store verification data
            verification = ContactVerification.create_or_update_verification(
                lead_id=lead_id,
                contact_type='email',
                contact_value=email,
                verification_data=verification_data
            )

            current_app.logger.info(f'[Contact Verification Controller] Successfully stored email verification: {verification.id}')
            return True, "Email verification stored successfully"

        except Exception as e:
            current_app.logger.error(f'[Contact Verification Controller] Error storing email verification: {str(e)}')
            return False, "Internal server error"

    @staticmethod
    def store_phone_verification(lead_id, phone, verification_data):
        """
        Store phone verification data for a lead
        Returns: (success, message)
        """
        current_app.logger.info(f'[Contact Verification Controller] Storing phone verification for lead: {lead_id}, phone: {phone}')

        try:
            # Validate lead exists
            lead = Lead.query.filter_by(lead_id=lead_id, deleted=False).first()
            if not lead:
                current_app.logger.warning(f'[Contact Verification Controller] Lead not found: {lead_id}')
                return False, "Lead not found"

            # Validate phone
            if not phone:
                current_app.logger.warning(f'[Contact Verification Controller] Phone is required')
                return False, "Phone is required"

            # Store verification data
            verification = ContactVerification.create_or_update_verification(
                lead_id=lead_id,
                contact_type='phone',
                contact_value=phone,
                verification_data=verification_data
            )

            current_app.logger.info(f'[Contact Verification Controller] Successfully stored phone verification: {verification.id}')
            return True, "Phone verification stored successfully"

        except Exception as e:
            current_app.logger.error(f'[Contact Verification Controller] Error storing phone verification: {str(e)}')
            return False, "Internal server error"

    @staticmethod
    def get_verification(lead_id, contact_type, contact_value):
        """
        Get verification for a specific contact (lead-associated)
        Returns: (success, message, data, found)
        """
        current_app.logger.info(f'[Contact Verification Controller] Getting verification for lead: {lead_id}, type: {contact_type}, value: {contact_value}')

        try:
            # Validate lead exists
            lead = Lead.query.filter_by(lead_id=lead_id, deleted=False).first()
            if not lead:
                current_app.logger.warning(f'[Contact Verification Controller] Lead not found: {lead_id}')
                return False, "Lead not found", None, False

            # Validate contact_type
            if contact_type not in ['phone', 'email']:
                current_app.logger.warning(f'[Contact Verification Controller] Invalid contact type: {contact_type}')
                return False, "Invalid contact type. Must be 'phone' or 'email'", None, False

            # Exact match first
            verification = ContactVerification.find_verification(lead_id, contact_type, contact_value)

            if verification:
                current_app.logger.info(f'[Contact Verification Controller] Verification found: {verification.id}')
                return True, "Verification found", verification.to_dict(), True

            # Fallback for phone: compare by digits-only to handle '+', spaces, dashes, etc.
            if contact_type == 'phone' and contact_value:
                normalized_query = ContactVerificationController._normalize_phone_for_compare(contact_value)
                current_app.logger.info('[Contact Verification Controller] Exact match not found, trying normalized phone lookup')
                candidates = ContactVerification.query.filter_by(
                    lead_id=lead_id,
                    contact_type='phone',
                    validation_type='lead'
                ).all()
                for candidate in candidates:
                    if ContactVerificationController._normalize_phone_for_compare(candidate.contact_value) == normalized_query:
                        current_app.logger.info(f'[Contact Verification Controller] Normalized phone match found: {candidate.id}')
                        return True, "Verification found", candidate.to_dict(), True

            current_app.logger.info(f'[Contact Verification Controller] No verification found')
            return True, "No verification found", None, False

        except Exception as e:
            current_app.logger.error(f'[Contact Verification Controller] Error getting verification: {str(e)}')
            return False, "Internal server error", None, False

    @staticmethod
    def get_verification_history(lead_id):
        """
        Get verification history for a lead (lead-associated only)
        Returns: (success, message, data)
        """
        current_app.logger.info(f'[Contact Verification Controller] Getting verification history for lead: {lead_id}')

        try:
            # Validate lead exists
            lead = Lead.query.filter_by(lead_id=lead_id, deleted=False).first()
            if not lead:
                current_app.logger.warning(f'[Contact Verification Controller] Lead not found: {lead_id}')
                return False, "Lead not found", None

            # Get verification history
            verifications = ContactVerification.get_verification_history(lead_id)
            data = [verification.to_dict() for verification in verifications]

            current_app.logger.info(f'[Contact Verification Controller] Found {len(verifications)} verifications')
            return True, f"Found {len(verifications)} verifications", data

        except Exception as e:
            current_app.logger.error(f'[Contact Verification Controller] Error getting verification history: {str(e)}')
            return False, "Internal server error", None

    # ==================== STANDALONE METHODS (NEW) ====================

    @staticmethod
    def store_standalone_email_verification(user_id, email, verification_data):
        """
        Store standalone email verification data
        Returns: (success, message)
        """
        current_app.logger.info(f'[Contact Verification Controller] Storing standalone email verification for user: {user_id}, email: {email}')

        try:
            # Validate email
            if not email:
                current_app.logger.warning(f'[Contact Verification Controller] Email is required')
                return False, "Email is required"

            # Store verification data
            verification = ContactVerification.create_or_update_standalone_verification(
                user_id=user_id,
                contact_type='email',
                contact_value=email,
                verification_data=verification_data
            )

            current_app.logger.info(f'[Contact Verification Controller] Successfully stored standalone email verification: {verification.id}')
            return True, "Standalone email verification stored successfully"

        except Exception as e:
            current_app.logger.error(f'[Contact Verification Controller] Error storing standalone email verification: {str(e)}')
            return False, "Internal server error"

    @staticmethod
    def store_standalone_phone_verification(user_id, phone, verification_data):
        """
        Store standalone phone verification data
        Returns: (success, message)
        """
        current_app.logger.info(f'[Contact Verification Controller] Storing standalone phone verification for user: {user_id}, phone: {phone}')

        try:
            # Validate phone
            if not phone:
                current_app.logger.warning(f'[Contact Verification Controller] Phone is required')
                return False, "Phone is required"

            # Store verification data
            verification = ContactVerification.create_or_update_standalone_verification(
                user_id=user_id,
                contact_type='phone',
                contact_value=phone,
                verification_data=verification_data
            )

            current_app.logger.info(f'[Contact Verification Controller] Successfully stored standalone phone verification: {verification.id}')
            return True, "Standalone phone verification stored successfully"

        except Exception as e:
            current_app.logger.error(f'[Contact Verification Controller] Error storing standalone phone verification: {str(e)}')
            return False, "Internal server error"

    @staticmethod
    def get_standalone_verification(user_id, contact_type, contact_value):
        """
        Get standalone verification for a specific contact
        Returns: (success, message, data, found)
        """
        current_app.logger.info(f'[Contact Verification Controller] Getting standalone verification for user: {user_id}, type: {contact_type}, value: {contact_value}')

        try:
            # Validate contact_type
            if contact_type not in ['phone', 'email']:
                current_app.logger.warning(f'[Contact Verification Controller] Invalid contact type: {contact_type}')
                return False, "Invalid contact type. Must be 'phone' or 'email'", None, False

            # Exact match first
            verification = ContactVerification.find_standalone_verification(user_id, contact_type, contact_value)

            if verification:
                current_app.logger.info(f'[Contact Verification Controller] Standalone verification found: {verification.id}')
                return True, "Standalone verification found", verification.to_dict(), True

            # Fallback for phone: compare by digits-only to handle '+', spaces, dashes, etc.
            if contact_type == 'phone' and contact_value:
                normalized_query = ContactVerificationController._normalize_phone_for_compare(contact_value)
                current_app.logger.info('[Contact Verification Controller] Exact match not found, trying normalized phone lookup')
                candidates = ContactVerification.query.filter_by(
                    user_id=user_id,
                    contact_type='phone',
                    validation_type='standalone'
                ).all()
                for candidate in candidates:
                    if ContactVerificationController._normalize_phone_for_compare(candidate.contact_value) == normalized_query:
                        current_app.logger.info(f'[Contact Verification Controller] Normalized phone match found: {candidate.id}')
                        return True, "Standalone verification found", candidate.to_dict(), True

            current_app.logger.info(f'[Contact Verification Controller] No standalone verification found')
            return True, "No standalone verification found", None, False

        except Exception as e:
            current_app.logger.error(f'[Contact Verification Controller] Error getting standalone verification: {str(e)}')
            return False, "Internal server error", None, False

    @staticmethod
    def get_standalone_verification_history(user_id):
        """
        Get standalone verification history for a user
        Returns: (success, message, data)
        """
        current_app.logger.info(f'[Contact Verification Controller] Getting standalone verification history for user: {user_id}')

        try:
            # Get verification history
            verifications = ContactVerification.get_standalone_verification_history(user_id)
            data = [verification.to_dict() for verification in verifications]

            current_app.logger.info(f'[Contact Verification Controller] Found {len(verifications)} standalone verifications')
            return True, f"Found {len(verifications)} standalone verifications", data

        except Exception as e:
            current_app.logger.error(f'[Contact Verification Controller] Error getting standalone verification history: {str(e)}')
            return False, "Internal server error", None

    @staticmethod
    def validate_verification_data(data):
        """
        Validate the incoming verification data
        """
        current_app.logger.info(f'[Contact Verification Controller] Validating verification data')

        required_fields = ['verification_data']

        for field in required_fields:
            if field not in data:
                current_app.logger.warning(f'[Contact Verification Controller] Missing required field: {field}')
                return False, f"Missing required field: {field}"

        return True, None