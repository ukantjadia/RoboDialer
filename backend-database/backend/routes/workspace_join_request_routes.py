from flask import Blueprint, request, jsonify
from flask_login import login_required
from controllers.workspace_join_request_controller import WorkspaceJoinRequestController

# Create blueprint
workspace_join_request_bp = Blueprint('workspace_join_request', __name__, url_prefix='/api/workspace-join-requests')

# ============================================================================
# PUBLIC WORKSPACE DISCOVERY ROUTES
# ============================================================================

@workspace_join_request_bp.route('/public-workspaces', methods=['GET'])
@login_required
def get_public_workspaces():
    """Get list of public workspaces that user can request to join"""
    return WorkspaceJoinRequestController.get_public_workspaces()

# ============================================================================
# JOIN REQUEST MANAGEMENT ROUTES (User perspective)
# ============================================================================

@workspace_join_request_bp.route('/', methods=['POST'])
@login_required
def create_join_request():
    """Create a new join request"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return WorkspaceJoinRequestController.create_join_request(data)

@workspace_join_request_bp.route('/my-requests', methods=['GET'])
@login_required
def get_my_join_requests():
    """Get current user's join requests"""
    return WorkspaceJoinRequestController.get_my_join_requests()

@workspace_join_request_bp.route('/<request_id>/cancel', methods=['POST'])
@login_required
def cancel_join_request(request_id):
    """Cancel a join request"""
    return WorkspaceJoinRequestController.cancel_join_request(request_id)

# ============================================================================
# WORKSPACE ADMIN/MANAGER ROUTES
# ============================================================================

@workspace_join_request_bp.route('/workspace/<workspace_id>/requests', methods=['GET'])
@login_required
def get_workspace_join_requests(workspace_id):
    """Get join requests for a workspace (for admins/managers)"""
    return WorkspaceJoinRequestController.get_workspace_join_requests(workspace_id)

@workspace_join_request_bp.route('/workspace/<workspace_id>/requests/<request_id>/approve', methods=['POST'])
@login_required
def approve_join_request(workspace_id, request_id):
    """Approve a join request"""
    return WorkspaceJoinRequestController.approve_join_request(workspace_id, request_id)

@workspace_join_request_bp.route('/workspace/<workspace_id>/requests/<request_id>/reject', methods=['POST'])
@login_required
def reject_join_request(workspace_id, request_id):
    """Reject a join request"""
    data = request.get_json() or {}
    return WorkspaceJoinRequestController.reject_join_request(workspace_id, request_id, data) 