from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from utils.decorators import role_required
from controllers.credit_transfer_log_controller import CreditTransferLogController

credit_transfer_log_bp = Blueprint('credit_transfer_log', __name__)

@credit_transfer_log_bp.route('/admin/credit-transfers')
@login_required
@role_required('admin', 'developer') # Protect this page for admins
def view_credit_transfers():
    """Renders the credit transfer logs page and provides the initial filter data."""
    filters = CreditTransferLogController.get_transfer_filters()
    return render_template('admin/credit_transfer_logs.html', filters=filters)

@credit_transfer_log_bp.route('/api/admin/credit-transfers', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'developer') # Protect the API endpoint
def get_credit_transfers_api():
    """Provides the JSON data for the DataTables on the credit transfer logs page."""
    response = CreditTransferLogController.get_transfers_paginated()
    return jsonify(response)

@credit_transfer_log_bp.route('/api/admin/credit-transfers/summary/<user_id>')
@login_required
@role_required('admin', 'developer')
def get_user_transfer_summary(user_id):
    """Get transfer summary for a specific user"""
    company_id = request.args.get('company_id')
    summary = CreditTransferLogController.get_user_transfer_summary(user_id, company_id)
    return jsonify(summary)

@credit_transfer_log_bp.route('/api/admin/credit-transfers/company-summary/<company_id>')
@login_required
@role_required('admin', 'developer')
def get_company_transfer_summary(company_id):
    """Get transfer summary for a specific company"""
    summary = CreditTransferLogController.get_company_transfer_summary(company_id)
    return jsonify(summary)
