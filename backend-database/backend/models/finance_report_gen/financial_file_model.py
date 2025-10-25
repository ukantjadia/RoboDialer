from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum
from datetime import datetime
import uuid

class FinancialFile(db.Model):
    __tablename__ = 'financial_file'

    file_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_report_upload.upload_id', ondelete='CASCADE'), nullable=False)

    file_name = db.Column(db.String(255), nullable=False)
    file_extension = db.Column(db.String(50), nullable=False)
    processed_file_path = db.Column(db.String(500), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)

    detected_periodicity = db.Column(SqlEnum('monthly', 'quarterly', 'annual', name='finance_detected_periodicity_enum'), nullable=True)
    user_selected_periodicity = db.Column(SqlEnum('monthly', 'quarterly', 'annual', name='finance_user_periodicity_enum'), nullable=True)

    file_type = db.Column(SqlEnum('income_statement', 'balance_sheet', 'cash_flow', 'unknown', name='finance_file_type_enum'), nullable=True)
    status = db.Column(SqlEnum('uploaded', 'headers_extracted', 'mapped', 'normalized', 'kpi_calculated', 'error', name='finance_file_status_enum'), nullable=False, default='uploaded')

    column_count = db.Column(db.Integer, nullable=True)
    row_count = db.Column(db.Integer, nullable=True)

    processing_started_at = db.Column(db.DateTime, nullable=True)
    processing_completed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'file_id': str(self.file_id),
            'upload_id': str(self.upload_id),
            'file_name': self.file_name,
            'processed_file_path': self.processed_file_path,
            'file_size': self.file_size,
            'detected_periodicity': self.detected_periodicity,
            'user_selected_periodicity': self.user_selected_periodicity,
            'file_type': self.file_type,
            'status': self.status,
            'column_count': self.column_count,
            'row_count': self.row_count,
            'processing_started_at': self.processing_started_at.isoformat() if self.processing_started_at else None,
            'processing_completed_at': self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
