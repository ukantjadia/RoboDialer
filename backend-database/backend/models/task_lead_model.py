from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

class TaskLead(db.Model):
    """Model for task-lead relationships"""
    __tablename__ = 'task_leads'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspace_tasks.task_id', ondelete='CASCADE'), nullable=False, index=True)
    lead_id = db.Column(db.String(100), db.ForeignKey('leads.lead_id', ondelete='CASCADE'), nullable=False)
    added_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)  # Additional notes about this lead for this task
    status = db.Column(db.String(50), default='active')  # active, contacted, qualified, converted, etc.
    
    # Scoring fields
    score = db.Column(db.String(20), nullable=True)  # 'good', 'medium', 'bad'
    score_notes = db.Column(db.Text, nullable=True)  # Notes about the score
    scored_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    scored_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship to get the actual lead and task objects
    task = db.relationship('WorkspaceTask', backref='task_leads')
    lead = db.relationship('Lead', backref='task_leads')
    user = db.relationship('User', foreign_keys=[added_by], backref='added_task_leads')
    scorer = db.relationship('User', foreign_keys=[scored_by], backref='scored_task_leads')

    def __repr__(self):
        return f'<TaskLead {self.task_id} -> {self.lead_id}>'

    def to_dict(self):
        """Convert TaskLead object to a dictionary."""
        try:
            result = {
                'id': str(self.id),
                'task_id': str(self.task_id),
                'lead_id': self.lead_id,
                'added_by': str(self.added_by),
                'added_at': self.added_at.isoformat() if self.added_at else None,
                'notes': self.notes,
                'status': self.status,
                'score': self.score,
                'score_notes': self.score_notes,
                'scored_by': str(self.scored_by) if self.scored_by else None,
                'scored_at': self.scored_at.isoformat() if self.scored_at else None,
            }
            
            # Safely add lead data
            try:
                result['lead'] = self.lead.to_dict() if self.lead else None
            except Exception as e:
                print(f"Error loading lead data: {e}")
                result['lead'] = None
            
            # Safely add user data
            try:
                result['user'] = {
                    'user_id': str(self.user.user_id),
                    'username': self.user.username,
                    'email': self.user.email
                } if self.user else None
            except Exception as e:
                print(f"Error loading user data: {e}")
                result['user'] = None
            
            # Safely add scorer data
            try:
                result['scorer'] = {
                    'user_id': str(self.scorer.user_id),
                    'username': self.scorer.username,
                    'email': self.scorer.email
                } if self.scorer else None
            except Exception as e:
                print(f"Error loading scorer data: {e}")
                result['scorer'] = None
                
            return result
            
        except Exception as e:
            print(f"Error in to_dict: {e}")
            # Return minimal data if everything fails
            return {
                'id': str(self.id) if hasattr(self, 'id') else None,
                'task_id': str(self.task_id) if hasattr(self, 'task_id') else None,
                'lead_id': self.lead_id if hasattr(self, 'lead_id') else None,
                'error': 'Failed to serialize task lead data'
            }



    @staticmethod
    def create(task_id, lead_id, added_by, notes=None, status='active'):
        """Create a new task-lead relationship"""
        task_lead = TaskLead(
            task_id=task_id,
            lead_id=lead_id,
            added_by=added_by,
            notes=notes,
            status=status
        )
        db.session.add(task_lead)
        db.session.commit()
        return task_lead

    @staticmethod
    def get_task_leads(task_id):
        """Get all leads for a specific task"""
        return TaskLead.query.filter_by(task_id=task_id).order_by(TaskLead.added_at.desc()).all()

    @staticmethod
    def get_lead_tasks(lead_id):
        """Get all tasks for a specific lead"""
        return TaskLead.query.filter_by(lead_id=lead_id).order_by(TaskLead.added_at.desc()).all()

    @staticmethod
    def get_project_task_leads(project_id):
        """Get all task leads from all tasks in a project"""
        from sqlalchemy.orm import joinedload
        from models.workspace_task_model import WorkspaceTask
        
        try:
            # Get all tasks in the project
            tasks = WorkspaceTask.query.filter_by(project_id=project_id).all()
            task_ids = [task.task_id for task in tasks]
            
            if not task_ids:
                return []
            
            # Get all task leads for these tasks with eager loading
            return TaskLead.query.options(
                joinedload(TaskLead.lead),
                joinedload(TaskLead.user),
                joinedload(TaskLead.scorer)
            ).filter(TaskLead.task_id.in_(task_ids)).order_by(TaskLead.added_at.desc()).all()
            
        except Exception as e:
            print(f"Error in get_project_task_leads: {e}")
            return []

    @staticmethod
    def get_workspace_task_leads(workspace_id):
        """Get all task leads from all tasks in a workspace"""
        from sqlalchemy.orm import joinedload
        from models.workspace_task_model import WorkspaceTask
        
        try:
            # Get all tasks in the workspace
            tasks = WorkspaceTask.query.filter_by(workspace_id=workspace_id).all()
            task_ids = [task.task_id for task in tasks]
            
            if not task_ids:
                return []
            
            # Get all task leads for these tasks with eager loading
            return TaskLead.query.options(
                joinedload(TaskLead.lead),
                joinedload(TaskLead.user),
                joinedload(TaskLead.scorer)
            ).filter(TaskLead.task_id.in_(task_ids)).order_by(TaskLead.added_at.desc()).all()
            
        except Exception as e:
            print(f"Error in get_workspace_task_leads: {e}")
            return []

    @staticmethod
    def remove_lead_from_task(task_id, lead_id):
        """Remove a lead from a task"""
        task_lead = TaskLead.query.filter_by(task_id=task_id, lead_id=lead_id).first()
        if task_lead:
            db.session.delete(task_lead)
            db.session.commit()
            return True
        return False

    def update_status(self, new_status):
        """Update the status of this task-lead relationship"""
        self.status = new_status
        db.session.commit()
        return self

    def update_notes(self, notes):
        """Update notes for this task-lead relationship"""
        self.notes = notes
        db.session.commit()
        return self

    def update_score(self, score, score_notes=None, scored_by=None):
        """Update the score of this task-lead relationship"""
        self.score = score
        self.score_notes = score_notes
        self.scored_by = scored_by
        self.scored_at = datetime.utcnow()
        db.session.commit()
        return self 