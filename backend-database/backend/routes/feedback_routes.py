from flask import Blueprint, request, jsonify, current_app
from controllers.feedback_controller import FeedbackController

feedback_bp = Blueprint('feedback', __name__)
feedback_controller = FeedbackController()

@feedback_bp.route('/feedback', methods=['POST'])
def capture_feedback():
    current_app.logger.info(f'Route hit: /feedback')

    try:
        data = request.get_json()
        if not data:
            current_app.logger.warning(f'Invalid JSON payload in feedback request')
            return jsonify({'success': False, 'error': 'Invalid JSON payload'}), 400

        result = feedback_controller.capture_feedback(data)

        if result.get('success'):
            current_app.logger.info(f'Successfully captured feedback')
        else:
            current_app.logger.error(f'Failed to capture feedback: {result.get("error")}')

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f'Unexpected error in capture_feedback: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@feedback_bp.route('/regenerate', methods=['POST'])
def regenerate_content():
    current_app.logger.info(f'Route hit: /regenerate')

    try:
        data = request.get_json()
        if not data:
            current_app.logger.warning(f'Invalid JSON payload in regenerate request')
            return jsonify({'success': False, 'error': 'Invalid JSON payload'}), 400

        result = feedback_controller.handle_regeneration(data)

        if result.get('success'):
            current_app.logger.info(f'Successfully regenerated content')
        else:
            current_app.logger.error(f'Failed to regenerate content: {result.get("error")}')

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f'Unexpected error in regenerate_content: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@feedback_bp.route('/analytics', methods=['GET'])
def get_analytics():
    current_app.logger.info(f'Route hit: /analytics')

    try:
        filters = request.args.to_dict()
        result = feedback_controller.get_feedback_analytics(filters)

        if result.get('success'):
            current_app.logger.info(f'Successfully retrieved analytics')
        else:
            current_app.logger.error(f'Failed to retrieve analytics: {result.get("error")}')

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f'Unexpected error in get_analytics: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@feedback_bp.route('/history', methods=['GET'])
def get_user_history():
    current_app.logger.info(f'Route hit: /history')

    try:
        user_id = request.args.get('user_id')
        if not user_id:
            current_app.logger.warning(f'Missing user_id parameter in history request')
            return jsonify({'success': False, 'error': 'Missing required parameter: user_id'}), 400

        result = FeedbackController.get_user_feedback_history(user_id)

        if result.get('success'):
            current_app.logger.info(f'Successfully retrieved history for user {user_id}')
        else:
            current_app.logger.error(f'Failed to retrieve history for user {user_id}: {result.get("error")}')

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f'Unexpected error in get_user_history: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500