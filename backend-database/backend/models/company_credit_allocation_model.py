from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

class CompanyCreditAllocation(db.Model):
    """Model for company credit allocations to members"""
    __tablename__ = 'company_credit_allocations'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = db.Column(UUID(as_uuid=True), db.ForeignKey('companies.company_id'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    credits_allocated = db.Column(db.Integer, default=0)
    credits_used = db.Column(db.Integer, default=0)
    allocated_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    allocated_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    company = db.relationship('Company', backref='credit_allocations')
    user = db.relationship('User', foreign_keys=[user_id], backref='company_credit_allocations')
    allocator = db.relationship('User', foreign_keys=[allocated_by])

    def __repr__(self):
        return f'<CompanyCreditAllocation {self.company_id} -> {self.user_id}: {self.credits_allocated}>'

    def to_dict(self):
        """Convert CompanyCreditAllocation object to a dictionary."""
        user_info = None
        allocator_info = None
        
        try:
            if self.user:
                user_info = {
                    'username': self.user.username,
                    'email': self.user.email
                }
        except:
            pass
            
        try:
            if self.allocator:
                allocator_info = {
                    'username': self.allocator.username,
                    'email': self.allocator.email
                }
        except:
            pass
        
        return {
            'id': str(self.id),
            'company_id': str(self.company_id),
            'user_id': str(self.user_id),
            'credits_allocated': self.credits_allocated,
            'credits_used': self.credits_used,
            'credits_remaining': self.credits_allocated - self.credits_used,
            'allocated_at': self.allocated_at.isoformat() if self.allocated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'allocated_by': str(self.allocated_by) if self.allocated_by else None,
            'is_active': self.is_active,
            'notes': self.notes,
            'user': user_info,
            'allocator': allocator_info
        }

    @staticmethod
    def create(company_id, user_id, credits_allocated, allocated_by=None, expires_at=None, notes=None):
        """Create a new credit allocation"""
        allocation = CompanyCreditAllocation(
            company_id=company_id,
            user_id=user_id,
            credits_allocated=credits_allocated,
            allocated_by=allocated_by,
            expires_at=expires_at,
            notes=notes
        )
        db.session.add(allocation)
        db.session.commit()
        return allocation

    def update_allocation(self, new_amount, updated_by=None, notes=None):
        """Update the allocated credits"""
        self.credits_allocated = new_amount
        self.allocated_by = updated_by
        self.allocated_at = datetime.utcnow()
        if notes:
            self.notes = notes
        db.session.commit()
        return self

    def use_credits(self, amount):
        """Use allocated credits"""
        if self.credits_used + amount > self.credits_allocated:
            return False
        
        self.credits_used += amount
        db.session.commit()
        return True

    def get_remaining_credits(self):
        """Get remaining credits"""
        return self.credits_allocated - self.credits_used

    def is_expired(self):
        """Check if allocation is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def deactivate(self):
        """Deactivate this allocation"""
        self.is_active = False
        db.session.commit()
        return self

    @staticmethod
    def get_active_allocation(company_id, user_id):
        """Get active allocation for a user in a company"""
        return CompanyCreditAllocation.query.filter_by(
            company_id=company_id,
            user_id=user_id,
            is_active=True
        ).first()

    @staticmethod
    def get_company_allocations(company_id):
        """Get all allocations for a company"""
        return CompanyCreditAllocation.query.filter_by(
            company_id=company_id,
            is_active=True
        ).all()

    @staticmethod
    def get_user_allocations(user_id):
        """Get all allocations for a user"""
        return CompanyCreditAllocation.query.filter_by(
            user_id=user_id,
            is_active=True
        ).all() 