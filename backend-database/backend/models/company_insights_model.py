from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.lead_model import db
import uuid
from datetime import datetime

class CompanyInsights(db.Model):
    """Model for storing company insights data"""
    __tablename__ = 'company_insights'

    insight_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    lead_id = db.Column(String(100), ForeignKey('leads.lead_id', ondelete='CASCADE'), nullable=False)

    # Feature data stored as JSONB
    ai_insights = db.Column(JSONB, nullable=True)
    competitors = db.Column(JSONB, nullable=True)
    growth_trends = db.Column(JSONB, nullable=True)
    reviews = db.Column(JSONB, nullable=True)
    maps = db.Column(JSONB, nullable=True)

    # Tracking fields
    is_completed = db.Column(Boolean, default=False, nullable=False)
    last_updated = db.Column(DateTime, nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, user_id, lead_id):
        self.user_id = user_id
        self.lead_id = lead_id

    def to_dict(self):
        """Convert CompanyInsights object to a dictionary"""
        return {
            'insight_id': str(self.insight_id),
            'user_id': str(self.user_id),
            'lead_id': self.lead_id,
            'ai_insights': self.ai_insights,
            'competitors': self.competitors,
            'growth_trends': self.growth_trends,
            'reviews': self.reviews,
            'maps': self.maps,
            'is_completed': self.is_completed,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def update_completion_status(self):
        """Update is_completed flag based on available data"""
        features = [self.ai_insights, self.competitors, self.growth_trends, self.reviews, self.maps]
        self.is_completed = all(feature is not None for feature in features)

    def update_feature_data(self, feature_name, data):
        """Update a specific feature's data and update completion status"""
        if hasattr(self, feature_name):
            setattr(self, feature_name, data)
            self.last_updated = datetime.utcnow()
            self.update_completion_status()
            return True
        return False
