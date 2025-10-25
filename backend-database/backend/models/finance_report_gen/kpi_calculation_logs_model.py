from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class KPICalculationLogs(db.Model):
    __tablename__ = 'kpi_calculation_logs'

    log_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_report_upload.upload_id', ondelete='CASCADE'), nullable=False)

    kpi_name = db.Column(db.String(255), nullable=False)
    calculation_step = db.Column(db.String(100), nullable=True)
    step_status = db.Column(SqlEnum('started', 'completed', 'failed', 'skipped', name='finance_step_status_enum'), nullable=True)

    input_data = db.Column(JSONB, nullable=True)
    output_result = db.Column(JSONB, nullable=True)
    error_details = db.Column(db.Text, nullable=True)
    processing_time_ms = db.Column(db.Integer, nullable=True)
    dependencies_checked = db.Column(JSONB, nullable=True)
    calculation_order = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'log_id': str(self.log_id),
            'upload_id': str(self.upload_id),
            'kpi_name': self.kpi_name,
            'calculation_step': self.calculation_step,
            'step_status': self.step_status,
            'input_data': self.input_data,
            'output_result': self.output_result,
            'error_details': self.error_details,
            'processing_time_ms': self.processing_time_ms,
            'dependencies_checked': self.dependencies_checked,
            'calculation_order': self.calculation_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
