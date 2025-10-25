# SQLAlchemy model for feedback (new, normalized)

import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import String, Text, DateTime, Column
# from models import db
from models.lead_model import db

class MessageFeedback(db.Model):
    """
    Feedback table: one row per feedback action (generation, upvote, downvote, regeneration, etc.)
    - entry_id: unique for every feedback action (PK)
    - message_id: links to the original generated message (not unique)
    - parent_message_id: links to the message_id of the parent message (if this is a regeneration)
    - feedback_type: 'generation', 'upvote', 'downvote', 'regeneration', etc.
    """
    __tablename__ = 'message_feedback'

    entry_id = db.Column('uuid', String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = db.Column(String(36), nullable=False)  # Link to this message
    parent_message_id = db.Column(String(36), nullable=True)  # Link to parent message if regenerated
    user_id = db.Column(Text, nullable=True)
    company_name = db.Column(Text, nullable=True)
    industry = db.Column(Text, nullable=True)
    tone = db.Column(Text, nullable=True)
    focus = db.Column(Text, nullable=True)
    context = db.Column(Text, nullable=True)
    model_used = db.Column(Text, nullable=True)
    prompt_template = db.Column(Text, nullable=True)
    prompt_text = db.Column(Text, nullable=True)
    generated_message = db.Column(JSONB, nullable=True)
    feedback_type = db.Column(Text, nullable=False)  # 'generation', 'upvote', 'downvote', etc.
    timestamp = db.Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MessageFeedback {self.entry_id}>'

    def to_dict(self):
        return {
            'entry_id': str(self.entry_id),
            'message_id': str(self.message_id),
            'parent_message_id': str(self.parent_message_id) if self.parent_message_id else None,
            'user_id': self.user_id,
            'company_name': self.company_name,
            'industry': self.industry,
            'tone': self.tone,
            'focus': self.focus,
            'context': self.context,
            'model_used': self.model_used,
            'prompt_template': self.prompt_template,
            'prompt_text': self.prompt_text,
            'generated_message': self.generated_message,
            'feedback_type': self.feedback_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }