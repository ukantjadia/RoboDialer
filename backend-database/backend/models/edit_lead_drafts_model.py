from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from models.lead_model import db
import uuid
from datetime import datetime

class EditLeadDraft(db.Model):
    """User drafts for lead editing"""
    __tablename__ = 'edit_lead_drafts'

    id = db.Column('uuid', String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    draft_id = db.Column('draft_id', String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column('user_id', UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    lead_id = db.Column('lead_id', String(100), ForeignKey('leads.lead_id'), nullable=False)
    version = db.Column('version', Integer, default=1)
    draft_data = db.Column('draft_data', db.JSON, nullable=False)
    change_summary = db.Column('change_summary', Text, nullable=True)
    phase = db.Column('phase', Enum('draft', 'review', 'approved', 'rejected', name='draft_phase_enum'), default='draft')
    status = db.Column('status', Enum('pending', 'in_progress', 'completed', 'archived', name='draft_status_enum'), default='pending')
    is_deleted = db.Column('is_deleted', Boolean, default=False)
    created_at = db.Column('created_at', DateTime, default=datetime.utcnow)
    updated_at = db.Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, user_id, lead_id, draft_data, change_summary=None, phase='draft', status='pending'):
        self.user_id = user_id
        self.lead_id = lead_id
        self.draft_data = draft_data
        self.change_summary = change_summary
        self.phase = phase
        self.status = status

    def to_dict(self):
        return {
            'id': self.id,
            'draft_id': self.draft_id,
            'user_id': str(self.user_id),
            'lead_id': self.lead_id,
            'version': self.version,
            'draft_data': self.draft_data,
            'change_summary': self.change_summary,
            'phase': self.phase,
            'status': self.status,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def increment_version(self):
        """Increment the version number"""
        self.version += 1