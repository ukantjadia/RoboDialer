from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class DataQualityMetrics(db.Model):
    __tablename__ = 'data_quality_metrics'

    metric_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_report_upload.upload_id', ondelete='CASCADE'), nullable=False)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_file.file_id', ondelete='CASCADE'), nullable=False)

    metric_type = db.Column(SqlEnum('completeness', 'accuracy', 'consistency', 'timeliness', name='finance_metric_type_enum'), nullable=False)
    metric_name = db.Column(db.String(255), nullable=False)
    metric_value = db.Column(db.Numeric(5, 2), nullable=True)
    threshold_min = db.Column(db.Numeric(5, 2), nullable=True)
    threshold_max = db.Column(db.Numeric(5, 2), nullable=True)
    quality_status = db.Column(SqlEnum('excellent', 'good', 'acceptable', 'poor', 'unacceptable', name='finance_quality_status_enum'), nullable=True)

    issues_found = db.Column(JSONB, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'metric_id': str(self.metric_id),
            'upload_id': str(self.upload_id),
            'file_id': str(self.file_id),
            'metric_type': self.metric_type,
            'metric_name': self.metric_name,
            'metric_value': float(self.metric_value) if self.metric_value else None,
            'threshold_min': float(self.threshold_min) if self.threshold_min else None,
            'threshold_max': float(self.threshold_max) if self.threshold_max else None,
            'quality_status': self.quality_status,
            'issues_found': self.issues_found,
            'recommendations': self.recommendations,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
