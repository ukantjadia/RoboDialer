from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from controllers.user_controller import UserController

# Create blueprint
user_bp = Blueprint('user', __name__, url_prefix='/api/users')

# ============================================================================
# MEMBER FLOW ROUTES
# ============================================================================

@user_bp.route('/me', methods=['GET'])
@login_required
def get_my_profile():
    """Get current user's profile (member flow)"""
    return UserController.get_my_profile()

@user_bp.route('/me', methods=['PATCH'])
@login_required
def update_my_profile():
    """Update current user's profile (member flow)"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return UserController.update_my_profile(data)

@user_bp.route('/me/activity', methods=['GET'])
@login_required
def get_my_activity():
    """Get current user's activity logs (member flow)"""
    return UserController.get_my_activity()

@user_bp.route('/me/credit-history', methods=['GET'])
@login_required
def get_my_credit_history():
    """Get current user's credit history (member flow)"""
    return UserController.get_my_credit_history()

@user_bp.route('/me/last-login', methods=['GET'])
@login_required
def get_my_last_login():
    """Get current user's last login information"""
    try:
        from datetime import datetime

        last_login_info = {
            'last_login_at': current_user.last_login_at.isoformat() if current_user.last_login_at else None,
            'days_since_last_login': None,
            'is_recently_active': False
        }

        # Calculate days since last login
        if current_user.last_login_at:
            days_since = (datetime.utcnow() - current_user.last_login_at).days
            last_login_info['days_since_last_login'] = days_since
            last_login_info['is_recently_active'] = days_since <= 30

        return jsonify({
            'success': True,
            'data': last_login_info
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500