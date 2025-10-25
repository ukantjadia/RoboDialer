from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class NormalizedFinancialData(db.Model):
    __tablename__ = 'normalized_financial_data'

    record_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_file.file_id', ondelete='CASCADE'), nullable=False)

    metric_name = db.Column(db.String(255), nullable=False)
    period_start_date = db.Column(db.Date, nullable=True)
    period_end_date = db.Column(db.Date, nullable=True)
    value = db.Column(db.Numeric(18, 2), nullable=True)
    original_value = db.Column(db.String(255), nullable=True)

    data_type = db.Column(SqlEnum('integer', 'decimal', 'percentage', 'currency', name='finance_data_type_enum'), nullable=True)
    validation_status = db.Column(SqlEnum('valid', 'suspicious', 'invalid', name='finance_validation_status_enum'), nullable=True)
    data_quality_score = db.Column(db.Numeric(3, 2), nullable=True)
    outlier_flag = db.Column(db.Boolean, default=False)
    validation_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'record_id': str(self.record_id),
            'file_id': str(self.file_id),
            'metric_name': self.metric_name,
            'period_start_date': self.period_start_date.isoformat() if self.period_start_date else None,
            'period_end_date': self.period_end_date.isoformat() if self.period_end_date else None,
            'value': float(self.value) if self.value else None,
            'original_value': self.original_value,
            'data_type': self.data_type,
            'validation_status': self.validation_status,
            'data_quality_score': float(self.data_quality_score) if self.data_quality_score else None,
            'outlier_flag': self.outlier_flag,
            'validation_notes': self.validation_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
