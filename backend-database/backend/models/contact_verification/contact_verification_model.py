from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from models.lead_model import db
import uuid

class ContactVerification(db.Model):
    __tablename__ = 'contact_verification'

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign keys - both can be null for different validation types
    lead_id = db.Column(db.String(100), db.ForeignKey('leads.lead_id'), nullable=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)

    # Contact information
    contact_type = db.Column(db.String(10), nullable=False)  # 'phone' or 'email'
    contact_value = db.Column(db.String(1000), nullable=False)  # The actual phone/email

    # Validation type to distinguish between lead-associated and standalone
    validation_type = db.Column(db.String(20), default='lead', nullable=False)  # 'lead' or 'standalone'

    # Verification data (stored as JSON)
    verification_data = db.Column(JSONB, nullable=False)

    # Metadata
    last_verified = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for better performance
    __table_args__ = (
        db.Index('idx_contact_verification_lead_contact', 'lead_id', 'contact_type', 'contact_value'),
        db.Index('idx_contact_verification_contact', 'contact_type', 'contact_value'),
        db.Index('idx_contact_verification_user_contact', 'user_id', 'contact_type', 'contact_value'),
        db.Index('idx_contact_verification_type', 'validation_type'),
    )

    def __repr__(self):
        return f'<ContactVerification {self.id}: {self.contact_type} for {self.validation_type} {self.lead_id or self.user_id}>'

    def to_dict(self):
        """Convert ContactVerification object to dictionary for API response"""
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'user_id': str(self.user_id) if self.user_id else None,
            'contact_type': self.contact_type,
            'contact_value': self.contact_value,
            'validation_type': self.validation_type,
            'verification_data': self.verification_data,
            'last_verified': self.last_verified.isoformat() if self.last_verified else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def find_verification(cls, lead_id, contact_type, contact_value):
        """
        Find verification for a specific lead and contact (lead-associated)
        """
        return cls.query.filter_by(
            lead_id=lead_id,
            contact_type=contact_type,
            contact_value=contact_value,
            validation_type='lead'
        ).first()

    @classmethod
    def find_standalone_verification(cls, user_id, contact_type, contact_value):
        """
        Find standalone verification for a specific user and contact
        """
        return cls.query.filter_by(
            user_id=user_id,
            contact_type=contact_type,
            contact_value=contact_value,
            validation_type='standalone'
        ).first()

    @classmethod
    def create_or_update_verification(cls, lead_id, contact_type, contact_value, verification_data):
        """
        Create or update lead-associated verification entry
        """
        existing = cls.find_verification(lead_id, contact_type, contact_value)

        if existing:
            # Update existing entry
            existing.verification_data = verification_data
            existing.last_verified = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            db.session.commit()
            return existing
        else:
            # Create new entry
            new_verification = cls(
                lead_id=lead_id,
                user_id=None,
                contact_type=contact_type,
                contact_value=contact_value,
                verification_data=verification_data,
                validation_type='lead',
                last_verified=datetime.utcnow()
            )
            db.session.add(new_verification)
            db.session.commit()
            return new_verification

    @classmethod
    def create_or_update_standalone_verification(cls, user_id, contact_type, contact_value, verification_data):
        """
        Create or update standalone verification entry
        """
        existing = cls.find_standalone_verification(user_id, contact_type, contact_value)

        if existing:
            # Update existing entry
            existing.verification_data = verification_data
            existing.last_verified = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            db.session.commit()
            return existing
        else:
            # Create new entry
            new_verification = cls(
                lead_id=None,
                user_id=user_id,
                contact_type=contact_type,
                contact_value=contact_value,
                verification_data=verification_data,
                validation_type='standalone',
                last_verified=datetime.utcnow()
            )
            db.session.add(new_verification)
            db.session.commit()
            return new_verification

    @classmethod
    def get_verification_history(cls, lead_id):
        """
        Get verification history for a lead (lead-associated only)
        """
        return cls.query.filter_by(
            lead_id=lead_id,
            validation_type='lead'
        ).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_standalone_verification_history(cls, user_id):
        """
        Get standalone verification history for a user
        """
        return cls.query.filter_by(
            user_id=user_id,
            validation_type='standalone'
        ).order_by(cls.created_at.desc()).all()