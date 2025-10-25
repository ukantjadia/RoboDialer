from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class DataGranularity(db.Model):
    __tablename__ = 'data_granularity'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_report_upload.upload_id', ondelete='CASCADE'), nullable=False)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_file.file_id', ondelete='CASCADE'), nullable=True)

    detected_granularity = db.Column(SqlEnum('daily', 'weekly', 'monthly', 'quarterly', 'yearly', name='detected_granularity_enum'), nullable=False)
    confidence_score = db.Column(db.Numeric(3, 2), nullable=True)
    period_count = db.Column(db.Integer, nullable=True)
    date_range_start = db.Column(db.Date, nullable=True)
    date_range_end = db.Column(db.Date, nullable=True)

    # Suggested chart periods
    suggested_chart_periods = db.Column(db.Text, nullable=True)  # JSON string of suggested periods
    auto_detection_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': str(self.id),
            'upload_id': str(self.upload_id),
            'file_id': str(self.file_id) if self.file_id else None,
            'detected_granularity': self.detected_granularity,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'period_count': self.period_count,
            'date_range_start': self.date_range_start.isoformat() if self.date_range_start else None,
            'date_range_end': self.date_range_end.isoformat() if self.date_range_end else None,
            'suggested_chart_periods': self.suggested_chart_periods,
            'auto_detection_notes': self.auto_detection_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
