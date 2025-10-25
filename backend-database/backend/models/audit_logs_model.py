from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from models.lead_model import db
import uuid
from datetime import datetime

class AuditLog(db.Model):
    """Audit logs for tracking changes to data"""
    __tablename__ = 'audit_logs'

    id = db.Column('bigint', db.BigInteger, primary_key=True, autoincrement=True)
    log_id = db.Column('log_id', String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column('user_id', UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    action_type = db.Column('action_type', SQLEnum('create', 'update', 'delete', 'view', 'export', 'import', name='action_type_enum'), nullable=False)
    table_affected = db.Column('table_affected', Text, nullable=False)
    record_id = db.Column('record_id', Text, nullable=False)
    old_values = db.Column('old_values', db.JSON, nullable=True)
    new_values = db.Column('new_values', db.JSON, nullable=True)
    ip_address = db.Column('ip_address', String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = db.Column('user_agent', Text, nullable=True)
    created_at = db.Column('created_at', DateTime, default=datetime.utcnow)

    def __init__(self, user_id, action_type, table_affected, record_id, old_values=None, new_values=None, ip_address=None, user_agent=None):
        self.user_id = user_id
        self.action_type = action_type
        self.table_affected = table_affected
        self.record_id = record_id
        self.old_values = old_values
        self.new_values = new_values
        self.ip_address = ip_address
        self.user_agent = user_agent

    def to_dict(self):
        return {
            'id': self.id,
            'log_id': self.log_id,
            'user_id': str(self.user_id),
            'action_type': self.action_type,
            'table_affected': self.table_affected,
            'record_id': self.record_id,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def log_change(cls, user_id, action_type, table_affected, record_id, old_values=None, new_values=None, ip_address=None, user_agent=None):
        """Create and add a new audit log entry"""
        log = cls(
            user_id=user_id,
            action_type=action_type,
            table_affected=table_affected,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log)
        return log