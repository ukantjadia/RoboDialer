from models.lead_model import db
from datetime import datetime
import uuid
import json
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum

class WorkspaceMember(db.Model):
    """Model for workspace members with roles"""
    __tablename__ = 'workspace_members'

    workspace_member_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    role = db.Column(SqlEnum('admin', 'manager', 'member', name='workspace_role'), default='member', nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, nullable=True)
    permissions_json = db.Column(db.Text, default='{}')  # JSON string for custom permissions
    credits_allocated = db.Column(db.Integer, nullable=False, default=0)
    credits_used = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<WorkspaceMember {self.user_id} in {self.workspace_id}>'

    def to_dict(self):
        """Convert WorkspaceMember object to a dictionary."""
        user_data = None
        if self.user_id:
            from models.user_model import User
            user = User.query.get(self.user_id)
            if user:
                user_data = {
                    'user_id': str(user.user_id),
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'linkedin_url': user.linkedin_url
                }

        return {
            'workspace_member_id': str(self.workspace_member_id),
            'workspace_id': str(self.workspace_id),
            'user_id': str(self.user_id),
            'role': self.role,
            'is_active': self.is_active,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'permissions': self.get_permissions(),
            'credits_allocated': self.credits_allocated,
            'credits_used': self.credits_used,
            'user_data': user_data
        }

    @staticmethod
    def create(workspace_id, user_id, role='member', permissions=None):
        """Create a new workspace member"""
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role
        )
        if permissions:
            member.set_permissions(permissions)
        
        db.session.add(member)
        db.session.commit()
        return member

    def get_remaining_credits(self):
        """Calculates the credits this member has left in this workspace."""
        return self.credits_allocated - self.credits_used

    def update(self, **kwargs):
        """Update workspace member information"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
        return self

    def update_last_active(self):
        """Update last active timestamp"""
        self.last_active = datetime.utcnow()
        db.session.commit()

    def get_permissions(self):
        """Get permissions as dictionary"""
        if not self.permissions_json:
            return {}
        try:
            return json.loads(self.permissions_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_permissions(self, permissions):
        """Set permissions from dictionary"""
        self.permissions_json = json.dumps(permissions)
        db.session.commit()

    def has_permission(self, permission):
        """Check if member has specific permission"""
        permissions = self.get_permissions()
        return permissions.get(permission, False)

    def is_admin(self):
        """Check if member is admin"""
        return self.role == 'admin'

    def is_manager(self):
        """Check if member is manager"""
        return self.role == 'manager'

    def can_manage_members(self):
        """Check if member can manage other members"""
        return self.role in ['admin', 'manager']

    def can_manage_projects(self):
        """Check if member can manage projects"""
        return self.role in ['admin', 'manager']

    def can_manage_workspace(self):
        """Check if member can manage workspace settings"""
        return self.role == 'admin'

    def can_assign_credits(self):
        """Check if member can assign credits (only admins)"""
        return self.role == 'admin'

    def can_update_own_profile_only(self):
        """Check if member can only update their own profile (members)"""
        return self.role in ['member']

    def can_update_own_tasks_only(self):
        """Check if member can only update their own tasks (members)"""
        return self.role in ['member']

    def can_invite_members(self):
        """Check if member can invite other members"""
        return self.role in ['admin', 'manager']

    def can_remove_members(self):
        """Check if member can remove other members"""
        return self.role in ['admin', 'manager']

    def can_create_projects(self):
        """Check if member can create projects"""
        return self.role in ['admin', 'manager']

    def can_edit_projects(self):
        """Check if member can edit projects"""
        return self.role in ['admin', 'manager']

    def get_user(self):
        """Get the user object"""
        from models.user_model import User
        return User.query.get(self.user_id)

    def get_workspace(self):
        """Get the workspace object"""
        from models.workspace_model import Workspace
        return Workspace.query.get(self.workspace_id)

    def deactivate(self):
        """Deactivate this member"""
        self.is_active = False
        db.session.commit()

    def reactivate(self):
        """Reactivate this member"""
        self.is_active = True
        db.session.commit()

    def change_role(self, new_role):
        """Change member role"""
        if new_role not in ['admin', 'manager', 'member']:
            raise ValueError("Invalid role. Must be 'admin', 'manager', or 'member'")
        
        self.role = new_role
        db.session.commit()
        return self
    
    def get_credits_summary(self):
        """Get credits summary for this member"""
        from models.credits_log_model import CreditsLog
        return CreditsLog.get_user_credits_summary(self.user_id, self.workspace_id)
    
    def get_activity_summary(self, days=30):
        """Get activity summary for this member"""
        from models.workspace_activity_log_model import WorkspaceActivityLog
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        activities = WorkspaceActivityLog.query.filter(
            WorkspaceActivityLog.workspace_id == self.workspace_id,
            WorkspaceActivityLog.user_id == self.user_id,
            WorkspaceActivityLog.created_at >= cutoff_date
        ).all()
        
        return {
            'total_activities': len(activities),
            'activities_by_type': {},
            'recent_activities': [activity.to_dict() for activity in activities[:10]]
        }