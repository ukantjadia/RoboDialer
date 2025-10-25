
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
import hashlib
import uuid
import enum
from models.lead_model import db



class Agent(db.Model):
    """Agents table - stores agent information for RoboDialer"""
    __tablename__ = 'agents'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Agent Information
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Status and Availability
    status = db.Column(db.String(50), nullable=False, default='active')  # active, inactive, on_break, unavailable
    is_available = db.Column(db.Boolean, nullable=False, default=True)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)  # For soft delete/archiving
    
    # Performance Metrics
    total_calls = db.Column(db.Integer, nullable=False, default=0)
    successful_calls = db.Column(db.Integer, nullable=False, default=0)
    
    # Configuration
    max_concurrent_calls = db.Column(db.Integer, nullable=False, default=1)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    score_given = db.Column(db.Float, nullable=True, default=None)
    call_logs = db.relationship(
        "CallLog",
        back_populates="agent",
        cascade="all, delete-orphan",
        lazy=True
    )
    def __repr__(self):
        return f'<Agent {self.id}: {self.name} - {self.status}>'
    
    def to_dict(self):
        """Convert Agent object to dictionary for API response"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'status': self.status,
            'is_available': self.is_available,
            'is_archived': self.is_archived,
            'total_calls': self.total_calls,
            'successful_calls': self.successful_calls,
            'max_concurrent_calls': self.max_concurrent_calls,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'score':self.score_given
        }
    


class AgentPreferences(db.Model):
    """Agent preferences table - stores agent-specific settings and preferences"""
    __tablename__ = 'agent_preferences'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to agent
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=False)
    
    # Voicemail settings
    voicemail_script = db.Column(db.Text, nullable=True)  # Custom voicemail message for this agent
    auto_voicemail_enabled = db.Column(db.Boolean, nullable=False, default=False)  # Auto send voicemail on no-pickup
    
    # Other preferences can be added here in future
    # call_timeout = db.Column(db.Integer, nullable=False, default=30)
    # preferred_calling_hours_start = db.Column(db.Time, nullable=True)
    # preferred_calling_hours_end = db.Column(db.Time, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    agent = db.relationship("Agent", backref=db.backref("preferences", uselist=False))
    
    def __repr__(self):
        return f'<AgentPreferences {self.agent_id}>'
    
    def to_dict(self):
        """Convert AgentPreferences object to dictionary for API response"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'voicemail_script': self.voicemail_script,
            'auto_voicemail_enabled': self.auto_voicemail_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

