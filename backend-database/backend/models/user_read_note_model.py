from datetime import datetime
from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID

class UserReadNote(db.Model):
    """Model for tracking which users have read which release notes"""
    __tablename__ = 'user_read_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    release_note_id = db.Column(db.Integer, db.ForeignKey('release_notes.id', ondelete='CASCADE'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'release_note_id', name='uix_user_release_note'),
    )

    def __init__(self, user_id, release_note_id):
        self.user_id = user_id
        self.release_note_id = release_note_id

    def to_dict(self):
        """Convert UserReadNote object to a dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'release_note_id': self.release_note_id,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }

    def __repr__(self):
        return f'<UserReadNote {self.user_id} read {self.release_note_id} at {self.read_at}>' 