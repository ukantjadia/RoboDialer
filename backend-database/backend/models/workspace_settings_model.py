from models.lead_model import db
from datetime import datetime
import uuid
import json
from sqlalchemy.dialects.postgresql import UUID

class WorkspaceSettings(db.Model):
    """Model for workspace settings"""
    __tablename__ = 'workspace_settings'

    settings_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False, unique=True)
    general_settings = db.Column(db.Text, default='{}')  # JSON string for general settings
    notification_settings = db.Column(db.Text, default='{}')  # JSON string for notification settings
    security_settings = db.Column(db.Text, default='{}')  # JSON string for security settings
    integration_settings = db.Column(db.Text, default='{}')  # JSON string for integration settings
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)

    def __repr__(self):
        return f'<WorkspaceSettings {self.workspace_id}>'

    def to_dict(self):
        """Convert WorkspaceSettings object to a dictionary."""
        return {
            'settings_id': str(self.settings_id),
            'workspace_id': str(self.workspace_id),
            'general_settings': self.get_general_settings(),
            'notification_settings': self.get_notification_settings(),
            'security_settings': self.get_security_settings(),
            'integration_settings': self.get_integration_settings(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': str(self.updated_by) if self.updated_by else None
        }

    @staticmethod
    def create(workspace_id, general_settings=None, notification_settings=None, 
               security_settings=None, integration_settings=None, updated_by=None):
        """Create new workspace settings"""
        settings = WorkspaceSettings(
            workspace_id=workspace_id,
            updated_by=updated_by
        )
        
        if general_settings:
            settings.set_general_settings(general_settings)
        if notification_settings:
            settings.set_notification_settings(notification_settings)
        if security_settings:
            settings.set_security_settings(security_settings)
        if integration_settings:
            settings.set_integration_settings(integration_settings)
        
        db.session.add(settings)
        db.session.commit()
        return settings

    def update(self, **kwargs):
        """Update workspace settings"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def get_workspace(self):
        """Get the workspace these settings belong to"""
        from models.workspace_model import Workspace
        return Workspace.query.get(self.workspace_id)

    def get_updated_by_user(self):
        """Get the user who last updated these settings"""
        if self.updated_by:
            from models.user_model import User
            return User.query.get(self.updated_by)
        return None

    def get_general_settings(self):
        """Get general settings as dictionary"""
        if not self.general_settings:
            return self.get_default_general_settings()
        try:
            return json.loads(self.general_settings)
        except (json.JSONDecodeError, TypeError):
            return self.get_default_general_settings()

    def set_general_settings(self, settings):
        """Set general settings from dictionary"""
        self.general_settings = json.dumps(settings)
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def get_notification_settings(self):
        """Get notification settings as dictionary"""
        if not self.notification_settings:
            return self.get_default_notification_settings()
        try:
            return json.loads(self.notification_settings)
        except (json.JSONDecodeError, TypeError):
            return self.get_default_notification_settings()

    def set_notification_settings(self, settings):
        """Set notification settings from dictionary"""
        self.notification_settings = json.dumps(settings)
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def get_security_settings(self):
        """Get security settings as dictionary"""
        if not self.security_settings:
            return self.get_default_security_settings()
        try:
            return json.loads(self.security_settings)
        except (json.JSONDecodeError, TypeError):
            return self.get_default_security_settings()

    def set_security_settings(self, settings):
        """Set security settings from dictionary"""
        self.security_settings = json.dumps(settings)
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def get_integration_settings(self):
        """Get integration settings as dictionary"""
        if not self.integration_settings:
            return self.get_default_integration_settings()
        try:
            return json.loads(self.integration_settings)
        except (json.JSONDecodeError, TypeError):
            return self.get_default_integration_settings()

    def set_integration_settings(self, settings):
        """Set integration settings from dictionary"""
        self.integration_settings = json.dumps(settings)
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def get_default_general_settings(self):
        """Get default general settings"""
        return {
            'workspace_name': '',
            'description': '',
            'timezone': 'UTC',
            'date_format': 'YYYY-MM-DD',
            'time_format': '24h',
            'language': 'en',
            'theme': 'light',
            'auto_archive_completed_tasks': True,
            'auto_archive_days': 30
        }

    def get_default_notification_settings(self):
        """Get default notification settings"""
        return {
            'email_notifications': True,
            'task_assignments': True,
            'task_comments': True,
            'task_due_dates': True,
            'project_updates': True,
            'member_invitations': True,
            'daily_digest': False,
            'weekly_summary': True
        }

    def get_default_security_settings(self):
        """Get default security settings"""
        return {
            'require_two_factor': False,
            'session_timeout_minutes': 480,  # 8 hours
            'max_login_attempts': 5,
            'password_min_length': 8,
            'require_strong_password': False,
            'ip_whitelist': [],
            'audit_log_enabled': True
        }

    def get_default_integration_settings(self):
        """Get default integration settings"""
        return {
            'slack_integration': {
                'enabled': False,
                'webhook_url': '',
                'notifications': {
                    'task_assignments': True,
                    'task_comments': True,
                    'project_updates': True
                }
            },
            'github_integration': {
                'enabled': False,
                'repository': '',
                'branch': 'main'
            },
            'google_calendar': {
                'enabled': False,
                'calendar_id': ''
            }
        }

    def update_setting(self, category, key, value, updated_by=None):
        """Update a specific setting"""
        if category == 'general':
            settings = self.get_general_settings()
            settings[key] = value
            self.set_general_settings(settings)
        elif category == 'notification':
            settings = self.get_notification_settings()
            settings[key] = value
            self.set_notification_settings(settings)
        elif category == 'security':
            settings = self.get_security_settings()
            settings[key] = value
            self.set_security_settings(settings)
        elif category == 'integration':
            settings = self.get_integration_settings()
            settings[key] = value
            self.set_integration_settings(settings)
        
        if updated_by:
            self.updated_by = updated_by
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self
    
    def reset_to_default(self):
        """Reset all settings to default values"""
        self.general_settings = json.dumps(self.get_default_general_settings())
        self.notification_settings = json.dumps(self.get_default_notification_settings())
        self.security_settings = json.dumps(self.get_default_security_settings())
        self.integration_settings = json.dumps(self.get_default_integration_settings())
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self