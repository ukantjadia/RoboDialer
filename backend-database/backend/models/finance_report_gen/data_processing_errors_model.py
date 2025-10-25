from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class DataProcessingErrors(db.Model):
    __tablename__ = 'data_processing_errors'

    error_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_report_upload.upload_id', ondelete='CASCADE'), nullable=False)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_file.file_id', ondelete='CASCADE'), nullable=True)

    error_type = db.Column(SqlEnum('file_format', 'missing_data', 'calculation_failed', 'mapping_invalid', 'validation_failed', name='finance_error_type_enum'), nullable=False)
    error_severity = db.Column(SqlEnum('low', 'medium', 'high', 'critical', name='finance_error_severity_enum'), nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    error_code = db.Column(db.String(50), nullable=True)
    affected_data = db.Column(JSONB, nullable=True)
    suggested_action = db.Column(db.Text, nullable=True)
    stack_trace = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(UUID(as_uuid=True), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'error_id': str(self.error_id),
            'upload_id': str(self.upload_id),
            'file_id': str(self.file_id) if self.file_id else None,
            'error_type': self.error_type,
            'error_severity': self.error_severity,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'affected_data': self.affected_data,
            'suggested_action': self.suggested_action,
            'stack_trace': self.stack_trace,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': str(self.resolved_by) if self.resolved_by else None,
            'resolution_notes': self.resolution_notes
        }
