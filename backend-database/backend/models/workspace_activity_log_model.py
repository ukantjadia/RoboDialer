from models.lead_model import db
from datetime import datetime, timedelta
import uuid
import json
from sqlalchemy.dialects.postgresql import UUID

class WorkspaceActivityLog(db.Model):
    """Model for workspace activity logs"""
    __tablename__ = 'workspace_activity_logs'

    log_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=True)  # project, task, member, etc.
    entity_id = db.Column(UUID(as_uuid=True), nullable=True)
    changes = db.Column(db.Text, nullable=True)  # JSON string for changes made
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6

    def __repr__(self):
        return f'<WorkspaceActivityLog {self.action}>'

    def to_dict(self):
        """Convert WorkspaceActivityLog object to a dictionary."""
        user_data = None
        if self.user_id:
            from models.user_model import User
            user = User.query.get(self.user_id)
            if user:
                user_data = {
                    'user_id': str(user.user_id),
                    'username': user.username,
                    'email': user.email
                }

        return {
            'log_id': str(self.log_id),
            'workspace_id': str(self.workspace_id),
            'user_id': str(self.user_id) if self.user_id else None,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': str(self.entity_id) if self.entity_id else None,
            'changes': self.get_changes(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'ip_address': self.ip_address,
            'user_data': user_data
        }

    @staticmethod
    def create(workspace_id, action, user_id=None, entity_type=None, entity_id=None, 
               changes=None, ip_address=None):
        """Create a new activity log entry"""
        log = WorkspaceActivityLog(
            workspace_id=workspace_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address
        )
        
        if changes:
            log.set_changes(changes)
        
        db.session.add(log)
        db.session.commit()
        return log

    def get_workspace(self):
        """Get the workspace this log belongs to"""
        from models.workspace_model import Workspace
        return Workspace.query.get(self.workspace_id)

    def get_user(self):
        """Get the user who performed this action"""
        if self.user_id:
            from models.user_model import User
            return User.query.get(self.user_id)
        return None

    def get_changes(self):
        """Get changes as dictionary"""
        if not self.changes:
            return {}
        try:
            return json.loads(self.changes)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_changes(self, changes):
        """Set changes from dictionary"""
        self.changes = json.dumps(changes)
        db.session.commit()

    @staticmethod
    def log_project_created(workspace_id, project_id, user_id, project_name, ip_address=None):
        """Log project creation"""
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='project_created',
            user_id=user_id,
            entity_type='project',
            entity_id=project_id,
            changes={'project_name': project_name},
            ip_address=ip_address
        )

    @staticmethod
    def log_project_updated(workspace_id, project_id, user_id, changes, ip_address=None):
        """Log project update"""
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='project_updated',
            user_id=user_id,
            entity_type='project',
            entity_id=project_id,
            changes=changes,
            ip_address=ip_address
        )

    @staticmethod
    def log_project_member_left(workspace_id, project_id, user_id, member_email, project_name, ip_address=None):
        """Log project member leaving"""
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='project_member_left',
            user_id=user_id,
            entity_type='project',
            entity_id=project_id,
            changes={'member_email': member_email, 'project_name': project_name},
            ip_address=ip_address
        )

    @staticmethod
    def log_task_created(workspace_id, task_id, user_id, task_title, project_id, ip_address=None):
        """Log task creation"""
        changes = {'task_title': task_title}
        if project_id:
            changes['project_id'] = str(project_id)
        
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='task_created',
            user_id=user_id,
            entity_type='task',
            entity_id=task_id,
            changes=changes,
            ip_address=ip_address
        )

    @staticmethod
    def log_task_moved(workspace_id, task_id, user_id, from_column, to_column, ip_address=None):
        """Log task movement"""
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='task_moved',
            user_id=user_id,
            entity_type='task',
            entity_id=task_id,
            changes={'from_column': from_column, 'to_column': to_column},
            ip_address=ip_address
        )

    @staticmethod
    def log_member_added(workspace_id, member_id, user_id, member_email, role, ip_address=None):
        """Log member addition"""
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='member_added',
            user_id=user_id,
            entity_type='member',
            entity_id=member_id,
            changes={'member_email': member_email, 'role': role},
            ip_address=ip_address
        )

    @staticmethod
    def log_member_removed(workspace_id, member_id, user_id, member_email, ip_address=None):
        """Log member removal"""
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='member_removed',
            user_id=user_id,
            entity_type='member',
            entity_id=member_id,
            changes={'member_email': member_email},
            ip_address=ip_address
        )

    @staticmethod
    def log_role_changed(workspace_id, member_id, user_id, member_email, old_role, new_role, ip_address=None):
        """Log role change"""
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='role_changed',
            user_id=user_id,
            entity_type='member',
            entity_id=member_id,
            changes={'member_email': member_email, 'old_role': old_role, 'new_role': new_role},
            ip_address=ip_address
        )

    @staticmethod
    def log_invitation_sent(workspace_id, invitation_id, user_id, email, role, ip_address=None):
        """Log invitation sent"""
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='invitation_sent',
            user_id=user_id,
            entity_type='invitation',
            entity_id=invitation_id,
            changes={'email': email, 'role': role},
            ip_address=ip_address
        )

    @staticmethod
    def log_settings_updated(workspace_id, user_id, setting_category, changes, ip_address=None):
        """Log settings update"""
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='settings_updated',
            user_id=user_id,
            entity_type='settings',
            changes={'category': setting_category, 'changes': changes},
            ip_address=ip_address
        )

    @staticmethod
    def get_workspace_activity(workspace_id, limit=50, offset=0, action_filter=None, user_filter=None):
        """Get activity logs for a workspace with filters"""
        query = WorkspaceActivityLog.query.filter_by(workspace_id=workspace_id)
        
        if action_filter:
            query = query.filter(WorkspaceActivityLog.action == action_filter)
        
        if user_filter:
            query = query.filter(WorkspaceActivityLog.user_id == user_filter)
        
        return query.order_by(WorkspaceActivityLog.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def get_user_activity(user_id, limit=50, offset=0):
        """Get activity logs for a specific user"""
        return WorkspaceActivityLog.query.filter_by(user_id=user_id)\
            .order_by(WorkspaceActivityLog.created_at.desc())\
            .offset(offset).limit(limit).all()

    @staticmethod
    def cleanup_old_logs(days_to_keep=90):
        """Clean up old activity logs"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        deleted_count = WorkspaceActivityLog.query.filter(
            WorkspaceActivityLog.created_at < cutoff_date
        ).delete()
        db.session.commit()
        return deleted_count

    @staticmethod
    def log_invitation_declined(workspace_id, invitation_id, user_id, email, reason, ip_address=None):
        """Log invitation declined"""
        return WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='invitation_declined',
            user_id=user_id,
            entity_type='invitation',
            entity_id=invitation_id,
            changes={'email': email, 'reason': reason},
            ip_address=ip_address
        )
    
    @staticmethod
    def get_workspace_activity_paginated(workspace_id, page=1, per_page=20, action_filter=None, user_filter=None, entity_type_filter=None):
        """Get paginated activity logs for a workspace with filters"""
        query = WorkspaceActivityLog.query.filter_by(workspace_id=workspace_id)
        
        if action_filter:
            query = query.filter(WorkspaceActivityLog.action == action_filter)
        
        if user_filter:
            query = query.filter(WorkspaceActivityLog.user_id == user_filter)
        
        if entity_type_filter:
            query = query.filter(WorkspaceActivityLog.entity_type == entity_type_filter)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        logs = query.order_by(WorkspaceActivityLog.created_at.desc())\
            .offset((page - 1) * per_page)\
            .limit(per_page)\
            .all()
        
        # Create pagination object
        from flask_sqlalchemy import Pagination
        pagination = Pagination(
            query=query,
            page=page,
            per_page=per_page,
            total=total,
            items=logs
        )
        
        return pagination