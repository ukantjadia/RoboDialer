from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class FinancialKPI(db.Model):
    __tablename__ = 'financial_kpi'

    kpi_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_report_upload.upload_id', ondelete='CASCADE'), nullable=False)

    kpi_name = db.Column(db.String(255), nullable=False)
    kpi_category = db.Column(db.String(100), nullable=True)
    kpi_value = db.Column(db.Numeric(10, 4), nullable=True)
    kpi_unit = db.Column(db.String(50), nullable=True)

    calculation_status = db.Column(SqlEnum('calculated', 'failed', 'skipped', 'pending', name='finance_calculation_status_enum'), nullable=True)
    threshold_status = db.Column(SqlEnum('below_standard', 'meets_standard', 'exceeds_benchmark', name='finance_threshold_status_enum'), nullable=True)

    industry_benchmark = db.Column(db.Numeric(10, 4), nullable=True)
    benchmark_source = db.Column(db.String(100), nullable=True)
    calculation_notes = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    dependencies_satisfied = db.Column(db.Boolean, default=True)
    calculation_duration_ms = db.Column(db.Integer, nullable=True)
    calculation_order = db.Column(db.Integer, nullable=True)
    last_calculation_date = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'kpi_id': str(self.kpi_id),
            'upload_id': str(self.upload_id),
            'kpi_name': self.kpi_name,
            'kpi_category': self.kpi_category,
            'kpi_value': float(self.kpi_value) if self.kpi_value else None,
            'kpi_unit': self.kpi_unit,
            'calculation_status': self.calculation_status,
            'threshold_status': self.threshold_status,
            'industry_benchmark': float(self.industry_benchmark) if self.industry_benchmark else None,
            'benchmark_source': self.benchmark_source,
            'calculation_notes': self.calculation_notes,
            'error_message': self.error_message,
            'dependencies_satisfied': self.dependencies_satisfied,
            'calculation_duration_ms': self.calculation_duration_ms,
            'calculation_order': self.calculation_order,
            'last_calculation_date': self.last_calculation_date.isoformat() if self.last_calculation_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
