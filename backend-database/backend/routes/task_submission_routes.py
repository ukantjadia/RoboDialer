from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from controllers.task_submission_controller import TaskSubmissionController

# Create blueprint
task_submission_bp = Blueprint('task_submission', __name__, url_prefix='/api/task-submission')

@task_submission_bp.route('/tasks/<task_id>/submit', methods=['POST'])
@login_required
def submit_task(task_id):
    """Submit a task for review/approval"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TaskSubmissionController.submit_task(task_id, data)

@task_submission_bp.route('/workspace/<workspace_id>/pending', methods=['GET'])
@login_required
def get_pending_submissions(workspace_id):
    """Get pending submissions for managers and admins"""
    return TaskSubmissionController.get_pending_submissions(workspace_id)

@task_submission_bp.route('/submissions/<submission_id>/review', methods=['POST'])
@login_required
def review_submission(submission_id):
    """Review a submission (approve/reject)"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    return TaskSubmissionController.review_submission(submission_id, data)

 