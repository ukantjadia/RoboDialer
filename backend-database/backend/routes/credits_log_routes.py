from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from utils.decorators import role_required
from controllers.credits_log_controller import CreditsLogController

credits_log_bp = Blueprint('credits_log', __name__)

@credits_log_bp.route('/admin/credits-logs')
@login_required
@role_required('admin', 'developer') # Protect this page for admins
def view_credit_logs():
    """Renders the credit logs page and provides the initial filter data."""
    filters = CreditsLogController.get_log_filters()
    return render_template('admin/credits_logs.html', filters=filters)

@credits_log_bp.route('/api/admin/credits-logs', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'developer') # Protect the API endpoint
def get_credit_logs_api():
    """Provides the JSON data for the DataTables on the credit logs page."""
    response = CreditsLogController.get_logs_paginated()
    return jsonify(response)