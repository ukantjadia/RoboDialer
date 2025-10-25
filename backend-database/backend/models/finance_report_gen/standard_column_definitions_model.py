from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class StandardColumnDefinitions(db.Model):
    __tablename__ = 'standard_column_definitions'

    column_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    column_name = db.Column(db.String(255), nullable=False)
    column_category = db.Column(db.String(100), nullable=True)
    column_subcategory = db.Column(db.String(100), nullable=True)
    applicable_file_types = db.Column(JSONB, nullable=True)
    is_required = db.Column(db.Boolean, default=False)
    priority_score = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    synonyms = db.Column(JSONB, nullable=True)
    pattern_matches = db.Column(JSONB, nullable=True)
    expected_data_type = db.Column(SqlEnum('integer', 'decimal', 'percentage', 'currency', 'date', 'month', 'year', 'time', 'fiscal', 'text' ,name='finance_expected_data_type_enum'), nullable=True)
    validation_rules = db.Column(JSONB, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'column_id': str(self.column_id),
            'column_name': self.column_name,
            'column_category': self.column_category,
            'column_subcategory': self.column_subcategory,
            'applicable_file_types': self.applicable_file_types,
            'is_required': self.is_required,
            'priority_score': self.priority_score,
            'description': self.description,
            'synonyms': self.synonyms,
            'pattern_matches': self.pattern_matches,
            'expected_data_type': self.expected_data_type,
            'validation_rules': self.validation_rules,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
