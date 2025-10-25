from flask import Blueprint, request, jsonify
from flask_login import login_required
from controllers.role_request_controller import RoleRequestController

# Create blueprint
role_request_bp = Blueprint('role_request', __name__, url_prefix='/api/role-request')

@role_request_bp.route('/workspace/<workspace_id>/request', methods=['POST'])
@login_required
def request_role_change(workspace_id):
    """Request a role change in workspace"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return RoleRequestController.request_role_change(workspace_id, data)

@role_request_bp.route('/workspace/<workspace_id>/pending', methods=['GET'])
@login_required
def get_pending_role_requests(workspace_id):
    """Get pending role change requests for workspace (admin/manager only)"""
    return RoleRequestController.get_pending_role_requests(workspace_id)

@role_request_bp.route('/requests/<request_id>/review', methods=['POST'])
@login_required
def review_role_request(request_id):
    """Approve or reject a role change request"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return RoleRequestController.review_role_request(request_id, data)

@role_request_bp.route('/my-requests', methods=['GET'])
@login_required
def get_my_role_requests():
    """Get current user's role change requests"""
    return RoleRequestController.get_user_role_requests()

@role_request_bp.route('/requests/<request_id>/cancel', methods=['POST'])
@login_required
def cancel_role_request(request_id):
    """Cancel a role change request"""
    return RoleRequestController.cancel_role_request(request_id)