from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum

class WorkspaceTask(db.Model):
    """Model for workspace tasks"""
    __tablename__ = 'workspace_tasks'

    task_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False)
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(SqlEnum('todo', 'in_progress', 'review', 'completed', name='task_status'), default='todo', nullable=False)
    priority = db.Column(SqlEnum('low', 'medium', 'high', 'urgent', name='task_priority'), default='medium', nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    assigned_to = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    estimated_hours = db.Column(db.Float, nullable=True)
    actual_hours = db.Column(db.Float, nullable=True)
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated tags
    parent_task_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspace_tasks.task_id', ondelete='SET NULL'), nullable=True)
    target_leads = db.Column(db.Integer, nullable=False, default=10)
    seen = db.Column(db.Boolean, default=False, nullable=False) # notification for team members whether they has seen the notif or not.

    def __repr__(self):
        return f'<WorkspaceTask {self.title}>'

    def to_dict(self, include_submissions=True, detailed_submissions=False):
        """Convert WorkspaceTask object to a dictionary."""
        assignee_data = None
        if self.assigned_to:
            from models.user_model import User
            assignee = User.query.get(self.assigned_to)
            if assignee:
                assignee_data = {
                    'user_id': str(assignee.user_id),
                    'username': assignee.username,
                    'email': assignee.email
                }
            else:
                # If assignee user not found, create a default structure
                assignee_data = {
                    'user_id': str(self.assigned_to),
                    'username': 'Unknown User',
                    'email': 'unknown@example.com'
                }

        task_dict = {
            'task_id': str(self.task_id),
            'workspace_id': str(self.workspace_id),
            'project_id': str(self.project_id) if self.project_id else None,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'assigned_to': str(self.assigned_to) if self.assigned_to else None,
            'assignee_data': assignee_data,
            'created_by': str(self.created_by),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completed_by': str(self.completed_by) if self.completed_by else None,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'tags': self.get_tags(),
            'parent_task_id': str(self.parent_task_id) if self.parent_task_id else None,
            'is_overdue': self.is_overdue(),
            'completion_percentage': self.get_completion_percentage(),
            'target_leads': self.target_leads,
            'seen': self.seen,
        }
        
        # Add submission data based on parameters
        if include_submissions:
            if detailed_submissions:
                # Include full submission details
                task_dict['submissions'] = {
                    'latest_submission': self.get_latest_submission().to_dict() if self.get_latest_submission() else None,
                    'all_submissions': [submission.to_dict() for submission in self.submissions],
                    'submissions_count': {
                        'total': len(self.submissions),
                        'pending': len([s for s in self.submissions if s.status == 'pending']),
                        'approved': len([s for s in self.submissions if s.status == 'approved']),
                        'rejected': len([s for s in self.submissions if s.status == 'rejected']),
                        'under_review': len([s for s in self.submissions if s.status == 'under_review'])
                    },
                    'has_pending_submission': self.has_pending_submission()
                }
            else:
                # Include summary only
                task_dict['submissions'] = self.get_submissions_summary()
        
        return task_dict

    @staticmethod
    def create(workspace_id, title, created_by, project_id=None, description=None, 
               status='todo', priority='medium', due_date=None, assigned_to=None,
               estimated_hours=None, tags=None, parent_task_id=None, target_leads=None):
        """Create a new workspace task"""
        task = WorkspaceTask(
            workspace_id=workspace_id,
            project_id=project_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            due_date=due_date,
            assigned_to=assigned_to,
            created_by=created_by,
            estimated_hours=estimated_hours,
            tags=','.join(tags) if tags else None,
            target_leads=target_leads,
            parent_task_id=parent_task_id
        )
        db.session.add(task)
        db.session.commit()

        # Log activity
        from models.workspace_activity_log_model import WorkspaceActivityLog
        WorkspaceActivityLog.log_task_created(
            workspace_id=workspace_id,
            task_id=task.task_id,
            user_id=created_by,
            task_title=title,
            project_id=project_id
        )

        return task

    def update(self, **kwargs):
        """Update task information"""
        changes = {}
        updated_by = kwargs.pop('updated_by', None)
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                old_value = getattr(self, key)
                if old_value != value:
                    changes[key] = {'old': old_value, 'new': value}
                    setattr(self, key, value)
        
        if changes:
            self.updated_at = datetime.utcnow()
            db.session.commit()

            # Log activity if status changed
            if 'status' in changes:
                from models.workspace_activity_log_model import WorkspaceActivityLog
                WorkspaceActivityLog.create(
                    workspace_id=self.workspace_id,
                    action='task_updated',
                    user_id=updated_by,
                    entity_type='task',
                    entity_id=self.task_id,
                    changes=changes
                )

        return self

    def complete_task(self, completed_by, actual_hours=None):
        """Mark task as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.completed_by = completed_by
        if actual_hours is not None:
            self.actual_hours = actual_hours
        db.session.commit()

        # Log activity
        from models.workspace_activity_log_model import WorkspaceActivityLog
        WorkspaceActivityLog.create(
            workspace_id=self.workspace_id,
            action='task_completed',
            user_id=completed_by,
            entity_type='task',
            entity_id=self.task_id,
            changes={'status': {'old': 'in_progress', 'new': 'completed'}}
        )

        return self

    def get_tags(self):
        """Get tags as list"""
        return self.tags.split(',') if self.tags else []

    def set_tags(self, tags):
        """Set tags from list"""
        self.tags = ','.join(tags) if tags else None
        db.session.commit()

    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status != 'completed':
            return datetime.utcnow() > self.due_date
        return False

    def get_completion_percentage(self):
        """Calculate task completion percentage"""
        if self.status == 'completed':
            return 100
        elif self.status == 'review':
            return 90
        elif self.status == 'in_progress':
            return 50
        return 0

    def get_subtasks(self):
        """Get all subtasks"""
        return WorkspaceTask.query.filter_by(parent_task_id=self.task_id).all()


    def get_submissions_summary(self):
        """Get summary of task submissions"""
        # Get the latest submission for this task
        latest_submission = None
        if self.submissions:
            latest_submission = max(self.submissions, key=lambda s: s.submitted_at)
        
        # Count submissions by status
        submissions_count = {
            'total': len(self.submissions),
            'pending': len([s for s in self.submissions if s.status == 'pending']),
            'approved': len([s for s in self.submissions if s.status == 'approved']),
            'rejected': len([s for s in self.submissions if s.status == 'rejected']),
            'under_review': len([s for s in self.submissions if s.status == 'under_review'])
        }
        
        return {
            'latest_submission': {
                'submission_id': str(latest_submission.submission_id),
                'submission_type': latest_submission.submission_type,
                'status': latest_submission.status,
                'submitted_at': latest_submission.submitted_at.isoformat(),
                'reviewed_at': latest_submission.reviewed_at.isoformat() if latest_submission.reviewed_at else None,
                'message': latest_submission.message,
                'notes': latest_submission.notes,
                'submitter': {
                    'user_id': str(latest_submission.submitter.user_id),
                    'username': latest_submission.submitter.username,
                    'email': latest_submission.submitter.email
                } if latest_submission.submitter else None,
                'reviewer': {
                    'user_id': str(latest_submission.reviewer.user_id),
                    'username': latest_submission.reviewer.username,
                    'email': latest_submission.reviewer.email
                } if latest_submission.reviewer else None
            } if latest_submission else None,
            'submissions_count': submissions_count,
            'has_pending_submission': submissions_count['pending'] > 0,
            'has_approved_submission': submissions_count['approved'] > 0,
            'last_submission_status': latest_submission.status if latest_submission else None
        }

    def get_submissions(self):
        """Get all submissions for this task"""
        return self.submissions

    def get_latest_submission(self):
        """Get the most recent submission for this task"""
        if self.submissions:
            return max(self.submissions, key=lambda s: s.submitted_at)
        return None

    def has_pending_submission(self):
        """Check if task has any pending submissions"""
        return any(s.status == 'pending' for s in self.submissions)

    def get_workspace(self):
        """Get the workspace this task belongs to"""
        from models.workspace_model import Workspace
        return Workspace.query.get(self.workspace_id)

    def get_project(self):
        """Get the project this task belongs to"""
        if self.project_id:
            from models.project_model import Project
            return Project.query.get(self.project_id)
        return None

    def get_assignee(self):
        """Get the assigned user"""
        if self.assigned_to:
            from models.user_model import User
            return User.query.get(self.assigned_to)
        return None

    def get_creator(self):
        """Get the user who created this task"""
        from models.user_model import User
        return User.query.get(self.created_by)

    def get_completer(self):
        """Get the user who completed this task"""
        if self.completed_by:
            from models.user_model import User
            return User.query.get(self.completed_by)
        return None

    def get_parent_task(self):
        """Get parent task if exists"""
        if self.parent_task_id:
            return WorkspaceTask.query.get(self.parent_task_id)
        return None

    @staticmethod
    def get_workspace_tasks(workspace_id, status=None, assigned_to=None, project_id=None):
        """Get tasks for a workspace with optional filters"""
        query = WorkspaceTask.query.filter_by(workspace_id=workspace_id)
        
        if status:
            query = query.filter_by(status=status)
        if assigned_to:
            query = query.filter_by(assigned_to=assigned_to)
        if project_id:
            query = query.filter_by(project_id=project_id)
            
        return query.order_by(WorkspaceTask.created_at.desc()).all()

    @staticmethod
    def get_user_tasks(user_id, workspace_id=None, status=None, seen=None):
        """Get tasks assigned to a user"""
        query = WorkspaceTask.query.filter_by(assigned_to=user_id)
        
        if workspace_id:
            query = query.filter_by(workspace_id=workspace_id)
        if status:
            query = query.filter_by(status=status)
        if isinstance(seen, bool):
            query = query.filter_by(seen=seen)
            
        return query.order_by(WorkspaceTask.due_date.asc()).all()

    @staticmethod
    def get_overdue_tasks(workspace_id=None):
        """Get overdue tasks"""
        query = WorkspaceTask.query.filter(
            WorkspaceTask.due_date < datetime.utcnow(),
            WorkspaceTask.status != 'completed'
        )
        
        if workspace_id:
            query = query.filter_by(workspace_id=workspace_id)
            
        return query.order_by(WorkspaceTask.due_date.asc()).all() 