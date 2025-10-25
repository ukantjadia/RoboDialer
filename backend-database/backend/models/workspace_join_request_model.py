from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum

class WorkspaceJoinRequest(db.Model):
    """Model for workspace join requests"""
    __tablename__ = 'workspace_join_requests'

    request_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    requested_role = db.Column(SqlEnum('manager', 'member', name='requested_role'), default='member', nullable=False)
    message = db.Column(db.Text, nullable=True)  # Optional message from requester
    status = db.Column(SqlEnum('pending', 'approved', 'rejected', 'cancelled', name='join_request_status'), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)  # Admin/manager who reviewed
    reviewed_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<WorkspaceJoinRequest {self.user_id} -> {self.workspace_id}>'

    def to_dict(self):
        """Convert WorkspaceJoinRequest object to a dictionary."""
        user_data = None
        if self.user_id:
            from models.user_model import User
            user = User.query.get(self.user_id)
            if user:
                user_data = {
                    'user_id': str(user.user_id),
                    'username': user.username,
                    'email': user.email,
                    'linkedin_url': user.linkedin_url
                }

        workspace_data = None
        if self.workspace_id:
            from models.workspace_model import Workspace
            workspace = Workspace.query.get(self.workspace_id)
            if workspace:
                workspace_data = {
                    'workspace_id': str(workspace.workspace_id),
                    'name': workspace.name,
                    'description': workspace.description,
                    'industry': workspace.industry
                }

        reviewer_data = None
        if self.reviewed_by:
            from models.user_model import User
            reviewer = User.query.get(self.reviewed_by)
            if reviewer:
                reviewer_data = {
                    'user_id': str(reviewer.user_id),
                    'username': reviewer.username,
                    'email': reviewer.email
                }

        return {
            'request_id': str(self.request_id),
            'workspace_id': str(self.workspace_id),
            'user_id': str(self.user_id),
            'requested_role': self.requested_role,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'reviewed_by': str(self.reviewed_by) if self.reviewed_by else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'rejection_reason': self.rejection_reason,
            'user_data': user_data,
            'workspace_data': workspace_data,
            'reviewer_data': reviewer_data
        }

    @staticmethod
    def create(workspace_id, user_id, requested_role='member', message=None):
        """Create a new join request"""
        # Check if there's already a pending request
        existing_request = WorkspaceJoinRequest.query.filter_by(
            workspace_id=workspace_id,
            user_id=user_id,
            status='pending'
        ).first()
        
        if existing_request:
            return None, "You already have a pending request for this workspace"
        
        # Check if user is already a member
        from models.workspace_member_model import WorkspaceMember
        existing_member = WorkspaceMember.query.filter_by(
            workspace_id=workspace_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if existing_member:
            return None, "You are already a member of this workspace"
        
        request = WorkspaceJoinRequest(
            workspace_id=workspace_id,
            user_id=user_id,
            requested_role=requested_role,
            message=message
        )
        db.session.add(request)
        db.session.commit()
        return request, "Join request created successfully"

    def approve(self, reviewed_by):
        """Approve the join request and add user to workspace"""
        if self.status != 'pending':
            return False, "Request is not pending"
        
        try:
            # Add user to workspace
            from models.workspace_member_model import WorkspaceMember
            member = WorkspaceMember.create(
                workspace_id=self.workspace_id,
                user_id=self.user_id,
                role=self.requested_role
            )
            
            # Update request status
            self.status = 'approved'
            self.reviewed_by = reviewed_by
            self.reviewed_at = datetime.utcnow()
            db.session.commit()
            
            # Log activity
            from models.workspace_activity_log_model import WorkspaceActivityLog
            WorkspaceActivityLog.create(
                workspace_id=self.workspace_id,
                action='join_request_approved',
                user_id=reviewed_by,
                entity_type='join_request',
                entity_id=self.request_id,
                changes={
                    'requester_email': self.get_user().email if self.get_user() else 'Unknown',
                    'requested_role': self.requested_role
                }
            )
            
            return True, "Join request approved successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to approve request: {str(e)}"

    def reject(self, reviewed_by, reason=None):
        """Reject the join request"""
        if self.status != 'pending':
            return False, "Request is not pending"
        
        self.status = 'rejected'
        self.reviewed_by = reviewed_by
        self.reviewed_at = datetime.utcnow()
        self.rejection_reason = reason
        db.session.commit()
        
        # Log activity
        from models.workspace_activity_log_model import WorkspaceActivityLog
        WorkspaceActivityLog.create(
            workspace_id=self.workspace_id,
            action='join_request_rejected',
            user_id=reviewed_by,
            entity_type='join_request',
            entity_id=self.request_id,
            changes={
                'requester_email': self.get_user().email if self.get_user() else 'Unknown',
                'requested_role': self.requested_role,
                'reason': reason
            }
        )
        
        return True, "Join request rejected"

    def cancel(self):
        """Cancel the join request (by the requester)"""
        if self.status != 'pending':
            return False, "Request is not pending"
        
        self.status = 'cancelled'
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True, "Join request cancelled"

    def get_user(self):
        """Get the user who made this request"""
        from models.user_model import User
        return User.query.get(self.user_id)

    def get_workspace(self):
        """Get the workspace this request is for"""
        from models.workspace_model import Workspace
        return Workspace.query.get(self.workspace_id)

    def get_reviewer(self):
        """Get the user who reviewed this request"""
        if self.reviewed_by:
            from models.user_model import User
            return User.query.get(self.reviewed_by)
        return None

    @staticmethod
    def get_pending_requests(workspace_id):
        """Get all pending requests for a workspace"""
        return WorkspaceJoinRequest.query.filter_by(
            workspace_id=workspace_id,
            status='pending'
        ).order_by(WorkspaceJoinRequest.created_at.desc()).all()

    @staticmethod
    def get_user_requests(user_id, status=None):
        """Get all requests made by a user"""
        query = WorkspaceJoinRequest.query.filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(WorkspaceJoinRequest.created_at.desc()).all() 