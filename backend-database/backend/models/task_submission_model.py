from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum

class TaskSubmission(db.Model):
    """Model for task submissions to notify managers and admins"""
    __tablename__ = 'task_submissions'

    submission_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspace_tasks.task_id', ondelete='CASCADE'), nullable=False, index=True)
    workspace_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id', ondelete='CASCADE'), nullable=False)
    submitted_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    submission_type = db.Column(SqlEnum('completion', 'review', 'approval', 'update', name='submission_type'), default='completion', nullable=False)
    status = db.Column(SqlEnum('pending', 'approved', 'rejected', 'under_review', name='submission_status'), default='pending', nullable=False)
    message = db.Column(db.Text, nullable=True)  # Additional message from submitter
    notes = db.Column(db.Text, nullable=True)  # Notes from reviewer/admin
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    
    # Relationships
    task = db.relationship('WorkspaceTask', backref='submissions')
    workspace = db.relationship('Workspace', backref='task_submissions')
    submitter = db.relationship('User', foreign_keys=[submitted_by], backref='submitted_tasks')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_submissions')

    def __repr__(self):
        return f'<TaskSubmission {self.submission_id} - {self.submission_type}>'

    def to_dict(self):
        """Convert TaskSubmission object to a dictionary."""
        return {
            'submission_id': str(self.submission_id),
            'task_id': str(self.task_id),
            'workspace_id': str(self.workspace_id),
            'submitted_by': str(self.submitted_by),
            'submission_type': self.submission_type,
            'status': self.status,
            'message': self.message,
            'notes': self.notes,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': str(self.reviewed_by) if self.reviewed_by else None,
            'task': self.task.to_dict() if self.task else None,
            'submitter': {
                'user_id': str(self.submitter.user_id),
                'username': self.submitter.username,
                'email': self.submitter.email
            } if self.submitter else None,
            'reviewer': {
                'user_id': str(self.reviewer.user_id),
                'username': self.reviewer.username,
                'email': self.reviewer.email
            } if self.reviewer else None
        }

    @staticmethod
    def create(task_id, workspace_id, submitted_by, submission_type='completion', message=None):
        """Create a new task submission"""
        submission = TaskSubmission(
            task_id=task_id,
            workspace_id=workspace_id,
            submitted_by=submitted_by,
            submission_type=submission_type,
            message=message
        )
        db.session.add(submission)
        db.session.commit()
        
        # Log activity
        from models.workspace_activity_log_model import WorkspaceActivityLog
        WorkspaceActivityLog.create(
            workspace_id=workspace_id,
            action='task_submitted',
            user_id=submitted_by,
            entity_type='task',
            entity_id=task_id,
            changes={
                'submission_type': submission_type,
                'message': message
            }
        )
        
        return submission

    @staticmethod
    def get_pending_submissions(workspace_id):
        """Get all pending submissions for a workspace"""
        return TaskSubmission.query.filter_by(
            workspace_id=workspace_id,
            status='pending'
        ).order_by(TaskSubmission.submitted_at.desc()).all()

    @staticmethod
    def get_submissions_by_user(user_id, workspace_id=None):
        """Get submissions by a specific user"""
        query = TaskSubmission.query.filter_by(submitted_by=user_id)
        if workspace_id:
            query = query.filter_by(workspace_id=workspace_id)
        return query.order_by(TaskSubmission.submitted_at.desc()).all()

    @staticmethod
    def get_submissions_for_review(workspace_id):
        """Get submissions that need review (pending and under_review)"""
        return TaskSubmission.query.filter(
            TaskSubmission.workspace_id == workspace_id,
            TaskSubmission.status.in_(['pending', 'under_review'])
        ).order_by(TaskSubmission.submitted_at.desc()).all()

    def approve(self, reviewed_by, notes=None):
        """Approve this submission"""
        self.status = 'approved'
        self.reviewed_by = reviewed_by
        self.reviewed_at = datetime.utcnow()
        self.notes = notes
        db.session.commit()
        
        # Log activity
        from models.workspace_activity_log_model import WorkspaceActivityLog
        WorkspaceActivityLog.create(
            workspace_id=self.workspace_id,
            action='task_submission_approved',
            user_id=reviewed_by,
            entity_type='task',
            entity_id=self.task_id,
            changes={
                'submission_id': str(self.submission_id),
                'notes': notes
            }
        )
        
        return self

    def reject(self, reviewed_by, notes=None):
        """Reject this submission"""
        self.status = 'rejected'
        self.reviewed_by = reviewed_by
        self.reviewed_at = datetime.utcnow()
        self.notes = notes
        db.session.commit()
        
        # Log activity
        from models.workspace_activity_log_model import WorkspaceActivityLog
        WorkspaceActivityLog.create(
            workspace_id=self.workspace_id,
            action='task_submission_rejected',
            user_id=reviewed_by,
            entity_type='task',
            entity_id=self.task_id,
            changes={
                'submission_id': str(self.submission_id),
                'notes': notes
            }
        )
        
        return self

    def mark_under_review(self, reviewed_by):
        """Mark submission as under review"""
        self.status = 'under_review'
        self.reviewed_by = reviewed_by
        self.reviewed_at = datetime.utcnow()
        db.session.commit()
        
        return self 