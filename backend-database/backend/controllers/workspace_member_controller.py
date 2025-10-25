from flask import jsonify, request
from flask_login import current_user
from models.workspace_model import Workspace
from models.workspace_member_model import WorkspaceMember
from models.workspace_invitation_model import WorkspaceInvitation
from models.workspace_activity_log_model import WorkspaceActivityLog
from models.user_model import User
from models.lead_model import db
import uuid
from datetime import datetime

class WorkspaceMemberController:
    """Controller for workspace member operations"""
    
    @staticmethod
    def get_workspace_members(workspace_id):
        """Get all members of a workspace"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user is member
            if not workspace.is_user_member(current_user.user_id):
                return {"error": "Access denied"}, 403
            
            # Get all active members
            members = workspace.get_members()
            
            # Get pending invitations
            pending_invitations = WorkspaceInvitation.get_pending_invitations(workspace.workspace_id)
            
            return {
                "members": [member.to_dict() for member in members],
                "pending_invitations": [inv.to_dict() for inv in pending_invitations]
            }, 200
            
        except Exception as e:
            return {"error": f"Failed to get workspace members: {str(e)}"}, 500
    
    @staticmethod
    def add_member(workspace_id, data):
        """Add a new member to workspace"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user can manage members
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can add members"}, 403
            
            # Get current user's member record to check specific permissions
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or not current_member.can_invite_members():
                return {"error": "You don't have permission to invite members"}, 403
            
            # Validate required fields
            if not data.get('email'):
                return {"error": "Email is required"}, 400
            
            email = data['email'].lower().strip()
            role = data.get('role', 'member')
            
            # Validate role based on current user's role
            current_user_role = current_member.role
            if current_user_role == 'admin':
                # Admins can add with any role
                if role not in ['admin', 'manager', 'member']:
                    return {"error": "Invalid role. Must be admin, manager, or member"}, 400
            elif current_user_role == 'manager':
                # Managers can only add members
                if role not in ['member']:
                    return {"error": "Managers can only add members"}, 403
            else:
                # Other roles shouldn't be able to add members (already checked by can_invite_members)
                return {"error": "You don't have permission to add members"}, 403
            
            # Check if user exists
            user = User.query.filter_by(email=email).first()
            if not user:
                return {"error": "User not found"}, 404
            
            # Check if user is already a member
            existing_member = WorkspaceMember.query.filter_by(
                workspace_id=workspace.workspace_id,
                user_id=user.user_id
            ).first()
            
            if existing_member:
                if existing_member.is_active:
                    return {"error": "User is already a member"}, 400
                else:
                    # Reactivate member with role validation
                    if current_user_role == 'manager' and existing_member.role in ['admin', 'manager']:
                        return {"error": "Managers cannot reactivate admin or manager accounts"}, 403
                    
                    # Reactivate member
                    existing_member.reactivate()
                    existing_member.change_role(role)
                    
                    # Log activity
                    WorkspaceActivityLog.log_member_added(
                        workspace_id=workspace.workspace_id,
                        member_id=existing_member.workspace_member_id,
                        user_id=current_user.user_id,
                        member_email=email,
                        role=role
                    )
                    
                    return existing_member.to_dict(), 200
            
            # Add new member
            member = WorkspaceMember.create(
                workspace_id=workspace.workspace_id,
                user_id=user.user_id,
                role=role
            )
            
            # Log activity
            WorkspaceActivityLog.log_member_added(
                workspace_id=workspace.workspace_id,
                member_id=member.workspace_member_id,
                user_id=current_user.user_id,
                member_email=email,
                role=role
            )
            
            return member.to_dict(), 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to add member: {str(e)}"}, 500
    
    @staticmethod
    def update_member_role(workspace_id, member_id, data):
        """Update member role"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user can manage members
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can update member roles"}, 403
            
            # Validate member_id
            try:
                member_uuid = uuid.UUID(member_id)
            except ValueError:
                return {"error": "Invalid member ID"}, 400
            
            member = WorkspaceMember.query.get(member_uuid)
            if not member or member.workspace_id != workspace.workspace_id:
                return {"error": "Member not found"}, 404
            
            # Validate new role
            new_role = data.get('role')
            if not new_role or new_role not in ['admin', 'manager', 'member']:
                return {"error": "Invalid role"}, 400
            
            # Prevent changing own role if not admin
            if member.user_id == current_user.user_id and not workspace.can_user_admin(current_user.user_id):
                return {"error": "Cannot change your own role"}, 403
            
            # Get old role for logging
            old_role = member.role
            
            # Update role
            member.change_role(new_role)
            
            # Get user email for logging
            user = member.get_user()
            user_email = user.email if user else "Unknown"
            
            # Log activity
            WorkspaceActivityLog.log_role_changed(
                workspace_id=workspace.workspace_id,
                member_id=member.workspace_member_id,
                user_id=current_user.user_id,
                member_email=user_email,
                old_role=old_role,
                new_role=new_role
            )
            
            return member.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to update member role: {str(e)}"}, 500
    
    @staticmethod
    def remove_member(workspace_id, member_id):
        """Remove member from workspace"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user can manage members
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can remove members"}, 403
            
            # Get current user's member record to check specific permissions
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or not current_member.can_remove_members():
                return {"error": "You don't have permission to remove members"}, 403
            
            # Validate member_id
            try:
                member_uuid = uuid.UUID(member_id)
            except ValueError:
                return {"error": "Invalid member ID"}, 400
            
            member = WorkspaceMember.query.get(member_uuid)
            if not member or member.workspace_id != workspace.workspace_id:
                return {"error": "Member not found"}, 404
            
            # Prevent removing yourself
            if member.user_id == current_user.user_id:
                return {"error": "Cannot remove yourself from workspace"}, 403
            
            # Get user email for logging
            user = member.get_user()
            user_email = user.email if user else "Unknown"
            
            # Log activity
            WorkspaceActivityLog.log_member_removed(
                workspace_id=workspace.workspace_id,
                member_id=member.workspace_member_id,
                user_id=current_user.user_id,
                member_email=user_email
            )
            
            # Deactivate member
            member.deactivate()
            
            return {"message": "Member removed successfully"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to remove member: {str(e)}"}, 500
    
    @staticmethod
    def invite_member(workspace_id, data):
        """Send invitation to join workspace"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user can manage members
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can send invitations"}, 403
            
            # Get current user's member record to check specific permissions
            current_member = workspace.get_member_by_user_id(current_user.user_id)
            if not current_member or not current_member.can_invite_members():
                return {"error": "You don't have permission to send invitations"}, 403
            
            # Validate required fields
            if not data.get('email'):
                return {"error": "Email is required"}, 400
            
            email = data['email'].lower().strip()
            role = data.get('role', 'member')
            expiry_days = data.get('expiry_days', 7)
            
            # Validate role based on inviter's role
            current_user_role = current_member.role
            if current_user_role == 'admin':
                # Admins can invite with any role
                if role not in ['admin', 'manager', 'member']:
                    return {"error": "Invalid role. Must be admin, manager, or member"}, 400
            elif current_user_role == 'manager':
                # Managers can only invite members
                if role not in ['member']:
                    return {"error": "Managers can only invite members"}, 403
            else:
                # Other roles shouldn't be able to invite (already checked by can_invite_members)
                return {"error": "You don't have permission to send invitations"}, 403
            
            # Check if user already exists and is a member
            user = User.query.filter_by(email=email).first()
            if user:
                existing_member = WorkspaceMember.query.filter_by(
                    workspace_id=workspace.workspace_id,
                    user_id=user.user_id,
                    is_active=True
                ).first()
                
                if existing_member:
                    return {"error": "User is already a member"}, 400
            
            # Check for existing pending invitation
            existing_invitation = WorkspaceInvitation.query.filter_by(
                workspace_id=workspace.workspace_id,
                email=email,
                status='pending'
            ).first()
            
            if existing_invitation:
                return {"error": "Invitation already sent to this email"}, 400
            
            # Create invitation
            invitation = WorkspaceInvitation.create(
                workspace_id=workspace.workspace_id,
                email=email,
                role=role,
                sent_by=current_user.user_id,
                expiry_days=expiry_days
            )
            
            # Log activity
            WorkspaceActivityLog.log_invitation_sent(
                workspace_id=workspace.workspace_id,
                invitation_id=invitation.invitation_id,
                user_id=current_user.user_id,
                email=email,
                role=role
            )
            
            # TODO: Send email invitation here
            
            return invitation.to_dict(), 201
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to send invitation: {str(e)}"}, 500
    
    @staticmethod
    def accept_invitation(token):
        """Accept workspace invitation"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Find invitation by token
            invitation = WorkspaceInvitation.get_by_token(token)
            if not invitation:
                return {"error": "Invalid or expired invitation"}, 404
            
            # Check if invitation is still pending
            if invitation.status != 'pending':
                return {"error": "Invitation has already been used or expired"}, 400
            
            # Check if invitation is expired
            if invitation.is_expired():
                invitation.status = 'expired'
                db.session.commit()
                return {"error": "Invitation has expired"}, 400
            
            # Accept invitation
            success, message = invitation.accept_invitation(current_user.user_id)
            
            if success:
                # If invitation has a release note, show it to the user
                if invitation.release_note_id:
                    from models.user_read_note_model import UserReadNote
                    # Check if user has already read this release note
                    existing_read = UserReadNote.query.filter_by(
                        user_id=current_user.user_id,
                        release_note_id=invitation.release_note_id
                    ).first()
                    
                    if not existing_read:
                        # Mark the release note as unread so it appears in notifications
                        # We don't create a read record, so it will show as unread
                        pass
                
                return {"message": "Invitation accepted successfully"}, 200
            else:
                return {"error": message}, 400
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to accept invitation: {str(e)}"}, 500
    
    @staticmethod
    def cancel_invitation(workspace_id, invitation_id):
        """Cancel pending invitation"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user can manage members
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can cancel invitations"}, 403
            
            # Validate invitation_id
            try:
                invitation_uuid = uuid.UUID(invitation_id)
            except ValueError:
                return {"error": "Invalid invitation ID"}, 400
            
            invitation = WorkspaceInvitation.query.get(invitation_uuid)
            if not invitation or invitation.workspace_id != workspace.workspace_id:
                return {"error": "Invitation not found"}, 404
            
            # Cancel invitation
            invitation.cancel_invitation()
            
            return {"message": "Invitation cancelled successfully"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to cancel invitation: {str(e)}"}, 500
    
    @staticmethod
    def resend_invitation(workspace_id, invitation_id):
        """Resend invitation"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user can manage members
            if not workspace.can_user_manage(current_user.user_id):
                return {"error": "Only admins and managers can resend invitations"}, 403
            
            # Validate invitation_id
            try:
                invitation_uuid = uuid.UUID(invitation_id)
            except ValueError:
                return {"error": "Invalid invitation ID"}, 400
            
            invitation = WorkspaceInvitation.query.get(invitation_uuid)
            if not invitation or invitation.workspace_id != workspace.workspace_id:
                return {"error": "Invitation not found"}, 404
            
            # Resend invitation
            invitation.resend_invitation()
            
            # TODO: Send email invitation here
            
            return invitation.to_dict(), 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to resend invitation: {str(e)}"}, 500

    @staticmethod
    def get_invitation(token):
        """Get invitation details by token"""
        try:
            # Find invitation by token
            invitation = WorkspaceInvitation.get_by_token(token)
            if not invitation:
                return {"error": "Invalid or expired invitation"}, 404
            
            # Get workspace details
            workspace = Workspace.query.get(invitation.workspace_id)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Prepare response data
            invitation_data = invitation.to_dict()
            invitation_data['workspace'] = workspace.to_dict()
            invitation_data['inviter'] = {
                'first_name': invitation.invited_by_email.split('@')[0] if invitation.invited_by_email else 'Unknown',
                'last_name': '',
                'email': invitation.invited_by_email
            }
            
            return invitation_data, 200
            
        except Exception as e:
            return {"error": f"Failed to get invitation details: {str(e)}"}, 500

    @staticmethod
    def decline_invitation(token):
        """Decline workspace invitation"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Find invitation by token
            invitation = WorkspaceInvitation.get_by_token(token)
            if not invitation:
                return {"error": "Invalid or expired invitation"}, 404
            
            # Check if invitation is still pending
            if invitation.status != 'pending':
                return {"error": "Invitation has already been used or expired"}, 400
            
            # Check if invitation is expired
            if invitation.is_expired():
                invitation.status = 'expired'
                db.session.commit()
                return {"error": "Invitation has expired"}, 400
            
            # Get reason from request
            data = request.get_json() or {}
            reason = data.get('reason', 'No reason provided')
            
            # Decline invitation
            invitation.status = 'declined'
            invitation.declined_at = datetime.utcnow()
            invitation.decline_reason = reason
            db.session.commit()
            
            # Log activity
            WorkspaceActivityLog.log_invitation_declined(
                workspace_id=invitation.workspace_id,
                invitation_id=invitation.invitation_id,
                user_id=current_user.user_id,
                email=invitation.email,
                reason=reason
            )
            
            return {"message": "Invitation declined successfully"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to decline invitation: {str(e)}"}, 500

    @staticmethod
    def leave_workspace(workspace_id):
        """Leave workspace (for members)"""
        try:
            if not current_user.is_authenticated:
                return {"error": "User must be authenticated"}, 401
            
            # Validate workspace_id
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except ValueError:
                return {"error": "Invalid workspace ID"}, 400
            
            workspace = Workspace.query.get(workspace_uuid)
            if not workspace:
                return {"error": "Workspace not found"}, 404
            
            # Check if user is a member
            member = WorkspaceMember.query.filter_by(
                workspace_id=workspace.workspace_id,
                user_id=current_user.user_id,
                is_active=True
            ).first()
            
            if not member:
                return {"error": "You are not a member of this workspace"}, 404
            
            # Check if user is admin - admins cannot leave if they are the only admin
            if member.role == 'admin':
                admin_count = WorkspaceMember.query.filter_by(
                    workspace_id=workspace.workspace_id,
                    role='admin',
                    is_active=True
                ).count()
                
                if admin_count <= 1:
                    return {"error": "Cannot leave workspace. You are the only admin. Please transfer admin rights to another member first."}, 403
            
            # Get user email for logging
            user = member.get_user()
            user_email = user.email if user else "Unknown"
            
            # Log activity before removing
            WorkspaceActivityLog.log_member_removed(
                workspace_id=workspace.workspace_id,
                member_id=member.workspace_member_id,
                user_id=current_user.user_id,
                member_email=user_email
            )
            
            # Deactivate member
            member.deactivate()
            
            return {"message": "You have successfully left the workspace"}, 200
            
        except Exception as e:
            db.session.rollback()
            return {"error": f"Failed to leave workspace: {str(e)}"}, 500 

    @staticmethod
    def get_invitation_release_notes(user_id):
        """Get release notes from invitations for a user"""
        try:
            from models.workspace_invitation_model import WorkspaceInvitation
            from models.release_note_model import ReleaseNote
            from models.user_read_note_model import UserReadNote
            
            # Get all accepted invitations for this user that have release notes
            accepted_invitations = WorkspaceInvitation.query.filter_by(
                email=current_user.email,
                status='accepted'
            ).filter(
                WorkspaceInvitation.release_note_id.isnot(None)
            ).all()
            
            invitation_release_notes = []
            for invitation in accepted_invitations:
                release_note = ReleaseNote.query.get(invitation.release_note_id)
                if release_note:
                    # Check if user has read this release note
                    read_record = UserReadNote.query.filter_by(
                        user_id=user_id,
                        release_note_id=release_note.id
                    ).first()
                    
                    note_data = release_note.to_dict()
                    note_data['read'] = read_record is not None
                    note_data['from_invitation'] = True
                    note_data['invitation_team'] = invitation.get_workspace().name if invitation.get_workspace() else 'Unknown Team'
                    
                    invitation_release_notes.append(note_data)
            
            return invitation_release_notes
            
        except Exception as e:
            return [] 