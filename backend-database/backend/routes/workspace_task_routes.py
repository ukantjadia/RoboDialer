from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from controllers.workspace_task_controller import WorkspaceTaskController

# Create blueprint
workspace_task_bp = Blueprint('workspace_task', __name__, url_prefix='/api/workspace')

@workspace_task_bp.route('/<workspace_id>/tasks', methods=['GET'])
@login_required
def get_workspace_tasks(workspace_id):
    """Get all tasks in workspace"""
    return WorkspaceTaskController.get_workspace_tasks(workspace_id)

@workspace_task_bp.route('/projects/<project_id>/tasks', methods=['GET'])
@login_required
def get_project_tasks(project_id):
    """Get all tasks for a specific project"""
    return WorkspaceTaskController.get_project_tasks(project_id)

@workspace_task_bp.route('/<workspace_id>/tasks', methods=['POST'])
@login_required
def create_task(workspace_id):
    """Create a new task"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return WorkspaceTaskController.create_task(workspace_id, data)

@workspace_task_bp.route('/tasks/<task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    """Get task details"""
    return WorkspaceTaskController.get_task(task_id)

@workspace_task_bp.route('/tasks/<task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """Update task"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return WorkspaceTaskController.update_task(task_id, data)

@workspace_task_bp.route('/tasks/<task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Delete task"""
    return WorkspaceTaskController.delete_task(task_id)

@workspace_task_bp.route('/tasks/<task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """Complete task"""
    data = request.get_json() or {}
    return WorkspaceTaskController.complete_task(task_id, data)

@workspace_task_bp.route('/user/tasks', methods=['GET'])
@login_required
def get_user_tasks():
    """Get tasks assigned to current user"""
    return WorkspaceTaskController.get_user_tasks()

@workspace_task_bp.route('/<workspace_id>/tasks/overdue', methods=['GET'])
@login_required
def get_workspace_overdue_tasks(workspace_id):
    """Get overdue tasks in workspace"""
    return WorkspaceTaskController.get_overdue_tasks(workspace_id)

@workspace_task_bp.route('/tasks/overdue', methods=['GET'])
@login_required
def get_all_overdue_tasks():
    """Get all overdue tasks across workspaces"""
    return WorkspaceTaskController.get_overdue_tasks() 
    
@workspace_task_bp.route('/<workspace_id>/tasks/forward-user-lead-draft', methods=['POST'])
@login_required
def forward_user_lead_draft_to_task(workspace_id):
    """Forward user lead draft to create a task"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return WorkspaceTaskController.forward_user_lead_draft_to_task(workspace_id, data) 

@workspace_task_bp.route('/tasks/<task_id>/mark-as-seen', methods=['POST'])
@login_required
def mark_task_as_seen(task_id):
    """Marks a task assigned to the current user as seen."""
    response, status_code = WorkspaceTaskController.mark_task_as_seen(task_id)
    return jsonify(response), status_code