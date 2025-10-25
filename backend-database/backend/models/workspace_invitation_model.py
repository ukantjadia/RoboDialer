from models.lead_model import db
from datetime import datetime, timedelta
import uuid
import secrets
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum

class WorkspaceInvitation(db.Model):
    """Model for workspace invitations"""
    __tablename__ = 'workspace_invitations'

    invitation_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(SqlEnum('admin', 'manager', 'member', name='invitation_role'), default='member', nullable=False)
    invitation_token = db.Column(db.String(255), unique=True, nullable=False)
    INVITATION_STATUSES = ['pending', 'accepted', 'expired', 'declined']
    status = db.Column(SqlEnum(*INVITATION_STATUSES, name='invitation_status', create_type=False), default='pending', nullable=False, server_default='pending')
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    sent_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    invited_by_email = db.Column(db.String(255), nullable=True)  # Email of the user who sent the invitation
    declined_at = db.Column(db.DateTime, nullable=True)
    decline_reason = db.Column(db.Text, nullable=True)
    release_note_id = db.Column(db.Integer, db.ForeignKey('release_notes.id'), nullable=True)  # Associated release note

    def __repr__(self):
        return f'<WorkspaceInvitation {self.email}>'

    def to_dict(self):
        """Convert WorkspaceInvitation object to a dictionary."""
        return {
            'invitation_id': str(self.invitation_id),
            'workspace_id': str(self.workspace_id),
            'email': self.email,
            'role': self.role,
            'invitation_token': self.invitation_token,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'sent_by': str(self.sent_by) if self.sent_by else None,
            'invited_by_email': self.invited_by_email,
            'declined_at': self.declined_at.isoformat() if self.declined_at else None,
            'decline_reason': self.decline_reason,
            'release_note_id': self.release_note_id,
            'is_expired': self.is_expired(),
            'days_until_expiry': self.days_until_expiry()
        }

    @staticmethod
    def create(workspace_id, email, role='member', sent_by=None, expiry_days=7, release_note_id=None):
        """Create a new workspace invitation"""
        # Generate unique invitation token
        invitation_token = secrets.token_urlsafe(32)
        
        # Set expiry date
        expires_at = datetime.utcnow() + timedelta(days=expiry_days)
        
        # Get inviter email
        invited_by_email = None
        if sent_by:
            from models.user_model import User
            inviter = User.query.get(sent_by)
            if inviter:
                invited_by_email = inviter.email
        
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=email,
            role=role,
            invitation_token=invitation_token,
            expires_at=expires_at,
            sent_by=sent_by,
            invited_by_email=invited_by_email,
            release_note_id=release_note_id
        )
        db.session.add(invitation)
        db.session.commit()
        return invitation

    def update(self, **kwargs):
        """Update invitation information"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self

    def get_workspace(self):
        """Get the workspace this invitation is for"""
        from models.workspace_model import Workspace
        return Workspace.query.get(self.workspace_id)

    def get_sent_by_user(self):
        """Get the user who sent this invitation"""
        if self.sent_by:
            from models.user_model import User
            return User.query.get(self.sent_by)
        return None

    def is_expired(self):
        """Check if invitation is expired"""
        return datetime.utcnow() > self.expires_at

    def days_until_expiry(self):
        """Get days until invitation expires"""
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    def accept_invitation(self, user_id):
        """Accept invitation and add user to workspace"""
        if self.status != 'pending':
            return False, "Invitation is not pending"
        
        if self.is_expired():
            self.status = 'expired'
            db.session.commit()
            return False, "Invitation has expired"
        
        # Add user to workspace
        from models.workspace_member_model import WorkspaceMember
        try:
            member = WorkspaceMember.create(
                workspace_id=self.workspace_id,
                user_id=user_id,
                role=self.role
            )
            
            # Mark invitation as accepted
            self.status = 'accepted'
            db.session.commit()
            
            return True, "Invitation accepted successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to accept invitation: {str(e)}"

    def resend_invitation(self, expiry_days=7):
        """Resend invitation with new token and expiry"""
        # Generate new token
        self.invitation_token = secrets.token_urlsafe(32)
        
        # Set new expiry date
        self.expires_at = datetime.utcnow() + timedelta(days=expiry_days)
        
        # Reset status to pending
        self.status = 'pending'
        
        # Update sent_at
        self.sent_at = datetime.utcnow()
        
        db.session.commit()
        return self

    def cancel_invitation(self):
        """Cancel invitation"""
        self.status = 'expired'
        db.session.commit()
        return self

    def extend_expiry(self, additional_days=7):
        """Extend invitation expiry date"""
        self.expires_at = datetime.utcnow() + timedelta(days=additional_days)
        db.session.commit()
        return self

    def save(self):
        """Save the invitation to database"""
        try:
            # Validate status before saving
            if self.status not in self.INVITATION_STATUSES:
                raise ValueError(f"Invalid status '{self.status}'. Must be one of: {', '.join(self.INVITATION_STATUSES)}")
            
            db.session.commit()
            return self
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to save invitation: {str(e)}")

    @staticmethod
    def get_by_token(token):
        """Get invitation by token"""
        return WorkspaceInvitation.query.filter_by(invitation_token=token).first()

    @staticmethod
    def get_pending_invitations(workspace_id):
        """Get all pending invitations for a workspace"""
        return WorkspaceInvitation.query.filter_by(
            workspace_id=workspace_id,
            status='pending'
        ).all()

    @staticmethod
    def cleanup_expired_invitations():
        """Clean up expired invitations"""
        expired_invitations = WorkspaceInvitation.query.filter(
            WorkspaceInvitation.status == 'pending',
            WorkspaceInvitation.expires_at < datetime.utcnow()
        ).all()
        
        for invitation in expired_invitations:
            invitation.status = 'expired'
        
        db.session.commit()
        return len(expired_invitations) 