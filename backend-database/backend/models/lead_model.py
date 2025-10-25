from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
import hashlib

db = SQLAlchemy()

class Lead(db.Model):
    __tablename__ = 'leads'
    
    # Primary key
    lead_id = db.Column(db.String(100), primary_key=True)
    
    # Base data
    search_keyword = db.Column(JSONB, nullable=False)  # Base64-encoded JSON string
    draft_data = db.Column(JSONB, nullable=True)  # Draft user data
    
    # Company Information
    company = db.Column(db.String(1000), nullable=False)
    website = db.Column(db.String(1000), nullable=True)
    industry = db.Column(db.String(1000), nullable=True)
    product_category = db.Column(db.String(2000), nullable=True)  # Previously product_service_category
    business_type = db.Column(db.String(1000), nullable=True)
    employees = db.Column(db.Integer, nullable=True)  # Previously employees_range
    revenue = db.Column(db.Float, nullable=True)
    year_founded = db.Column(db.String(20), nullable=True)
    bbb_rating = db.Column(db.String(10), nullable=True)
    
    # Location Information
    street = db.Column(db.String(1000), nullable=True)
    city = db.Column(db.String(1000), nullable=True)
    state = db.Column(db.String(1000), nullable=True)
    
    # Company Contact
    company_phone = db.Column(db.String(20), nullable=True)  # New field
    company_linkedin = db.Column(db.String(1000), nullable=True)  # Previously linkedin_url
    
    # Owner/Contact Information
    owner_first_name = db.Column(db.String(1000), nullable=True)  # Previously first_name
    owner_last_name = db.Column(db.String(1000), nullable=True)  # Previously last_name
    owner_title = db.Column(db.String(1000), nullable=True)  # Previously title
    owner_linkedin = db.Column(db.String(1000), nullable=True)
    owner_phone_number = db.Column(db.String(20), nullable=True)  # New field
    owner_email = db.Column(db.String(1000), nullable=True)  # Previously email
    phone = db.Column(db.String(20), nullable=True)  # Changed from Integer to String
    
    # Source information
    source = db.Column(db.String(1000), nullable=False)  # Growjo / Apollo / both
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(1000), default='new', nullable=False)
    is_edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    edited_by = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<Lead {self.lead_id}: {self.company}>'
    
    # Helper method to convert to dictionary
    def to_dict(self):
        """Convert Lead object to dictionary for API response"""
        return {
            'lead_id': self.lead_id,
            'search_keyword': self.search_keyword,
            'draft_data': self.draft_data,
            'company': self.company,
            'website': self.website,
            'industry': self.industry,
            'product_category': self.product_category,
            'business_type': self.business_type,
            'employees': self.employees,
            'revenue': self.revenue,
            'year_founded': self.year_founded,
            'bbb_rating': self.bbb_rating,
            'street': self.street,
            'city': self.city,
            'state': self.state,
            'company_phone': self.company_phone,
            'company_linkedin': self.company_linkedin,
            'owner_first_name': self.owner_first_name,
            'owner_last_name': self.owner_last_name,
            'owner_title': self.owner_title,
            'owner_linkedin': self.owner_linkedin,
            'owner_phone_number': self.owner_phone_number,
            'owner_email': self.owner_email,
            'phone': self.phone,
            'source': self.source,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted': self.deleted,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'is_edited': self.is_edited,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'edited_by': self.edited_by
        }

    @classmethod
    def generate_lead_id(cls, company, street, city, state, company_phone, website):
        """
        Generate a unique lead_id based on company information.
        Uses SHA-256 hash of combined company details to create a unique identifier.
        """
        # Combine all fields into a single string, using empty string for None values
        combined = f"{company or ''}{street or ''}{city or ''}{state or ''}{company_phone or ''}{website or ''}"
        # Create SHA-256 hash
        hash_object = hashlib.sha256(combined.encode())
        # Return first 32 characters of the hex digest
        return hash_object.hexdigest()[:32]

    def __init__(self, **kwargs):
        # Generate lead_id if not provided
        if 'lead_id' not in kwargs:
            kwargs['lead_id'] = self.generate_lead_id(
                company=kwargs.get('company'),
                street=kwargs.get('street'),
                city=kwargs.get('city'),
                state=kwargs.get('state'),
                company_phone=kwargs.get('company_phone'),
                website=kwargs.get('website')
            )
        super().__init__(**kwargs)