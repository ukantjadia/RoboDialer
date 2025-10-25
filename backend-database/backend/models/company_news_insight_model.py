from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.lead_model import db
from datetime import datetime
import uuid

class CompanyNewsInsight(db.Model):
    __tablename__ = 'company_news_insights'

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    lead_id = Column(String(100), ForeignKey('leads.lead_id'), nullable=True)
    company_name = Column(String(255), nullable=False)
    headline = Column(Text, nullable=False)
    insights = Column(JSONB, nullable=False)  # Array of strings
    source = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True)  # Object with keys: relevancy, event_type, topic
    published_at = Column(DateTime, nullable=True)
    saved_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': str(self.user_id),
            'lead_id': self.lead_id,
            'company_name': self.company_name,
            'headline': self.headline,
            'insights': self.insights,
            'source': self.source,
            'tags': self.tags,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'saved_at': self.saved_at.isoformat() if self.saved_at else None
        }