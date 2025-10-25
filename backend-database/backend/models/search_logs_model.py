from sqlalchemy import Column, String, Integer, Text, DateTime, LargeBinary, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from models.lead_model import db
import uuid
from datetime import datetime

class SearchLog(db.Model):
    """Log of user searches"""
    __tablename__ = 'search_logs'

    id = db.Column('uuid', String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    search_id = db.Column('search_id', String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column('user_id', UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    search_query = db.Column('search_query', Text, nullable=False)
    search_hash = db.Column('search_hash', LargeBinary, nullable=True)  # BYTEA in PostgreSQL
    search_parameters = db.Column('search_parameters', db.JSON, nullable=True)
    result_count = db.Column('result_count', Integer, default=0)
    execution_time_ms = db.Column('execution_time_ms', Integer, default=0)
    searched_at = db.Column('searched_at', DateTime, default=datetime.utcnow)

    def __init__(self, user_id, search_query, search_parameters=None, search_hash=None, result_count=0, execution_time_ms=0):
        self.user_id = user_id
        self.search_query = search_query
        self.search_parameters = search_parameters or {}
        self.search_hash = search_hash
        self.result_count = result_count
        self.execution_time_ms = execution_time_ms

    def to_dict(self):
        return {
            'id': self.id,
            'search_id': self.search_id,
            'user_id': str(self.user_id),
            'search_query': self.search_query,
            'search_parameters': self.search_parameters,
            'result_count': self.result_count,
            'execution_time_ms': self.execution_time_ms,
            'searched_at': self.searched_at.isoformat() if self.searched_at else None
        }