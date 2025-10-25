from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.workspace_invitation_model import WorkspaceInvitation, db
from models.workspace_model import Workspace
from models.user_model import User
from datetime import datetime

bp = Blueprint('invitations', __name__, url_prefix='/api/invitations')

@bp.route('/pending', methods=['GET'])
@login_required
def get_pending_invitations():
    """Get all pending invitations for the current user"""
    try:
        # Get invitations sent to current user's email
        invitations = WorkspaceInvitation.query.filter_by(
            email=current_user.email,
            status='pending'
        ).all()
        
        invitation_list = []
        for invitation in invitations:
            invitation_data = invitation.to_dict()
            
            # Get workspace name
            workspace = Workspace.query.get(invitation.workspace_id)
            invitation_data['workspace_name'] = workspace.name if workspace else 'Unknown'
            
            invitation_list.append(invitation_data)
        
        return jsonify(invitation_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<invitation_id>/accept', methods=['POST'])
@login_required
def accept_invitation(invitation_id):
    """Accept an invitation"""
    try:
        # Find the invitation
        invitation = WorkspaceInvitation.query.get(invitation_id)
        
        if not invitation:
            return jsonify({'success': False, 'message': 'Invitation not found'}), 404
        
        # Check if invitation is for current user
        if invitation.email != current_user.email:
            return jsonify({'success': False, 'message': 'This invitation is not for you'}), 403
        
        # Check if invitation is still pending
        if invitation.status != 'pending':
            return jsonify({'success': False, 'message': 'Invitation is not pending'}), 400
        
        # Check if invitation is expired
        if invitation.is_expired():
            invitation.status = 'expired'
            invitation.save()
            return jsonify({'success': False, 'message': 'Invitation has expired'}), 400
        
        # Accept the invitation
        success, message = invitation.accept_invitation(current_user.user_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<invitation_id>/decline', methods=['POST'])
@login_required
def decline_invitation(invitation_id):
    """Decline an invitation"""
    try:
        # Find the invitation
        invitation = WorkspaceInvitation.query.get(invitation_id)
        
        if not invitation:
            return jsonify({'success': False, 'message': 'Invitation not found'}), 404
        
        # Check if invitation is for current user
        if invitation.email != current_user.email:
            return jsonify({'success': False, 'message': 'This invitation is not for you'}), 403
        
        # Check if invitation is still pending
        if invitation.status != 'pending':
            return jsonify({'success': False, 'message': 'Invitation is not pending'}), 400
        
        # Get decline reason from request
        data = request.get_json() or {}
        reason = data.get('reason')
        
        try:
            # Update invitation status
            invitation.status = 'declined'
            invitation.declined_at = datetime.utcnow()
            invitation.decline_reason = reason
            invitation.save()
            
            return jsonify({'success': True, 'message': 'Invitation declined successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Failed to decline invitation: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<invitation_id>', methods=['GET'])
@login_required
def get_invitation(invitation_id):
    """Get a specific invitation"""
    try:
        invitation = WorkspaceInvitation.query.get(invitation_id)
        
        if not invitation:
            return jsonify({'error': 'Invitation not found'}), 404
        
        # Check if invitation is for current user
        if invitation.email != current_user.email:
            return jsonify({'error': 'This invitation is not for you'}), 403
        
        invitation_data = invitation.to_dict()
        
        # Get workspace name
        workspace = Workspace.query.get(invitation.workspace_id)
        invitation_data['workspace_name'] = workspace.name if workspace else 'Unknown'
        
        return jsonify(invitation_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 