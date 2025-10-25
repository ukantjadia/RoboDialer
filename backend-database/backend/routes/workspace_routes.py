from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from controllers.workspace_controller import WorkspaceController
from controllers.workspace_member_controller import WorkspaceMemberController
from controllers.project_controller import ProjectController

from controllers.workspace_settings_controller import WorkspaceSettingsController

# Create blueprint
workspace_bp = Blueprint('workspace', __name__, url_prefix='/api/workspace')

# ============================================================================
# WORKSPACE ROUTES
# ============================================================================

@workspace_bp.route('/', methods=['GET'])
@login_required
def get_user_workspaces():
    """Get all workspaces for current user"""
    return WorkspaceController.get_user_workspaces()

@workspace_bp.route('/', methods=['POST'])
@login_required
def create_workspace():
    """Create a new workspace"""
    # Handle both JSON and FormData
    data = None
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json()
    else:
        # Handle FormData
        data = {
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'domain': request.form.get('domain'),
            'industry': request.form.get('industry'),
            'size': request.form.get('size', 'medium'),
        }

    if not data:
        return jsonify({"error": "No data provided"}), 400
    return WorkspaceController.create_workspace_v2(data)

@workspace_bp.route('/search', methods=['GET'])
@login_required
def search_workspaces():
    """Search workspaces by name or description"""
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "Search query is required"}), 400
    return WorkspaceController.search_workspaces(query)

@workspace_bp.route('/<workspace_id>', methods=['GET'])
@login_required
def get_workspace(workspace_id):
    """Get workspace details"""
    return WorkspaceController.get_workspace(workspace_id)

@workspace_bp.route('/<workspace_id>', methods=['PUT'])
@login_required
def update_workspace(workspace_id):
    """Update workspace"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return WorkspaceController.update_workspace(workspace_id, data)

@workspace_bp.route('/<workspace_id>', methods=['DELETE'])
@login_required
def delete_workspace(workspace_id):
    """Delete workspace"""
    return WorkspaceController.delete_workspace(workspace_id)

@workspace_bp.route('/<workspace_id>/archive', methods=['PUT'])
@login_required
def archive_workspace(workspace_id):
    """Archive workspace"""
    return WorkspaceController.archive_workspace(workspace_id)

@workspace_bp.route('/<workspace_id>/overview', methods=['GET'])
@login_required
def get_workspace_overview(workspace_id):
    """Get workspace overview with statistics"""
    return WorkspaceController.get_workspace_overview(workspace_id)

# ============================================================================
# WORKSPACE MEMBER ROUTES
# ============================================================================

@workspace_bp.route('/<workspace_id>/members', methods=['GET'])
@login_required
def get_workspace_members(workspace_id):
    """Get all members of a workspace"""
    return WorkspaceMemberController.get_workspace_members(workspace_id)

@workspace_bp.route('/<workspace_id>/members', methods=['POST'])
@login_required
def add_member(workspace_id):
    """Add a new member to workspace"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return WorkspaceMemberController.add_member(workspace_id, data)

@workspace_bp.route('/<workspace_id>/members/<member_id>/role', methods=['PUT'])
@login_required
def update_member_role(workspace_id, member_id):
    """Update member role"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return WorkspaceMemberController.update_member_role(workspace_id, member_id, data)

@workspace_bp.route('/<workspace_id>/members/<member_id>', methods=['DELETE'])
@login_required
def remove_member(workspace_id, member_id):
    """Remove member from workspace"""
    return WorkspaceMemberController.remove_member(workspace_id, member_id)

@workspace_bp.route('/<workspace_id>/members/<workspace_member_id>/info', methods=['GET'])
@login_required
def get_member_info(workspace_id, workspace_member_id):
    """Get detailed information about a workspace member, including their projects and tasks."""
    # The controller will handle all logic and validation
    response, status_code = WorkspaceController.get_member_project_and_task_info(
        workspace_id, 
        workspace_member_id
    )
    return jsonify(response), status_code

# ============================================================================
# WORKSPACE INVITATION ROUTES
# ============================================================================

@workspace_bp.route('/<workspace_id>/invitations', methods=['POST'])
@login_required
def invite_member(workspace_id):
    """Send invitation to join workspace"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return WorkspaceMemberController.invite_member(workspace_id, data)

@workspace_bp.route('/invitations/<token>', methods=['GET'])
def get_invitation(token):
    """Get invitation details by token"""
    return WorkspaceMemberController.get_invitation(token)

@workspace_bp.route('/invitations/<token>/accept', methods=['POST'])
@login_required
def accept_invitation(token):
    """Accept workspace invitation"""
    return WorkspaceMemberController.accept_invitation(token)

@workspace_bp.route('/invitations/<token>/decline', methods=['POST'])
@login_required
def decline_invitation(token):
    """Decline workspace invitation"""
    return WorkspaceMemberController.decline_invitation(token)

@workspace_bp.route('/<workspace_id>/invitations/<invitation_id>/cancel', methods=['DELETE'])
@login_required
def cancel_invitation(workspace_id, invitation_id):
    """Cancel pending invitation"""
    return WorkspaceMemberController.cancel_invitation(workspace_id, invitation_id)

@workspace_bp.route('/<workspace_id>/invitations/<invitation_id>/resend', methods=['POST'])
@login_required
def resend_invitation(workspace_id, invitation_id):
    """Resend invitation"""
    return WorkspaceMemberController.resend_invitation(workspace_id, invitation_id)

@workspace_bp.route('/<workspace_id>/members/me/leave', methods=['POST'])
@login_required
def leave_workspace(workspace_id):
    """Leave workspace (for members)"""
    return WorkspaceMemberController.leave_workspace(workspace_id)

# ============================================================================
# PROJECT ROUTES
# ============================================================================

@workspace_bp.route('/<workspace_id>/projects', methods=['GET'])
@login_required
def get_workspace_projects(workspace_id):
    """Get all projects in a workspace"""
    return ProjectController.get_workspace_projects_v2(workspace_id)

@workspace_bp.route('/<workspace_id>/projects', methods=['POST'])
@login_required
def create_project(workspace_id):
    """Create a new project"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return ProjectController.create_project(workspace_id, data)

@workspace_bp.route('/<workspace_id>/projects/search', methods=['GET'])
@login_required
def search_projects(workspace_id):
    """Search projects in workspace"""
    query = request.args.get('q')
    if not query:
        return jsonify({"error": "Search query is required"}), 400
    return ProjectController.search_projects(workspace_id, query)

@workspace_bp.route('/<workspace_id>/projects/statistics', methods=['GET'])
@login_required
def get_project_statistics(workspace_id):
    """Get project statistics for workspace"""
    return ProjectController.get_project_statistics(workspace_id)

# ============================================================================
# PROJECT DETAIL ROUTES
# ============================================================================

@workspace_bp.route('/projects/<project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    """Get project details"""
    return ProjectController.get_project(project_id)

@workspace_bp.route('/projects/<project_id>', methods=['PUT'])
@login_required
def update_project(project_id):
    """Update project"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return ProjectController.update_project(project_id, data)

@workspace_bp.route('/projects/<project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    """Delete project"""
    return ProjectController.delete_project(project_id)

@workspace_bp.route('/projects/<project_id>/members/me/leave', methods=['POST'])
@login_required
def leave_project(project_id):
    """Leave project (for members)"""
    return ProjectController.leave_project(project_id)

@workspace_bp.route('/projects/<project_id>/members/add', methods=['POST'])
@login_required
def add_project_member(project_id):
    """Adds a workspace member to a specific project."""
    data = request.get_json()
    if not data or 'workspace_member_id' not in data:
        return jsonify({"error": "workspace_member_id is required"}), 400
    
    workspace_member_id = data.get('workspace_member_id')
    response, status_code = ProjectController.add_member_to_project(project_id, workspace_member_id)
    return jsonify(response), status_code

@workspace_bp.route('/projects/<project_id>/members/remove', methods=['DELETE'])
@login_required
def remove_project_member(project_id):
    """Removes a member from a specific project."""
    data = request.get_json()
    if not data or 'workspace_member_id' not in data:
        return jsonify({"error": "workspace_member_id is required"}), 400
        
    workspace_member_id = data.get('workspace_member_id')
    response, status_code = ProjectController.remove_member_from_project(project_id, workspace_member_id)
    return jsonify(response), status_code



# ============================================================================
# WORKSPACE SETTINGS ROUTES
# ============================================================================

@workspace_bp.route('/<workspace_id>/settings', methods=['GET'])
@login_required
def get_workspace_settings(workspace_id):
    """Get workspace settings"""
    return WorkspaceSettingsController.get_workspace_settings(workspace_id)

@workspace_bp.route('/<workspace_id>/settings', methods=['PUT'])
@login_required
def update_workspace_settings(workspace_id):
    """Update workspace settings"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return WorkspaceSettingsController.update_workspace_settings(workspace_id, data)

@workspace_bp.route('/<workspace_id>/settings/reset', methods=['POST'])
@login_required
def reset_workspace_settings(workspace_id):
    """Reset workspace settings to default"""
    return WorkspaceSettingsController.reset_workspace_settings(workspace_id)

@workspace_bp.route('/<workspace_id>/permissions', methods=['GET'])
@login_required
def get_workspace_permissions(workspace_id):
    """Get workspace permission matrix"""
    return WorkspaceSettingsController.get_workspace_permissions(workspace_id)

@workspace_bp.route('/<workspace_id>/activity', methods=['GET'])
@login_required
def get_workspace_activity_logs(workspace_id):
    """Get workspace activity logs"""
    return WorkspaceSettingsController.get_workspace_activity_logs(workspace_id)

@workspace_bp.route('/<workspace_id>/export', methods=['GET'])
@login_required
def export_workspace_data(workspace_id):
    """Export workspace data"""
    return WorkspaceSettingsController.export_workspace_data(workspace_id)

@workspace_bp.route('/<workspace_id>/analytics', methods=['GET'])
@login_required
def get_workspace_analytics(workspace_id):
    """Get workspace analytics and insights"""
    return WorkspaceSettingsController.get_workspace_analytics(workspace_id)
