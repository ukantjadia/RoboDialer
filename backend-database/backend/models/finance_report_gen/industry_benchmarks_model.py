from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class IndustryBenchmarks(db.Model):
    __tablename__ = 'industry_benchmarks'

    benchmark_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    industry_name = db.Column(db.String(100), nullable=False)
    kpi_name = db.Column(db.String(255), nullable=False)
    benchmark_type = db.Column(SqlEnum('minimum', 'target', 'excellent', 'industry_average', name='finance_benchmark_type_enum'), nullable=False)
    benchmark_value = db.Column(db.Numeric(10, 4), nullable=True)
    benchmark_unit = db.Column(db.String(50), nullable=True)
    data_source = db.Column(db.String(255), nullable=True)
    data_year = db.Column(db.Integer, nullable=True)
    sample_size = db.Column(db.Integer, nullable=True)
    confidence_level = db.Column(db.Numeric(3, 2), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'benchmark_id': str(self.benchmark_id),
            'industry_name': self.industry_name,
            'kpi_name': self.kpi_name,
            'benchmark_type': self.benchmark_type,
            'benchmark_value': float(self.benchmark_value) if self.benchmark_value else None,
            'benchmark_unit': self.benchmark_unit,
            'data_source': self.data_source,
            'data_year': self.data_year,
            'sample_size': self.sample_size,
            'confidence_level': float(self.confidence_level) if self.confidence_level else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
