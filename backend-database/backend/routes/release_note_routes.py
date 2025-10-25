from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models.release_note_model import ReleaseNote
from models.user_read_note_model import UserReadNote
from models.lead_model import db
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.decorators import admin_required, developer_required

bp = Blueprint('release_notes', __name__)


@bp.route('/api/release-notes', methods=['GET'])
@login_required
def get_release_notes():
    """Get all release notes, with read status for current user, excluding dismissed notes"""
    notes = ReleaseNote.query.order_by(ReleaseNote.created_at.desc()).all()
    
    # Get all note IDs that have been read by the current user
    read_note_ids = set(
        n.release_note_id for n in UserReadNote.query.filter_by(user_id=current_user.user_id)
    )
    
    # Get dismissed note IDs from user's dismissed_notes field
    dismissed_note_ids = set(current_user.get_dismissed_notes())
    
    # Filter out dismissed notes and add read status
    filtered_notes = []
    for note in notes:
        if note.id not in dismissed_note_ids:
            filtered_notes.append({
                **note.to_dict(), 
                'read': note.id in read_note_ids
            })
    
    return jsonify({
        'notes': filtered_notes
    })

@bp.route('/api/release-notes', methods=['POST'])
@login_required
@developer_required
def create_release_note():
    """Create a new release note (only for developers and admins)"""
    data = request.get_json()
    
    if not all(key in data for key in ['title', 'content', 'type']):
        return jsonify({'error': 'Missing required fields'}), 400
        
    if data['type'] not in ['feature', 'bug', 'improvement']:
        return jsonify({'error': 'Invalid note type'}), 400
    
    try:
        note = ReleaseNote.create(
            title=data['title'],
            content=data['content'],
            type=data['type'],
            created_by=current_user,
            audience=data.get('audience', 'all')
        )
        return jsonify(note.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/release-notes/<int:note_id>', methods=['PUT'])
@login_required
@developer_required
def update_release_note(note_id):
    """Update a release note (only for developers and admins)"""
    note = ReleaseNote.query.get_or_404(note_id)
    data = request.get_json()
    
    if 'type' in data and data['type'] not in ['feature', 'bug', 'improvement']:
        return jsonify({'error': 'Invalid note type'}), 400
    
    try:
        note.update(
            title=data.get('title'),
            content=data.get('content'),
            type=data.get('type')
        )
        return jsonify(note.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/release-notes/<int:note_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_release_note(note_id):
    """Delete a release note (only for admins)"""
    try:
        note = ReleaseNote.query.get_or_404(note_id)
        
        # Log the deletion attempt
        from flask import current_app
        current_app.logger.info(f"[Release Note] Attempting to delete release note ID: {note_id}, Title: {note.title}")
        
        note.delete()
        
        current_app.logger.info(f"[Release Note] Successfully deleted release note ID: {note_id}")
        return jsonify({'message': 'Release note deleted successfully'}), 200
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"[Release Note] Failed to delete release note ID: {note_id}: {str(e)}")
        return jsonify({'error': f'Failed to delete release note: {str(e)}'}), 500

@bp.route('/api/release-notes/<int:note_id>/read', methods=['POST'])
@login_required
def mark_as_read(note_id):
    """Mark a release note as read by the current user"""
    note = ReleaseNote.query.get_or_404(note_id)
    
    # Check if already read
    if UserReadNote.query.filter_by(user_id=current_user.user_id, release_note_id=note_id).first():
        return jsonify({'message': 'Already marked as read'}), 200
    
    try:
        read_note = UserReadNote(user_id=current_user.user_id, release_note_id=note_id)
        db.session.add(read_note)
        db.session.commit()
        return jsonify({'message': 'Marked as read'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/release-notes/<int:note_id>/dismiss', methods=['POST'])
@login_required
def dismiss_note(note_id):
    """Dismiss a release note for the current user (hide from their view)"""
    note = ReleaseNote.query.get_or_404(note_id)
    
    # Check if already dismissed
    if current_user.has_dismissed_note(note_id):
        return jsonify({'message': 'Already dismissed'}), 200
    
    try:
        current_user.add_dismissed_note(note_id)
        return jsonify({'message': 'Note dismissed successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/release-notes/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    """Get count of unread release notes for the current user (excluding dismissed notes)"""
    # Get dismissed note IDs from user's dismissed_notes field
    dismissed_note_ids = set(current_user.get_dismissed_notes())
    
    # Get total notes excluding dismissed ones
    total_notes = ReleaseNote.query.filter(~ReleaseNote.id.in_(dismissed_note_ids)).count()
    
    # Get read notes count (excluding dismissed ones)
    read_notes = UserReadNote.query.filter_by(user_id=current_user.user_id).count()
    
    return jsonify({
        'unread_count': total_notes - read_notes
    })

@bp.route('/api/release-notes/all', methods=['GET'])
@login_required
@developer_required
def get_all_release_notes():
    notes = ReleaseNote.query.order_by(ReleaseNote.created_at.desc()).all()
    return jsonify({'notes': [n.to_dict() for n in notes]}) 

@bp.route('/api/release-notes/invitation/<int:note_id>/read', methods=['POST'])
@login_required
def mark_invitation_note_read(note_id):
    """Mark invitation-related release note as read"""
    try:
        from models.user_read_note_model import UserReadNote
        from models.release_note_model import ReleaseNote
        
        # Check if release note exists
        release_note = ReleaseNote.query.get(note_id)
        if not release_note:
            return jsonify({"error": "Release note not found"}), 404
        
        # Check if user has access to this release note via invitation
        from controllers.workspace_member_controller import WorkspaceMemberController
        invitation_notes = WorkspaceMemberController.get_invitation_release_notes(current_user.user_id)
        
        has_access = any(note['id'] == note_id for note in invitation_notes)
        if not has_access:
            return jsonify({"error": "Access denied"}), 403
        
        # Mark as read
        existing_read = UserReadNote.query.filter_by(
            user_id=current_user.user_id,
            release_note_id=note_id
        ).first()
        
        if not existing_read:
            read_note = UserReadNote(
                user_id=current_user.user_id,
                release_note_id=note_id
            )
            db.session.add(read_note)
            db.session.commit()
        
        return jsonify({"message": "Release note marked as read"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to mark as read: {str(e)}"}), 500 