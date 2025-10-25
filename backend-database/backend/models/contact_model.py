import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Column, Boolean, DateTime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID

from models.lead_model import db, Lead

class Contact(db.Model):
    __tablename__ = 'contacts'

    contact_id = db.Column('uuid', String(36), primary_key=True, default=lambda: str(uuid.uuid4()),  unique=True, nullable=False)
    lead_id = db.Column('lead_id', String(100), ForeignKey('leads.lead_id'), nullable=False)

    company_phone = db.Column(db.String(100), nullable=True)
    owner_first_name = db.Column(db.String(1000), nullable=True)
    owner_last_name = db.Column(db.String(1000), nullable=True)
    owner_title = db.Column(db.String(1000), nullable=True)
    owner_linkedin = db.Column(db.String(1000), nullable=True)
    owner_phone_number = db.Column(db.String(100), nullable=True)
    owner_email = db.Column(db.String(1000), nullable=True)
    phone = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(1000), nullable=True)
    state = db.Column(db.String(1000), nullable=True)
    is_primary = db.Column('is_primary', Boolean, default=False, nullable=False)
    created_at = db.Column('created_at', DateTime, default=datetime.utcnow)
    updated_at = db.Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    def __repr__(self):
        return f'<Contact {self.contact_id} for Lead {self.lead_id}>'

    def to_dict(self):
        return {
            'contact_id': str(self.contact_id),
            'lead_id': self.lead_id,
            'company_phone': self.company_phone,
            'owner_first_name': self.owner_first_name,
            'owner_last_name': self.owner_last_name,
            'owner_title': self.owner_title,
            'owner_linkedin': self.owner_linkedin,
            'owner_phone_number': self.owner_phone_number,
            'owner_email': self.owner_email,
            'phone': self.phone,
            'city': self.city,
            'state': self.state,
            'is_primary': self.is_primary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }