from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, Text, Enum
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from models.lead_model import db


# db = SQLAlchemy()

class Message(db.Model):
    __tablename__ = 'messages'

    message_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = db.Column('lead_id', String(100), ForeignKey('leads.lead_id'), nullable=True)  # if null that's mean it's come from standalone generator
    user_id = db.Column('user_id', UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    message_type = db.Column(db.String(50), nullable=False)  # 'email' or 'linkedin'
    message_content = db.Column(JSONB, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # user = db.relationship('User', back_populates='messages')

    def __repr__(self):
        return f'<Message {self.message_id}>'

    def to_dict(self):
        """Convert Message object to a dictionary."""
        return {
            'message_id': self.message_id,
            'user_id': self.user_id,
            'message_type': self.message_type,
            'message_content': self.message_content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }