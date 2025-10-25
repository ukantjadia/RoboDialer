from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models.lead_model import db
from datetime import datetime, timedelta
import hashlib
import uuid
import json
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'

    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='user', nullable=False)
    tier = db.Column(db.String(50), default='free', nullable=False)
    company = db.Column(db.String(100))  # New field for company
    last_login_at = db.Column(db.DateTime, nullable=True)  # New field for last login tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    subscription = db.relationship('UserSubscription', backref='user', uselist=False)

    # Company account fields
    company_id = db.Column(UUID(as_uuid=True), db.ForeignKey('companies.company_id'), nullable=True)
    is_company_admin = db.Column(db.Boolean, default=False)
    company_role = db.Column(db.String(50), default='member')  # admin, member, viewer
    status = db.Column(SqlEnum('active', 'cancelled', 's_cancelled', 'pause', name='userstatus'), default='active', nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    linkedin_url = db.Column(db.String(255), nullable=True)

    # Team fields - commented out to avoid database migration issues
    # active_team_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id'), nullable=True)

    # # Email verification and password reset fields
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verification_sent_at = db.Column(db.DateTime, nullable=True)
    password_reset_sent_at = db.Column(db.DateTime, nullable=True)

    # # Release notes dismiss tracking
    dismissed_notes = db.Column(db.Text, nullable=True)  # JSON string of dismissed note IDs

    # EmailGen template initialization flag
    has_initialized_templates = db.Column(db.Boolean, default=False, nullable=False)

    def get_id(self):
        """Return user_id as the identifier for Flask-Login"""
        return str(self.user_id)

    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if password matches"""
        return check_password_hash(self.password_hash, password)

    def has_role(self, role):
        """Check if user has specific role"""
        return self.role == role

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'

    def is_developer(self):
        """Check if user is developer"""
        return self.role == 'developer'

    def is_staff(self):
        """Check if user is admin or developer"""
        return self.role in ['admin', 'developer']

    def is_company_member_role(self):
        """Check if user has company member role"""
        return self.role == 'company_member'

    def is_company_admin_user(self):
        """Check if user is a company admin"""
        return self.is_company_admin

    def is_company_member(self):
        """Check if user is part of a company"""
        return self.company_id is not None

    def get_company(self):
        """Get the company this user belongs to"""
        if self.company_id:
            from models.company_model import Company
            return Company.query.get(self.company_id)
        return None

    def can_manage_company(self):
        """Check if user can manage company (admin or company admin)"""
        return self.role in ['admin', 'developer'] or self.is_company_admin

    def get_dismissed_notes(self):
        """Get list of dismissed note IDs"""
        if not self.dismissed_notes:
            return []
        try:
            return json.loads(self.dismissed_notes)
        except (json.JSONDecodeError, TypeError):
            return []

    def add_dismissed_note(self, note_id):
        """Add a note ID to dismissed notes"""
        dismissed = self.get_dismissed_notes()
        if note_id not in dismissed:
            dismissed.append(note_id)
            self.dismissed_notes = json.dumps(dismissed)
            db.session.commit()

    def remove_dismissed_note(self, note_id):
        """Remove a note ID from dismissed notes"""
        dismissed = self.get_dismissed_notes()
        if note_id in dismissed:
            dismissed.remove(note_id)
            self.dismissed_notes = json.dumps(dismissed) if dismissed else None
            db.session.commit()

    def has_dismissed_note(self, note_id):
        """Check if user has dismissed a specific note"""
        return note_id in self.get_dismissed_notes()

    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login_at = datetime.utcnow()
        db.session.commit()

    @classmethod
    def get_active_users_count(cls, days=30):
        """Get count of users active in last X days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return cls.query.filter(
            cls.last_login_at >= cutoff_date,
            cls.status == 'active'
        ).count()

    @classmethod
    def get_inactive_users(cls, days=30):
        """Get users inactive for X+ days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return cls.query.filter(
            (cls.last_login_at < cutoff_date) | (cls.last_login_at.is_(None)),
            cls.status == 'active'
        ).all()

    @classmethod
    def get_users_by_last_login(cls, days=30):
        """Get users grouped by last login activity"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        active_users = cls.query.filter(
            cls.last_login_at >= cutoff_date,
            cls.status == 'active'
        ).all()

        inactive_users = cls.query.filter(
            (cls.last_login_at < cutoff_date) | (cls.last_login_at.is_(None)),
            cls.status == 'active'
        ).all()

        return {
            'active': active_users,
            'inactive': inactive_users,
            'total_active': len(active_users),
            'total_inactive': len(inactive_users)
        }

    def __repr__(self):
        return f'<User {self.username}>'

    @classmethod
    def generate_user_id(cls, email, password):
        """
        Generate a unique user_id based on email and password.
        Uses SHA-256 hash of combined email and password.
        """
        combined = f"{email or ''}{password or ''}"
        hash_object = hashlib.sha256(combined.encode())
        return hash_object.hexdigest()[:32]

    def __init__(self, **kwargs):
        # Generate user_id if not provided
        if 'user_id' not in kwargs:
            kwargs['user_id'] = self.generate_user_id(
                email=kwargs.get('email'),
                password=kwargs.get('password')
            )
        super().__init__(**kwargs)


    def pending_workspace_invitations(self):
        """Get pending workspace invitations for this user"""
        try:
            from models.workspace_invitation_model import WorkspaceInvitation
            return WorkspaceInvitation.query.filter_by(
                email=self.email,
                status='pending'
            ).all()
        except Exception:
            return []

    def to_dict(self):
        company_data = None
        if self.company_id:
            company = self.get_company()
            if company:
                company_data = {
                    'company_id': str(company.company_id),
                    'name': company.name,
                    'subscription_tier': company.subscription_tier
                }
        # Add credit allocation info
        credits_allocated = 0
        credits_used = 0
        credits_remaining = 0
        if self.company_id:
            try:
                from models.company_credit_allocation_model import CompanyCreditAllocation
                allocation = CompanyCreditAllocation.get_active_allocation(self.company_id, self.user_id)
                if allocation:
                    credits_allocated = allocation.credits_allocated
                    credits_used = allocation.credits_used
                    credits_remaining = allocation.credits_allocated - allocation.credits_used
            except Exception:
                pass

        # Calculate days since last login
        days_since_last_login = None
        if self.last_login_at:
            days_since_last_login = (datetime.utcnow() - self.last_login_at).days

        return {
            "user_id": str(self.user_id),
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "tier": self.tier,
            "company": self.company,
            "company_id": str(self.company_id) if self.company_id else None,
            "is_company_admin": self.is_company_admin,
            "company_role": self.company_role,
            "company_data": company_data,
            "linkedin_url": self.linkedin_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "days_since_last_login": days_since_last_login,
            "status": self.status,
            "is_active": self.is_active,
            "is_email_verified": self.is_email_verified,
            "email_verification_sent_at": self.email_verification_sent_at.isoformat() if self.email_verification_sent_at else None,
            "password_reset_sent_at": self.password_reset_sent_at.isoformat() if self.password_reset_sent_at else None,
            "dismissed_notes": self.dismissed_notes,
            # Add credit allocation fields
            "credits_allocated": credits_allocated,
            "credits_used": credits_used,
            "credits_remaining": credits_remaining
        }