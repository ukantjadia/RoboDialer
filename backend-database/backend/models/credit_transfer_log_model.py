from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

class CreditTransferLog(db.Model):
    __tablename__ = 'credit_transfer_logs'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = db.Column(UUID(as_uuid=True), nullable=True)
    from_user_id = db.Column(UUID(as_uuid=True), nullable=False)
    to_user_id = db.Column(UUID(as_uuid=True), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    transferred_at = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': str(self.id),
            'company_id': str(self.company_id),
            'from_user_id': str(self.from_user_id),
            'to_user_id': str(self.to_user_id),
            'amount': self.amount,
            'transferred_at': self.transferred_at.isoformat() if self.transferred_at else None,
            'note': self.note
        } 