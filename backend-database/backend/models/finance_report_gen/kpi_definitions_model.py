from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class KPIDefinitions(db.Model):
    __tablename__ = 'kpi_definitions'

    kpi_def_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kpi_name = db.Column(db.String(255), nullable=False)
    kpi_category = db.Column(db.String(100), nullable=True)
    kpi_subcategory = db.Column(db.String(100), nullable=True)
    formula = db.Column(db.Text, nullable=True)
    formula_type = db.Column(SqlEnum('simple_ratio', 'complex_formula', 'custom_logic', name='finance_formula_type_enum'), nullable=True)
    required_columns = db.Column(JSONB, nullable=True)
    optional_columns = db.Column(JSONB, nullable=True)
    dependencies = db.Column(JSONB, nullable=True)
    dependency_level = db.Column(db.Integer, nullable=True)
    industry_benchmarks = db.Column(JSONB, nullable=True)
    description = db.Column(db.Text, nullable=True)
    calculation_notes = db.Column(db.Text, nullable=True)
    expected_range_min = db.Column(db.Numeric(10, 4), nullable=True)
    expected_range_max = db.Column(db.Numeric(10, 4), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    priority_order = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'kpi_def_id': str(self.kpi_def_id),
            'kpi_name': self.kpi_name,
            'kpi_category': self.kpi_category,
            'kpi_subcategory': self.kpi_subcategory,
            'formula': self.formula,
            'formula_type': self.formula_type,
            'required_columns': self.required_columns,
            'optional_columns': self.optional_columns,
            'dependencies': self.dependencies,
            'dependency_level': self.dependency_level,
            'industry_benchmarks': self.industry_benchmarks,
            'description': self.description,
            'calculation_notes': self.calculation_notes,
            'expected_range_min': float(self.expected_range_min) if self.expected_range_min else None,
            'expected_range_max': float(self.expected_range_max) if self.expected_range_max else None,
            'is_active': self.is_active,
            'priority_order': self.priority_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
