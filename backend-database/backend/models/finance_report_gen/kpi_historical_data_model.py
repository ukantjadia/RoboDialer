from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class KPIHistoricalData(db.Model):
    __tablename__ = 'kpi_historical_data'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_report_upload.upload_id', ondelete='CASCADE'), nullable=False)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_file.file_id', ondelete='CASCADE'), nullable=True)

    kpi_name = db.Column(db.String(255), nullable=False)
    kpi_category = db.Column(db.String(100), nullable=True)

    # Time period information
    period_start_date = db.Column(db.Date, nullable=False)
    period_end_date = db.Column(db.Date, nullable=False)
    period_type = db.Column(SqlEnum('daily', 'weekly', 'monthly', 'quarterly', 'yearly', name='kpi_period_type_enum'), nullable=False)
    period_label = db.Column(db.String(100), nullable=True)  # "2023-Q1", "Jan 2023", etc.

    # KPI values
    kpi_value = db.Column(db.Numeric(18, 4), nullable=True)
    kpi_unit = db.Column(db.String(50), nullable=True)

    # Calculation metadata
    calculation_status = db.Column(SqlEnum('calculated', 'failed', 'skipped', 'pending', name='finance_calculation_status_enum'), nullable=True)
    calculation_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data_quality_score = db.Column(db.Numeric(3, 2), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    calculation_duration_ms = db.Column(db.Integer, nullable=True)

    # Benchmarking
    industry_benchmark = db.Column(db.Numeric(10, 4), nullable=True)
    benchmark_source = db.Column(db.String(100), nullable=True)
    threshold_status = db.Column(SqlEnum('below_standard', 'meets_standard', 'exceeds_benchmark', name='finance_threshold_status_enum'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': str(self.id),
            'upload_id': str(self.upload_id),
            'file_id': str(self.file_id) if self.file_id else None,
            'kpi_name': self.kpi_name,
            'kpi_category': self.kpi_category,
            'period_start_date': self.period_start_date.isoformat() if self.period_start_date else None,
            'period_end_date': self.period_end_date.isoformat() if self.period_end_date else None,
            'period_type': self.period_type,
            'period_label': self.period_label,
            'kpi_value': float(self.kpi_value) if self.kpi_value else None,
            'kpi_unit': self.kpi_unit,
            'calculation_status': self.calculation_status,
            'calculation_timestamp': self.calculation_timestamp.isoformat() if self.calculation_timestamp else None,
            'data_quality_score': float(self.data_quality_score) if self.data_quality_score else None,
            'error_message': self.error_message,
            'calculation_duration_ms': self.calculation_duration_ms,
            'industry_benchmark': float(self.industry_benchmark) if self.industry_benchmark else None,
            'benchmark_source': self.benchmark_source,
            'threshold_status': self.threshold_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
