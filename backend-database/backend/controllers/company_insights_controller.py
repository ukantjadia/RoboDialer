from models.lead_model import db, Lead
from models.company_insights_model import CompanyInsights
from flask import current_app
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime

class CompanyInsightsController:

    @staticmethod
    def store_feature_data(user_id, lead_id, feature_name, data):
        """
        Store data for a specific feature (ai_insights, competitors, growth_trends, reviews, maps)
        """
        try:
            current_app.logger.info(f"Storing {feature_name} data for user {user_id}, lead {lead_id}")

            # Check if lead exists
            lead = Lead.query.filter_by(lead_id=lead_id, deleted=False).first()
            if not lead:
                current_app.logger.warning(f"Lead {lead_id} not found for user {user_id}")
                return False, "Lead not found"

            # Find existing insights record or create new one
            insights = CompanyInsights.query.filter_by(user_id=user_id, lead_id=lead_id).first()

            if not insights:
                insights = CompanyInsights(user_id=user_id, lead_id=lead_id)
                db.session.add(insights)
                current_app.logger.info(f"Created new insights record for user {user_id}, lead {lead_id}")

            # Update the specific feature data
            if insights.update_feature_data(feature_name, data):
                flag_modified(insights, feature_name)
                db.session.commit()
                current_app.logger.info(f"Successfully stored {feature_name} data for user {user_id}, lead {lead_id}")
                return True, insights.to_dict()
            else:
                current_app.logger.error(f"Invalid feature name: {feature_name}")
                return False, "Invalid feature name"

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error storing {feature_name} data for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_feature_data(user_id, lead_id, feature_name):
        """
        Get data for a specific feature
        """
        try:
            current_app.logger.info(f"Retrieving {feature_name} data for user {user_id}, lead {lead_id}")

            insights = CompanyInsights.query.filter_by(user_id=user_id, lead_id=lead_id).first()

            if not insights:
                current_app.logger.info(f"No insights record found for user {user_id}, lead {lead_id}")
                return False, "No insights data available for this lead"

            feature_data = getattr(insights, feature_name, None)

            if feature_data is None:
                current_app.logger.info(f"No {feature_name} data available for user {user_id}, lead {lead_id}")
                return False, f"No {feature_name} data available"

            current_app.logger.info(f"Successfully retrieved {feature_name} data for user {user_id}, lead {lead_id}")
            return True, {
                'feature_data': feature_data,
                'last_updated': insights.last_updated.isoformat() if insights.last_updated else None,
                'is_completed': insights.is_completed
            }

        except Exception as e:
            current_app.logger.error(f"Error retrieving {feature_name} data for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_all_insights(user_id, lead_id):
        """
        Get all insights data for a lead
        """
        try:
            current_app.logger.info(f"Retrieving all insights data for user {user_id}, lead {lead_id}")

            insights = CompanyInsights.query.filter_by(user_id=user_id, lead_id=lead_id).first()

            if not insights:
                current_app.logger.info(f"No insights record found for user {user_id}, lead {lead_id}")
                return False, "No insights data available for this lead"

            current_app.logger.info(f"Successfully retrieved all insights data for user {user_id}, lead {lead_id}")
            return True, insights.to_dict()

        except Exception as e:
            current_app.logger.error(f"Error retrieving all insights data for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def check_lead_access(user_id, lead_id):
        """
        Check if user has access to the lead (lead exists and is not deleted)
        """
        try:
            lead = Lead.query.filter_by(lead_id=lead_id, deleted=False).first()
            if not lead:
                current_app.logger.warning(f"Lead {lead_id} not found or deleted for user {user_id}")
                return False, "Lead not found or access denied"
            return True, "Access granted"
        except Exception as e:
            current_app.logger.error(f"Error checking lead access for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)
