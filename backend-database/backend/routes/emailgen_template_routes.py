from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from controllers.emailgen_template_controller import EmailGenTemplateController
import os
import json
from config.config import Config
from models.emailgen_template_model import EmailGenTemplate, db
from models.user_model import User

emailgen_template_bp = Blueprint('emailgen_template_bp', __name__)

@emailgen_template_bp.route('/api/emailgen_templates/', methods=['GET'])
@login_required
def list_emailgen_templates():
    logger = current_app.logger
    logger.info(f"User {current_user.user_id}: {current_user.username} requested template list.")
    return jsonify(EmailGenTemplateController.get_templates())

@emailgen_template_bp.route('/api/emailgen_templates/', methods=['POST'])
@login_required
def create_emailgen_template():
    logger = current_app.logger
    data = request.get_json(force=True)
    logger.info(f"User {current_user.user_id}: {current_user.username} creating template: {data.get('template_name')}")
    success, result = EmailGenTemplateController.create_template(data)
    status = 201 if success else 400
    return jsonify(result), status

@emailgen_template_bp.route('/api/emailgen_templates/<template_id>', methods=['PUT'])
@login_required
def update_emailgen_template(template_id):
    logger = current_app.logger
    data = request.get_json(force=True)
    logger.info(f"User {current_user.user_id}: {current_user.username} updating template {template_id}")
    success, result = EmailGenTemplateController.update_template(template_id, data)
    status = 200 if success else 400
    return jsonify(result), status

@emailgen_template_bp.route('/api/emailgen_templates/<template_id>', methods=['DELETE'])
@login_required
def delete_emailgen_template(template_id):
    logger = current_app.logger
    logger.info(f"User {current_user.user_id}: {current_user.username} deleting template {template_id}")
    success, result = EmailGenTemplateController.delete_template(template_id)
    status = 200 if success else 400
    return jsonify({'success': success, 'message': result}), status

@emailgen_template_bp.route('/api/emailgen_templates/<template_id>/set_default', methods=['POST'])
@login_required
def set_default_emailgen_template(template_id):
    logger = current_app.logger
    logger.info(f"User {current_user.user_id}: {current_user.username} setting default template {template_id}")
    success, result = EmailGenTemplateController.set_default(template_id)
    status = 200 if success else 400
    return jsonify(result), status

@emailgen_template_bp.route('/api/emailgen_templates/<template_id>/increment_usage', methods=['POST'])
@login_required
def increment_usage_emailgen_template(template_id):
    logger = current_app.logger
    logger.info(f"User {current_user.user_id}: {current_user.username} incrementing usage for template {template_id}")
    success, result = EmailGenTemplateController.increment_usage(template_id)
    status = 200 if success else 400
    return jsonify({'success': success, 'usage_count': result} if success else {'success': False, 'message': result}), status

@emailgen_template_bp.route('/api/emailgen_templates/init_user_templates', methods=['POST'])
@login_required
def init_user_templates():
    logger = current_app.logger
    logger.info(f"User {current_user.user_id}: {current_user.username} initializing user templates.")

    # Check if templates already initialized
    if current_user.has_initialized_templates:
        return jsonify({
            "message": "Templates already initialized",
            "templates": EmailGenTemplateController.get_templates(),
            "status": "already_initialized"
        }), 200

    user = User.query.get(current_user.user_id)
    success, result, status = EmailGenTemplateController.init_user_templates(user)

    if success:
        return jsonify({
            "message": "Templates initialized successfully",
            "templates": result,
            "status": "initialized"
        }), status
    else:
        return jsonify({
            "error": "Failed to initialize templates",
            "details": result,
            "status": "failed"
        }), status