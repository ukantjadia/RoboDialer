import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, Text, DateTime, Column, Boolean, Integer, ForeignKey, UniqueConstraint
from models.lead_model import db

class EmailGenTemplate(db.Model):
    __tablename__ = 'emailgen_templates'
    __table_args__ = (
        UniqueConstraint('user_id', 'template_name', name='uq_user_emailgen_template_name'),
    )

    template_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    template_name = db.Column(String(100), nullable=False)
    template_content = db.Column(Text, nullable=False)
    is_default = db.Column(Boolean, default=False)
    cta_line = db.Column(Text, nullable=True)
    usage_count = db.Column(Integer, default=0)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_predefined = db.Column(Boolean, default=False)

    def to_dict(self):
        return {
            'template_id': str(self.template_id),
            'user_id': str(self.user_id),
            'template_name': self.template_name,
            'template_content': self.template_content,
            'is_default': self.is_default,
            'cta_line': self.cta_line,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_predefined': self.is_predefined
        }