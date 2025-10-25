from flask import Blueprint, request, jsonify, current_app
from controllers.ai_analysis_controller import AIAnalysisController
from flask_login import login_required, current_user
import uuid

# Create blueprint
ai_analysis_bp = Blueprint('ai_analysis', __name__)

@ai_analysis_bp.route('/api/recommend', methods=['POST'])
@login_required
def create_or_update_ai_analysis():
    """
    POST /api/recommend - Create new AI analysis or update existing one

    Expected payload:
    {
        "lead_id": "string",
        "project_id": "uuid",
        "task_id": "uuid", // Optional - task ID for task-specific analysis
        "website_text": "object", // Optional - scraped website content
        "ai_analysis": "object" // Optional - AI analysis results
    }
    """
    # Log request start
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))
    current_app.logger.info(f'[AI Analysis] POST /api/recommend - User: {username} (ID: {user_id})')

    try:
        data = request.get_json()
        current_app.logger.info(f'[AI Analysis] Request data: lead_id={data.get("lead_id")}, project_id={data.get("project_id")}, task_id={data.get("task_id")}')

        # Get current user
        if not user_id:
            current_app.logger.warning(f'[AI Analysis] Unauthenticated user attempt')
            return jsonify({'error': 'User not authenticated'}), 401

        # Validate request data
        current_app.logger.info(f'[AI Analysis] Validating request data...')
        is_valid, error_message = AIAnalysisController.validate_analysis_data(data)
        if not is_valid:
            current_app.logger.warning(f'[AI Analysis] Validation failed: {error_message}')
            return jsonify({'error': error_message}), 400

        # Validate user access
        current_app.logger.info(f'[AI Analysis] Validating user access...')
        has_access, access_error = AIAnalysisController.validate_user_access(user_id, data['project_id'])
        if not has_access:
            current_app.logger.warning(f'[AI Analysis] Access denied: {access_error}')
            return jsonify({'error': access_error}), 404

        # Create or update analysis
        current_app.logger.info(f'[AI Analysis] Creating/updating analysis...')
        success, message, analysis_data, status_code = AIAnalysisController.create_or_update_analysis(
            lead_id=data['lead_id'],
            project_id=data['project_id'],
            user_id=user_id,
            task_id=data.get('task_id'),
            website_text=data.get('website_text'),
            ai_analysis=data.get('ai_analysis')
        )

        if success:
            current_app.logger.info(f'[AI Analysis] Successfully saved analysis for project: {data["project_id"]}')
            return jsonify({
                'success': True,
                'message': message,
                'analysis': analysis_data
            }), status_code
        else:
            current_app.logger.error(f'[AI Analysis] Failed to save analysis: {message}')
            return jsonify({'error': message}), status_code

    except Exception as e:
        current_app.logger.error(f'[AI Analysis] Unexpected error in create_or_update_ai_analysis route: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@ai_analysis_bp.route('/api/analysis/project/<string:project_id>', methods=['GET'])
@login_required
def get_project_analysis(project_id):
    """
    GET /api/analysis/project/<project_id> - List all AI analyses for a specific project
    """
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))
    current_app.logger.info(f'[AI Analysis] GET /api/analysis/project/{project_id} - User: {username} (ID: {user_id})')

    try:
        if not user_id:
            current_app.logger.warning(f'[AI Analysis] Unauthenticated user attempt for project: {project_id}')
            return jsonify({'error': 'User not authenticated'}), 401

        # Validate user access
        current_app.logger.info(f'[AI Analysis] Validating user access for project: {project_id}')
        has_access, access_error = AIAnalysisController.validate_user_access(user_id, project_id)
        if not has_access:
            current_app.logger.warning(f'[AI Analysis] Access denied for project {project_id}: {access_error}')
            return jsonify({'error': access_error}), 404

        # Get analyses list
        current_app.logger.info(f'[AI Analysis] Retrieving analyses for project: {project_id}')
        success, message, analyses_data, status_code = AIAnalysisController.get_project_analysis(project_id)

        if success:
            return jsonify({
                'success': True,
                'analyses': analyses_data
            }), status_code
        else:
            return jsonify({'error': message}), status_code

    except Exception as e:
        current_app.logger.error(f'[AI Analysis] Unexpected error in get_project_analysis route for project {project_id}: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@ai_analysis_bp.route('/api/analysis/project/<string:project_id>/task/<string:task_id>', methods=['GET'])
@login_required
def get_task_analysis(project_id, task_id):
    """
    GET /api/analysis/project/<project_id>/task/<task_id> - List all AI analyses for a specific task within a project
    """
    user_id = getattr(current_user, 'user_id', None)
    username = getattr(current_user, 'username', getattr(current_user, 'email', 'anonymous'))
    current_app.logger.info(f'[AI Analysis] GET /api/analysis/project/{project_id}/task/{task_id} - User: {username} (ID: {user_id})')

    try:
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        # Validate user access based on project
        has_access, access_error = AIAnalysisController.validate_user_access(user_id, project_id)
        if not has_access:
            return jsonify({'error': access_error}), 404

        success, message, analyses_data, status_code = AIAnalysisController.get_task_analysis(project_id, task_id)
        if success:
            return jsonify({
                'success': True,
                'analyses': analyses_data
            }), status_code
        else:
            return jsonify({'error': message}), status_code

    except Exception as e:
        current_app.logger.error(f'[AI Analysis] Unexpected error in get_task_analysis route: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500
