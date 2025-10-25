from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from controllers.team_controller import TeamController
from controllers.team_project_controller import TeamProjectController
from models.user_model import User
from models.lead_model import db

# Create blueprint
team_bp = Blueprint('team', __name__, url_prefix='/api/teams')

# ============================================================================
# CREDIT MANAGEMENT ROUTES
# ============================================================================

@team_bp.route('/<team_id>/credits', methods=['GET'])
@login_required
def get_team_credits(team_id):
    """Get team's total credits"""
    return TeamController.get_team_credits(team_id)

@team_bp.route('/<team_id>/credits/assign', methods=['POST'])
@login_required
def assign_credits(team_id):
    """Assign credits to member and deduct from team credits"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TeamController.assign_team_credits(team_id, data)

@team_bp.route('/<team_id>/members/<member_id>/credits', methods=['GET'])
@login_required
def get_member_credits(team_id, member_id):
    """Get current member's credits"""
    return TeamController.get_member_credits(team_id, member_id)

@team_bp.route('/<team_id>/credits/request', methods=['POST'])
@login_required
def request_credits(team_id):
    """Request credits from team pool"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TeamController.request_credits(team_id, data)

@team_bp.route('/<team_id>/credits/requests', methods=['GET'])
@login_required
def get_credit_requests(team_id):
    """Get all credit requests"""
    return TeamController.get_credit_requests(team_id)

@team_bp.route('/<team_id>/credits/requests/<request_id>/approve', methods=['POST'])
@login_required
def approve_credit_request(team_id, request_id):
    """Approve credit request"""
    return TeamController.approve_credit_request(team_id, request_id)

@team_bp.route('/<team_id>/credits/requests/<request_id>/reject', methods=['POST'])
@login_required
def reject_credit_request(team_id, request_id):
    """Reject credit request"""
    data = request.get_json() or {}  # For rejection reason
    return TeamController.reject_credit_request(team_id, request_id, data)

# ============================================================================
# BASIC TEAM ROUTES
# ============================================================================

@team_bp.route('/<team_id>', methods=['GET'])
@login_required
def get_team(team_id):
    """Get team details"""
    return TeamController.get_team(team_id)

@team_bp.route('/<team_id>', methods=['DELETE'])
@login_required
def delete_team(team_id):
    """Delete team"""
    return TeamController.delete_team(team_id)

@team_bp.route('/<team_id>/members', methods=['GET'])
@login_required
def get_team_members(team_id):
    """Get all members of a team"""
    return TeamController.get_team_members(team_id)

@team_bp.route('/<team_id>/members/invite', methods=['POST'])
@login_required
def invite_team_member(team_id):
    """Invite a member to team"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TeamController.invite_team_member(team_id, data)

@team_bp.route('/<team_id>/members/<member_id>', methods=['PUT'])
@login_required
def update_team_member(team_id, member_id):
    """Update team member (role and/or credits)"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TeamController.update_team_member(team_id, member_id, data)

@team_bp.route('/<team_id>/members/<member_id>/role', methods=['PATCH'])
@login_required
def update_member_role(team_id, member_id):
    """Update member role (manager policy enforced)"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TeamController.update_member_role(team_id, member_id, data)
@team_bp.route('/<team_id>/members/<member_id>', methods=['DELETE'])
@login_required
def remove_team_member(team_id, member_id):
    """Remove member from team"""
    return TeamController.remove_team_member(team_id, member_id)

# ============================================================================
# PROJECT ROUTES
# ============================================================================

@team_bp.route('/<team_id>/projects', methods=['GET'])
@login_required
def get_team_projects(team_id):
    """Get all projects in a team"""
    return TeamProjectController.get_team_projects(team_id)

@team_bp.route('/<team_id>/projects', methods=['POST'])
@login_required
def create_team_project(team_id):
    """Create a new project in team"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TeamProjectController.create_team_project(team_id, data)

@team_bp.route('/<team_id>/projects/<project_id>', methods=['PUT'])
@login_required
def update_team_project(team_id, project_id):
    """Update project in team"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TeamProjectController.update_team_project(team_id, project_id, data)

@team_bp.route('/<team_id>/projects/<project_id>', methods=['DELETE'])
@login_required
def delete_team_project(team_id, project_id):
    """Delete project from team"""
    return TeamProjectController.delete_team_project(team_id, project_id)

@team_bp.route('/projects/metrics/common', methods=['GET'])
@login_required
def get_common_metrics():
    """Get list of common project metrics"""
    from models.project_metrics_model import ProjectMetrics
    try:
        metrics = ProjectMetrics.get_common_metrics()
        return jsonify({"metrics": metrics}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch common metrics: {str(e)}"}), 500



# ============================================================================
# ACTIVITY LOGS ROUTES
# ============================================================================

@team_bp.route('/<team_id>/activity', methods=['GET'])
@login_required
def get_team_activity(team_id):
    """Get team activity logs"""
    return TeamController.get_team_activity(team_id) 