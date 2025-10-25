from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum

class Project(db.Model):
    """Model for workspace projects"""
    __tablename__ = 'projects'

    project_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(SqlEnum('active', 'completed', 'archived', 'paused', name='project_status'), default='active', nullable=False)
    priority = db.Column(SqlEnum('low', 'medium', 'high', 'urgent', name='project_priority'), default='medium', nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    assigned_to = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    revenue = db.Column(db.Numeric(15, 2), default=0, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    employees = db.Column(db.Integer, default=0, nullable=True)
    progress = db.Column(db.Integer, default=0, nullable=True)

    def __repr__(self):
        return f'<Project {self.name}>'

    def to_dict(self):
        """Convert Project object to a dictionary."""
        return {
            'project_id': str(self.project_id),
            'workspace_id': str(self.workspace_id),
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': str(self.created_by) if self.created_by else None,
            'assigned_to': str(self.assigned_to) if self.assigned_to else None,
            'revenue': float(self.revenue) if self.revenue else 0,
            'location': self.location,
            'employees': self.employees or 0,
            'progress': self.progress or 0,
            'task_count': self.get_task_count(),
            'completed_task_count': self.get_completed_task_count(),
            'progress_percentage': self.get_progress_percentage()
        }

    @staticmethod
    def create(workspace_id, name, description=None, status='active', priority='medium',
               start_date=None, due_date=None, created_by=None, assigned_to=None,
               revenue=None, location=None, employees=None, progress=None):
        """Create a new project"""
        project = Project(
            workspace_id=workspace_id,
            name=name,
            description=description,
            status=status,
            priority=priority,
            start_date=start_date,
            due_date=due_date,
            created_by=created_by,
            assigned_to=assigned_to,
            revenue=revenue,
            location=location,
            employees=employees,
            progress=progress
        )
        db.session.add(project)
        return project

    def update(self, **kwargs):
        """Update project information"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def get_workspace(self):
        """Get the workspace this project belongs to"""
        from models.workspace_model import Workspace
        return Workspace.query.get(self.workspace_id)

    def get_creator(self):
        """Get the user who created this project"""
        if self.created_by:
            from models.user_model import User
            return User.query.get(self.created_by)
        return None

    def get_assigned_user(self):
        """Get the user assigned to this project"""
        if self.assigned_to:
            from models.user_model import User
            return User.query.get(self.assigned_to)
        return None

    def get_tasks(self):
        """Get all tasks for this project"""
        from models.workspace_task_model import WorkspaceTask
        return WorkspaceTask.query.filter_by(project_id=self.project_id).all()

    def get_task_count(self):
        """Get total task count"""
        from models.workspace_task_model import WorkspaceTask
        return WorkspaceTask.query.filter_by(project_id=self.project_id).count()

    def get_completed_task_count(self):
        """Get completed task count"""
        from models.workspace_task_model import WorkspaceTask
        return WorkspaceTask.query.filter_by(project_id=self.project_id, status='completed').count()

    def get_progress_percentage(self):
        """Calculate project progress percentage"""
        total_tasks = self.get_task_count()
        if total_tasks == 0:
            return 0
        
        completed_tasks = self.get_completed_task_count()
        return round((completed_tasks / total_tasks) * 100, 2)

    def is_overdue(self):
        """Check if project is overdue"""
        if not self.due_date:
            return False
        return datetime.now().date() > self.due_date and self.status != 'completed'

    def days_until_due(self):
        """Get days until due date"""
        if not self.due_date:
            return None
        delta = self.due_date - datetime.now().date()
        return delta.days

    def change_status(self, new_status):
        """Change project status"""
        if new_status not in ['active', 'completed', 'archived', 'paused']:
            raise ValueError("Invalid status")
        
        self.status = new_status
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def assign_to_user(self, user_id):
        """Assign project to a user"""
        self.assigned_to = user_id
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def unassign(self):
        """Unassign project from current user"""
        self.assigned_to = None
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self 