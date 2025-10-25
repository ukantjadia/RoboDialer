from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

class Company(db.Model):
    """Model for company accounts"""
    __tablename__ = 'companies'

    company_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(200), nullable=False)
    domain = db.Column(db.String(100), unique=True, nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    size = db.Column(db.String(50), nullable=True)  # small, medium, large
    description = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Parent-child company relationship
    parent_company_id = db.Column(UUID(as_uuid=True), db.ForeignKey('companies.company_id'), nullable=True)
    
    # Subscription info
    subscription_tier = db.Column(db.String(50), default='silver')  # silver, gold, platinum
    total_credits = db.Column(db.Integer, default=0)
    credits_used = db.Column(db.Integer, default=0)
    max_members = db.Column(db.Integer, default=5)  # based on tier
    
    # Billing
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f'<Company {self.name}>'

    def to_dict(self):
        """Convert Company object to a dictionary."""
        total_credits = self.total_credits if self.total_credits is not None else 'Unlimited'
        credits_remaining = (
            'Unlimited' if self.total_credits is None else self.total_credits - self.credits_used
        )
        return {
            'company_id': str(self.company_id),
            'name': self.name,
            'domain': self.domain,
            'industry': self.industry,
            'size': self.size,
            'description': self.description,
            'website': self.website,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'parent_company_id': str(self.parent_company_id) if self.parent_company_id else None,
            'subscription_tier': self.subscription_tier,
            'total_credits': total_credits,
            'credits_used': self.credits_used,
            'credits_remaining': credits_remaining,
            'max_members': self.max_members,
            'stripe_customer_id': self.stripe_customer_id,
        }

    @staticmethod
    def create(name, domain=None, industry=None, size='medium', subscription_tier=None, parent_company_id=None, created_by=None):
        """Create a new company"""
        from models.plan_model import Plan
        # Jika subscription_tier tidak diisi, ambil dari tier user pembuat
        if not subscription_tier:
            if created_by and getattr(created_by, 'tier', None):
                subscription_tier = created_by.tier
            else:
                subscription_tier = 'silver'
        # Get plan from DB according to subscription_tier
        plan = Plan.query.filter(Plan.plan_name.ilike(subscription_tier)).first()
        # Determine if platinum/unlimited
        is_platinum = (subscription_tier or '').lower().startswith('platinum')
        if is_platinum:
            plan_initial_credits = 0  # Fix: platinum allocation always 0
        else:
            plan_initial_credits = plan.initial_credits if plan else 125
        # Hardcode max_members mapping
        tier_members = {
            'silver': 2,
            'gold': 5,
            'platinum': 10,
            'silver_annual': 2,
            'gold_annual': 5,
            'platinum_annual': 10
        }
        company = Company(
            name=name,
            domain=domain,
            industry=industry,
            size=size,
            subscription_tier=subscription_tier,
            parent_company_id=parent_company_id
        )
        # Set credits from plan or unlimited for platinum
        company.total_credits = plan_initial_credits
        # Set max_members from mapping, default 2
        company.max_members = tier_members.get(subscription_tier, 2)
        db.session.add(company)
        db.session.commit()
        return company

    def update(self, **kwargs):
        """Update company information"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def get_members(self):
        """Get all company members"""
        from models.user_model import User
        return User.query.filter_by(company_id=self.company_id).all()

    def get_admin_members(self):
        """Get company admin members"""
        from models.user_model import User
        return User.query.filter_by(
            company_id=self.company_id,
            is_company_admin=True
        ).all()

    def get_member_count(self):
        """Get current member count"""
        from models.user_model import User
        return User.query.filter_by(company_id=self.company_id).count()

    def can_add_member(self):
        """Check if company can add more members"""
        return self.get_member_count() < self.max_members

    def get_parent_company(self):
        """Get parent company if this is a sub-company"""
        if self.parent_company_id:
            return Company.query.get(self.parent_company_id)
        return None

    def get_sub_companies(self):
        """Get all sub-companies of this company"""
        return Company.query.filter_by(parent_company_id=self.company_id).all()

    def is_sub_company(self):
        """Check if this company is a sub-company"""
        return self.parent_company_id is not None

    def is_parent_company(self):
        """Check if this company has sub-companies"""
        return Company.query.filter_by(parent_company_id=self.company_id).count() > 0

    def delete_with_sub_companies(self):
        """Delete this company and all its sub-companies"""
        from models.company_credit_allocation_model import CompanyCreditAllocation
        from models.user_model import User
        
        # Get all sub-companies recursively
        sub_companies = self.get_all_sub_companies_recursive()
        
        # Delete all sub-companies first
        for sub_company in sub_companies:
            # Remove all members from sub-company
            sub_members = sub_company.get_members()
            for member in sub_members:
                member.company_id = None
                member.is_company_admin = False
                member.company_role = 'member'
            
            # Delete credit allocations for sub-company
            CompanyCreditAllocation.query.filter_by(company_id=sub_company.company_id).delete()
            
            # Delete the sub-company
            db.session.delete(sub_company)
        
        # Remove all members from this company
        members = self.get_members()
        for member in members:
            member.company_id = None
            member.is_company_admin = False
            member.company_role = 'member'
        
        # Delete credit allocations for this company
        CompanyCreditAllocation.query.filter_by(company_id=self.company_id).delete()
        
        # Delete this company
        db.session.delete(self)
        db.session.commit()

    def get_all_sub_companies_recursive(self):
        """Get all sub-companies recursively (including sub-companies of sub-companies)"""
        all_sub_companies = []
        sub_companies = self.get_sub_companies()
        
        for sub_company in sub_companies:
            all_sub_companies.append(sub_company)
            # Recursively get sub-companies of this sub-company
            all_sub_companies.extend(sub_company.get_all_sub_companies_recursive())
        
        return all_sub_companies

    def use_credits(self, amount):
        """Use company credits"""
        if self.subscription_tier == 'platinum':
            return True  # Unlimited credits
        
        if self.credits_used + amount > self.total_credits:
            return False
        
        self.credits_used += amount
        db.session.commit()
        return True

    def reset_credits(self):
        """Reset credits based on tier"""
        tier_credits = {
            'silver': 125,
            'gold': 292,
            'platinum': None
        }
        
        if self.subscription_tier != 'platinum':
            self.total_credits = tier_credits.get(self.subscription_tier, 125)
            self.credits_used = 0
            db.session.commit()
    
    def get_workspaces(self):
        """Get all workspaces for this company"""
        from models.workspace_model import Workspace
        return Workspace.query.filter_by(company_id=self.company_id).all()
    
    def get_workspace_count(self):
        """Get total workspace count"""
        from models.workspace_model import Workspace
        return Workspace.query.filter_by(company_id=self.company_id).count()
    
    def get_active_workspaces(self):
        """Get active workspaces for this company"""
        from models.workspace_model import Workspace
        return Workspace.query.filter_by(company_id=self.company_id, is_active=True).all()
    
    def get_credits_summary(self):
        """Get credits summary for this company"""
        if self.subscription_tier == 'platinum':
            return {
                'total_credits': 'Unlimited',
                'credits_used': self.credits_used,
                'credits_remaining': 'Unlimited',
                'usage_percentage': 0
            }
        else:
            remaining = self.total_credits - self.credits_used
            usage_percentage = (self.credits_used / self.total_credits * 100) if self.total_credits > 0 else 0
            return {
                'total_credits': self.total_credits,
                'credits_used': self.credits_used,
                'credits_remaining': remaining,
                'usage_percentage': round(usage_percentage, 2)
            }