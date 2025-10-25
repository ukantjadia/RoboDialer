from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
import hashlib
import uuid
import enum
from models.lead_model import db



class CallLog(db.Model):
    """Call logs table - stores call activity for RoboDialer"""
    __tablename__ = 'call_logs'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Foreign Keys
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    lead_id = db.Column(db.Integer, nullable=True)  # Optional lead reference
    agent = db.relationship("Agent", back_populates="call_logs")
    
    # Call Details
    phone_number = db.Column(db.String(100), nullable=False)  # Increased from 20 to 100 to accommodate company names
    direction = db.Column(db.String(20), nullable=False, default='outgoing')  # 'incoming' or 'outgoing'
    status = db.Column(db.String(50), nullable=False, default='completed')  # 'completed', 'failed', 'busy', etc.
    action_taken = db.Column(db.String(50), nullable=False, default='call')  # 'call', 'voicemail', 'email'
    contact_name = db.Column(db.String(255), nullable=True)  # Name of the contact
    
    # Call Timing
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Integer, nullable=True)  # Duration in seconds
    
    # Call Content
    notes = db.Column(db.Text, nullable=True)
    recording_url = db.Column(db.String(500), nullable=True)
    
    # Follow-up Information
    follow_up_required = db.Column(db.Boolean, nullable=False, default=False)
    follow_up_date = db.Column(db.DateTime, nullable=True)
    
    # System Information
    call_attempt_number = db.Column(db.Integer, nullable=False, default=1)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<CallLog {self.id}: Agent {self.agent_id} -> Phone {self.phone_number}>'
    
    def to_dict(self):
        """Convert CallLog object to dictionary for API response"""
        return {
            'id': self.id,
            'call_log_id': self.id,  # Frontend expects this field
            'agent_id': self.agent_id,
            'lead_id': self.lead_id,
            'phone_number': self.phone_number,
            'direction': self.direction,
            'status': self.status,
            'action_taken': self.action_taken,
            'contact_name': self.contact_name,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration': self.duration,
            'notes': self.notes,
            'recording_url': self.recording_url,
            'follow_up_required': self.follow_up_required,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'call_attempt_number': self.call_attempt_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
