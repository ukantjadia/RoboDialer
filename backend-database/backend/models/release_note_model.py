from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.lead_model import db

class ReleaseNote(db.Model):
    """Model for release notes"""
    __tablename__ = 'release_notes'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    icon = Column(String(10))
    tag = Column(String(50))
    related_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    content = Column(Text)
    type = Column(String(50))
    created_by_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    audience = Column(String(20), default='all')  # 'all' or 'admin_dev'
    expired_date = Column(DateTime, nullable=True)
    created_by = relationship('User', foreign_keys=[created_by_id])

    def to_dict(self):
        """Convert ReleaseNote object to a dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'icon': self.icon,
            'tag': self.tag,
            'related_path': self.related_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'content': self.content,
            'type': self.type,
            'created_by': {
                'id': str(self.created_by_id) if self.created_by_id else None,
                'username': self.created_by.username if self.created_by else None
            },
            'audience': self.audience,
            'expired_date': self.expired_date.isoformat() if self.expired_date else None
        }

    @staticmethod
    def create(title, content, type, created_by, audience='all'):
        note = ReleaseNote(
            title=title,
            content=content,
            type=type,
            created_by_id=getattr(created_by, 'user_id', None),
            audience=audience
        )
        db.session.add(note)
        db.session.commit()
        return note

    def update(self, title=None, content=None, type=None):
        if title is not None:
            self.title = title
        if content is not None:
            self.content = content
        if type is not None:
            self.type = type
        db.session.commit()
        return self

    def delete(self):
        # First delete all related UserReadNote records
        from models.user_read_note_model import UserReadNote
        UserReadNote.query.filter_by(release_note_id=self.id).delete()
        
        # Then delete the release note
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return f'<ReleaseNote {self.title}>' 