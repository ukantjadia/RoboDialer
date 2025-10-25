from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

class FinancialReportVersion(db.Model):
    __tablename__ = 'financial_report_version'

    version_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id = db.Column(UUID(as_uuid=True), db.ForeignKey('financial_report_upload.upload_id', ondelete='CASCADE'), nullable=False)

    version_number = db.Column(db.Integer, nullable=False)
    generated_date = db.Column(db.DateTime, default=datetime.utcnow)

    summary = db.Column(db.Text, nullable=True)
    insights = db.Column(JSONB, nullable=True)
    risks = db.Column(JSONB, nullable=True)
    recommendations = db.Column(JSONB, nullable=True)

    generated_by_llm = db.Column(db.Boolean, default=True)
    llm_model_used = db.Column(db.String(100), nullable=True)
    llm_prompt_version = db.Column(db.String(50), nullable=True)

    download_link_pdf = db.Column(db.String(500), nullable=True)
    download_link_excel = db.Column(db.String(500), nullable=True)
    report_metadata = db.Column(JSONB, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'version_id': str(self.version_id),
            'upload_id': str(self.upload_id),
            'version_number': self.version_number,
            'generated_date': self.generated_date.isoformat() if self.generated_date else None,
            'summary': self.summary,
            'insights': self.insights,
            'risks': self.risks,
            'recommendations': self.recommendations,
            'generated_by_llm': self.generated_by_llm,
            'llm_model_used': self.llm_model_used,
            'llm_prompt_version': self.llm_prompt_version,
            'download_link_pdf': self.download_link_pdf,
            'download_link_excel': self.download_link_excel,
            'report_metadata': self.report_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
