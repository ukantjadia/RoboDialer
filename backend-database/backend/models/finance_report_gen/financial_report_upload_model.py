from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class FinancialReportUpload(db.Model):
    __tablename__ = 'financial_report_upload'

    upload_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    industry = db.Column(db.String(100), nullable=True)

    data_granularity = db.Column(SqlEnum('monthly', 'quarterly', 'annual', name='finance_data_granularity_enum'), nullable=True)
    status = db.Column(SqlEnum('uploaded', 'mapping', 'processing', 'completed', 'error', name='finance_upload_status_enum'), nullable=False, default='uploaded')

    total_files = db.Column(db.Integer, nullable=True)
    processed_files = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'upload_id': str(self.upload_id),
            'user_id': str(self.user_id),
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'industry': self.industry,
            'data_granularity': self.data_granularity,
            'status': self.status,
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
