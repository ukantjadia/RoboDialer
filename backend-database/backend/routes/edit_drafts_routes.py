from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.edit_lead_drafts_model import EditLeadDraft
from models.lead_model import Lead, db
from controllers.audit_controller import AuditController
from utils.decorators import role_required
from datetime import datetime, timedelta

# Create blueprint
drafts_edit_bp = Blueprint('drafts_edit', __name__)

@drafts_edit_bp.route('/api/lead-drafts', methods=['POST'])
@login_required
def create_lead_draft():
    """Create a new lead draft"""
    data = request.json
    
    if not data:
        return jsonify({"error": "No input data provided"}), 400
        
    lead_id = data.get('lead_id')
    draft_data = data.get('draft_data')
    change_summary = data.get('change_summary')
    
    if not lead_id or not draft_data:
        return jsonify({"error": "lead_id and draft_data are required"}), 400
    
    # Check if lead exists
    lead = Lead.query.filter_by(lead_id=lead_id, deleted=False).first()
    if not lead:
        return jsonify({"error": "Lead not found"}), 404
    
    try:
        # Create new draft
        draft = EditLeadDraft(
            user_id=str(current_user.user_id),
            lead_id=lead_id,
            draft_data=draft_data,
            change_summary=change_summary
        )
        
        db.session.add(draft)
        
        # Log the creation
        AuditController.log_action(
            user_id=current_user.user_id,
            action_type='create',
            table_affected='edit_lead_drafts',
            record_id=draft.id,
            new_values=draft.to_dict()
        )
        
        db.session.commit()
        return jsonify({"message": "Draft created successfully", "draft": draft.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@drafts_edit_bp.route('/api/lead-drafts', methods=['GET'])
@login_required
def get_user_drafts():
    """Get all drafts for the current user"""
    try:
        # Get all non-deleted drafts for the current user
        drafts_edit = EditLeadDraft.query.filter_by(user_id=str(current_user.user_id), deleted=False).all()
        
        # Format results
        results = []
        for draft in drafts_edit:
            lead = Lead.query.filter_by(lead_id=draft.lead_id, deleted=False).first()
            if lead:
                result = draft.to_dict()
                result['lead'] = {
                    'lead_id': lead.lead_id,
                    'company': lead.company
                }
                results.append(result)
        
        return jsonify({
            "total": len(results),
            "drafts_edit": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@drafts_edit_bp.route('/api/lead-drafts/<string:draft_id>', methods=['GET'])
@login_required
def get_draft(draft_id):
    """Get a specific draft"""
    draft = EditLeadDraft.query.filter_by(draft_id=draft_id, deleted=False).first()
    if not draft:
        return jsonify({"error": "Draft not found"}), 404
    
    # Check if user has access to this draft
    if draft.user_id != str(current_user.user_id) and not current_user.role in ['admin', 'developer']:
        return jsonify({"error": "You don't have permission to access this draft"}), 403
    
    try:
        lead = Lead.query.filter_by(lead_id=draft.lead_id, deleted=False).first()
        result = draft.to_dict()
        if lead:
            result['lead'] = {
                'lead_id': lead.lead_id,
                'company': lead.company
            }
        
        # Log the view
        AuditController.log_action(
            user_id=current_user.user_id,
            action_type='view',
            table_affected='edit_lead_drafts',
            record_id=draft.id
        )
        
        db.session.commit()
        return jsonify(result)
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@drafts_edit_bp.route('/api/lead-drafts/<string:draft_id>', methods=['PUT'])
@login_required
def update_draft(draft_id):
    """Update a draft"""
    data = request.json
    
    if not data:
        return jsonify({"error": "No input data provided"}), 400
    
    draft = EditLeadDraft.query.filter_by(draft_id=draft_id, deleted=False).first()
    if not draft:
        return jsonify({"error": "Draft not found"}), 404
    
    # Check if user has permission to edit this draft
    if draft.user_id != str(current_user.user_id) and not current_user.role in ['admin', 'developer']:
        return jsonify({"error": "You don't have permission to update this draft"}), 403
    
    try:
        # Store old values for audit
        old_values = draft.to_dict()
        
        # Update fields
        if 'draft_data' in data:
            draft.draft_data = data['draft_data']
            # Increment version
            draft.increment_version()
        
        if 'change_summary' in data:
            draft.change_summary = data['change_summary']
        
        if 'phase' in data:
            draft.phase = data['phase']
        
        if 'status' in data:
            draft.status = data['status']
        
        # Log the update
        AuditController.log_action(
            user_id=current_user.user_id,
            action_type='update',
            table_affected='edit_lead_drafts',
            record_id=draft.id,
            old_values=old_values,
            new_values=draft.to_dict()
        )
        
        db.session.commit()
        return jsonify({"message": "Draft updated successfully", "draft": draft.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@drafts_edit_bp.route('/api/lead-drafts/<string:draft_id>', methods=['DELETE'])
@login_required
def delete_draft(draft_id):
    """Soft delete a draft"""
    draft = EditLeadDraft.query.filter_by(draft_id=draft_id, deleted=False).first()
    if not draft:
        return jsonify({"error": "Draft not found"}), 404
    
    # Check if user has permission to delete this draft
    if draft.user_id != str(current_user.user_id) and not current_user.role in ['admin', 'developer']:
        return jsonify({"error": "You don't have permission to delete this draft"}), 403
    
    try:
        # Store old values for audit
        old_values = draft.to_dict()
        
        # Soft delete by setting deleted
        draft.deleted = True
        
        # Log the deletion
        AuditController.log_action(
            user_id=current_user.user_id,
            action_type='delete',
            table_affected='edit_lead_drafts',
            record_id=draft.id,
            old_values=old_values,
            new_values=draft.to_dict()
        )
        
        db.session.commit()
        return jsonify({"message": "Draft deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500 