from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

class Workspace(db.Model):
    """Model for workspace"""
    __tablename__ = 'workspaces'

    workspace_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    domain = db.Column(db.String(100), nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    size = db.Column(db.String(50), nullable=True)  # small, medium, large
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    company_id = db.Column(UUID(as_uuid=True), db.ForeignKey('companies.company_id'), nullable=True)
    total_credit_pool = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<Workspace {self.name}>'

    def to_dict(self):
        """Convert Workspace object to a dictionary."""
        return {
            'workspace_id': str(self.workspace_id),
            'name': self.name,
            'description': self.description,
            'domain': self.domain,
            'industry': self.industry,
            'size': self.size,
            'is_active': self.is_active,
            'status': 'active' if self.is_active else 'inactive',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': str(self.created_by) if self.created_by else None,
            'company_id': str(self.company_id) if self.company_id else None,
            'member_count': self.get_member_count(),
            'project_count': self.get_project_count(),
            'total_credit_pool': self.total_credit_pool,
            'active_project_count': self.get_active_project_count()
        }

    @staticmethod
    def create(name, description=None, domain=None, industry=None, 
               size='medium', created_by=None, company_id=None, total_credit_pool=None):
        """Create a new workspace"""
        workspace = Workspace(
            name=name,
            description=description,
            domain=domain,
            industry=industry,
            size=size,
            created_by=created_by,
            total_credit_pool=total_credit_pool,
            company_id=company_id
        )
        db.session.add(workspace)
        db.session.commit()
        return workspace

    def update(self, **kwargs):
        """Update workspace information"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def get_members(self):
        """Get all workspace members"""
        from models.workspace_member_model import WorkspaceMember
        return WorkspaceMember.query.filter_by(workspace_id=self.workspace_id, is_active=True).all()

    def get_member_count(self):
        """Get current member count"""
        from models.workspace_member_model import WorkspaceMember
        return WorkspaceMember.query.filter_by(workspace_id=self.workspace_id, is_active=True).count()

    def get_admin_members(self):
        """Get workspace admin members"""
        from models.workspace_member_model import WorkspaceMember
        return WorkspaceMember.query.filter_by(
            workspace_id=self.workspace_id,
            role='admin',
            is_active=True
        ).all()

    def get_projects(self):
        """Get all projects in this workspace"""
        from models.project_model import Project
        return Project.query.filter_by(workspace_id=self.workspace_id).all()

    def get_project_count(self):
        """Get total project count"""
        from models.project_model import Project
        return Project.query.filter_by(workspace_id=self.workspace_id).count()

    def get_active_project_count(self):
        """Get active project count"""
        from models.project_model import Project
        return Project.query.filter_by(workspace_id=self.workspace_id, status='active').count()

    def get_company(self):
        """Get the company this workspace belongs to"""
        if self.company_id:
            from models.company_model import Company
            return Company.query.get(self.company_id)
        return None

    def get_creator(self):
        """Get the user who created this workspace"""
        if self.created_by:
            from models.user_model import User
            return User.query.get(self.created_by)
        return None

    def is_user_member(self, user_id):
        """Check if user is a member of this workspace"""
        from models.workspace_member_model import WorkspaceMember
        member = WorkspaceMember.query.filter_by(
            workspace_id=self.workspace_id,
            user_id=user_id,
            is_active=True
        ).first()
        return member is not None

    def get_user_role(self, user_id):
        """Get user's role in this workspace"""
        from models.workspace_member_model import WorkspaceMember
        member = WorkspaceMember.query.filter_by(
            workspace_id=self.workspace_id,
            user_id=user_id,
            is_active=True
        ).first()
        return member.role if member else None

    def can_user_manage(self, user_id):
        """Check if user can manage this workspace (admin or manager)"""
        role = self.get_user_role(user_id)
        return role in ['admin', 'manager']

    def can_user_admin(self, user_id):
        """Check if user is admin of this workspace"""
        role = self.get_user_role(user_id)
        return role == 'admin'

    def delete_workspace(self):
        """Delete this workspace and all related data"""
        # Delete all related data (cascade will handle most)
        db.session.delete(self)
        db.session.commit()
    
    def get_member_by_user_id(self, user_id):
        """Get workspace member by user ID"""
        from models.workspace_member_model import WorkspaceMember
        return WorkspaceMember.query.filter_by(
            workspace_id=self.workspace_id,
            user_id=user_id,
            is_active=True
        ).first()
    
    def get_project_by_id(self, project_id):
        """Get project by ID in this workspace"""
        from models.project_model import Project
        return Project.query.filter_by(
            workspace_id=self.workspace_id,
            project_id=project_id
        ).first()
    
    def get_settings(self):
        """Get workspace settings"""
        from models.workspace_settings_model import WorkspaceSettings
        return WorkspaceSettings.query.filter_by(workspace_id=self.workspace_id).first()
    
    def export_data(self, format='json'):
        """Export workspace data"""
        data = {
            'workspace': self.to_dict(),
            'members': [member.to_dict() for member in self.get_members()],
            'projects': [project.to_dict() for project in self.get_projects()],
            'settings': self.get_settings().to_dict() if self.get_settings() else {}
        }
        
        if format == 'json':
            return data, 200
        elif format == 'csv':
            # TODO: Implement CSV export
            return {"error": "CSV export not implemented yet"}, 501
        else:
            return {"error": "Invalid export format"}, 400
    
    def get_analytics(self):
        """Get workspace analytics and insights"""
        # Get basic statistics
        member_count = self.get_member_count()
        project_count = self.get_project_count()
        active_project_count = self.get_active_project_count()
        
        # Get recent activity
        from models.workspace_activity_log_model import WorkspaceActivityLog
        recent_activities = WorkspaceActivityLog.get_workspace_activity(
            workspace_id=self.workspace_id,
            limit=10
        )
        
        # Calculate task completion rate (placeholder)
        task_completion_rate = 75  # Placeholder
        
        analytics = {
            'metrics': {
                'member_count': member_count,
                'project_count': project_count,
                'active_project_count': active_project_count,
                'task_completion_rate': task_completion_rate
            },
            'task_completion_data': {
                'completed': 75,
                'in_progress': 20,
                'pending': 5
            },
            'project_status_data': {
                'active': active_project_count,
                'completed': project_count - active_project_count,
                'archived': 0
            },
            'team_performance_data': {
                'avg_task_completion_time': '2.5 days',
                'productivity_score': 85
            },
            'recent_activities': [log.to_dict() for log in recent_activities]
        }
        
        return analytics