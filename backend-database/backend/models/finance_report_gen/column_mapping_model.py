from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

class ColumnMapping(db.Model):
    __tablename__ = 'column_mapping'

    mapping_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_file.file_id', ondelete='CASCADE'), nullable=False)

    original_column_name = db.Column(db.String(255), nullable=False)
    mapped_column_name = db.Column(db.String(255), nullable=True)
    mapping_confidence = db.Column(db.Numeric(3, 2), nullable=True)
    auto_suggested = db.Column(db.Boolean, default=False)
    is_required = db.Column(db.Boolean, default=False)
    skipped = db.Column(db.Boolean, default=False)
    mapping_notes = db.Column(db.Text, nullable=True)
    synonyms_used = db.Column(JSONB, nullable=True)
    complete_mapping_json = db.Column(JSONB, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'mapping_id': str(self.mapping_id),
            'file_id': str(self.file_id),
            'original_column_name': self.original_column_name,
            'mapped_column_name': self.mapped_column_name,
            'mapping_confidence': float(self.mapping_confidence) if self.mapping_confidence else None,
            'auto_suggested': self.auto_suggested,
            'is_required': self.is_required,
            'skipped': self.skipped,
            'mapping_notes': self.mapping_notes,
            'synonyms_used': self.synonyms_used,
            'complete_mapping_json': self.complete_mapping_json,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
