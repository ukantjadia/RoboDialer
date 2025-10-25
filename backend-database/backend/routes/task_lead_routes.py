from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from controllers.task_lead_controller import TaskLeadController

# Create blueprint
task_lead_bp = Blueprint('task_lead', __name__, url_prefix='/api/task-lead')

@task_lead_bp.route('/<task_id>/leads', methods=['GET'])
@login_required
def get_task_leads(task_id):
    """Get all leads for a task"""
    return TaskLeadController.get_task_leads(task_id)

@task_lead_bp.route('/<task_id>/leads', methods=['POST'])
@login_required
def add_lead_to_task(task_id):
    """Add a lead to a task"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TaskLeadController.add_lead_to_task(task_id, data)

@task_lead_bp.route('/<task_id>/leads/create', methods=['POST'])
@login_required
def create_lead_for_task(task_id):
    """Create a new lead and add it to a task"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TaskLeadController.create_lead_for_task(task_id, data)

@task_lead_bp.route('/<task_id>/leads/<lead_id>', methods=['DELETE'])
@login_required
def remove_lead_from_task(task_id, lead_id):
    """Remove a lead from a task"""
    return TaskLeadController.remove_lead_from_task(task_id, lead_id)

@task_lead_bp.route('/<task_id>/leads/<lead_id>', methods=['PUT'])
@login_required
def update_task_lead_status(task_id, lead_id):
    """Update the status of a task-lead relationship"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TaskLeadController.update_task_lead_and_lead(task_id, lead_id, data)

@task_lead_bp.route('/<task_id>/leads/<lead_id>/score', methods=['POST'])
@login_required
def score_task_lead(task_id, lead_id):
    """Score a task-lead relationship"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TaskLeadController.score_task_lead(task_id, lead_id, data)

@task_lead_bp.route('/<task_id>/leads/<lead_id>/score', methods=['GET'])
@login_required
def get_task_lead_score(task_id, lead_id):
    """Get the score for a specific task-lead relationship"""
    return TaskLeadController.get_task_lead_score(task_id, lead_id)

@task_lead_bp.route('/<task_id>/leads/<lead_id>/score', methods=['PUT'])
@login_required
def update_task_lead_score(task_id, lead_id):
    """Update the score for a task-lead relationship"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TaskLeadController.update_task_lead_score(task_id, lead_id, data)

@task_lead_bp.route('/projects/<project_id>/task-leads', methods=['GET'])
@login_required
def get_project_task_leads(project_id):
    """Get all task leads from all tasks in a project (for managers and admins)"""
    return TaskLeadController.get_project_task_leads(project_id)

@task_lead_bp.route('/workspace/<workspace_id>/task-leads', methods=['GET'])
@login_required
def get_workspace_task_leads(workspace_id):
    """Get all task leads from all tasks in a workspace (for admins and managers)"""
    return TaskLeadController.get_workspace_task_leads(workspace_id) 