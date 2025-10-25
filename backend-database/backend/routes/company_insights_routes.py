from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from controllers.company_insights_controller import CompanyInsightsController

# Create blueprint
company_insights_bp = Blueprint('company_insights', __name__)

# Valid feature names
VALID_FEATURES = ['ai_insights', 'competitors', 'growth_trends', 'reviews', 'maps']

@company_insights_bp.route('/api/company-insights/ai-insights', methods=['POST'])
@login_required
def store_ai_insights():
    """Store AI insights data"""
    return _store_feature_data('ai_insights')

@company_insights_bp.route('/api/company-insights/ai-insights/<string:lead_id>', methods=['GET'])
@login_required
def get_ai_insights(lead_id):
    """Get AI insights data"""
    return _get_feature_data(lead_id, 'ai_insights')

@company_insights_bp.route('/api/company-insights/competitors', methods=['POST'])
@login_required
def store_competitors():
    """Store competitors data"""
    return _store_feature_data('competitors')

@company_insights_bp.route('/api/company-insights/competitors/<string:lead_id>', methods=['GET'])
@login_required
def get_competitors(lead_id):
    """Get competitors data"""
    return _get_feature_data(lead_id, 'competitors')

@company_insights_bp.route('/api/company-insights/growth-trends', methods=['POST'])
@login_required
def store_growth_trends():
    """Store growth trends data"""
    return _store_feature_data('growth_trends')

@company_insights_bp.route('/api/company-insights/growth-trends/<string:lead_id>', methods=['GET'])
@login_required
def get_growth_trends(lead_id):
    """Get growth trends data"""
    return _get_feature_data(lead_id, 'growth_trends')

@company_insights_bp.route('/api/company-insights/reviews', methods=['POST'])
@login_required
def store_reviews():
    """Store reviews data"""
    return _store_feature_data('reviews')

@company_insights_bp.route('/api/company-insights/reviews/<string:lead_id>', methods=['GET'])
@login_required
def get_reviews(lead_id):
    """Get reviews data"""
    return _get_feature_data(lead_id, 'reviews')

@company_insights_bp.route('/api/company-insights/maps', methods=['POST'])
@login_required
def store_maps():
    """Store maps data"""
    return _store_feature_data('maps')

@company_insights_bp.route('/api/company-insights/maps/<string:lead_id>', methods=['GET'])
@login_required
def get_maps(lead_id):
    """Get maps data"""
    return _get_feature_data(lead_id, 'maps')

@company_insights_bp.route('/api/company-insights/all/<string:lead_id>', methods=['GET'])
@login_required
def get_all_insights(lead_id):
    """Get all insights data for a lead"""
    try:
        current_app.logger.info(f"Master API called for lead {lead_id} by user {current_user.user_id}")

        # Check lead access
        access_granted, access_message = CompanyInsightsController.check_lead_access(current_user.user_id, lead_id)
        if not access_granted:
            return jsonify({"error": access_message}), 404

        # Get all insights data
        success, result = CompanyInsightsController.get_all_insights(current_user.user_id, lead_id)

        if success:
            return jsonify({
                "success": True,
                "data": result
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": result
            }), 404

    except Exception as e:
        current_app.logger.error(f"Error in master API for lead {lead_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def _store_feature_data(feature_name):
    """Helper function to store feature data"""
    try:
        data = request.json

        if not data:
            return jsonify({"error": "No input data provided"}), 400

        lead_id = data.get('lead_id')
        feature_data = data.get('data')

        if not lead_id:
            return jsonify({"error": "lead_id is required"}), 400

        if feature_data is None:
            return jsonify({"error": "data is required"}), 400

        current_app.logger.info(f"Storing {feature_name} data for lead {lead_id} by user {current_user.user_id}")

        # Check lead access
        access_granted, access_message = CompanyInsightsController.check_lead_access(current_user.user_id, lead_id)
        if not access_granted:
            return jsonify({"error": access_message}), 404

        # Store the feature data
        success, result = CompanyInsightsController.store_feature_data(
            current_user.user_id,
            lead_id,
            feature_name,
            feature_data
        )

        if success:
            return jsonify({
                "success": True,
                "message": f"{feature_name} data stored successfully",
                "data": result
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": result
            }), 400

    except Exception as e:
        current_app.logger.error(f"Error storing {feature_name} data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def _get_feature_data(lead_id, feature_name):
    """Helper function to get feature data"""
    try:
        current_app.logger.info(f"Getting {feature_name} data for lead {lead_id} by user {current_user.user_id}")

        # Check lead access
        access_granted, access_message = CompanyInsightsController.check_lead_access(current_user.user_id, lead_id)
        if not access_granted:
            return jsonify({"error": access_message}), 404

        # Get the feature data
        success, result = CompanyInsightsController.get_feature_data(
            current_user.user_id,
            lead_id,
            feature_name
        )

        if success:
            return jsonify({
                "success": True,
                "data": result
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": result
            }), 404

    except Exception as e:
        current_app.logger.error(f"Error getting {feature_name} data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
