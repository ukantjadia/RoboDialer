from models.lead_model import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum as SqlEnum

class CreditsLog(db.Model):
    """Model for tracking all credit changes for audit purposes"""
    __tablename__ = 'credits_logs'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = db.Column(UUID(as_uuid=True), db.ForeignKey('workspaces.workspace_id'), nullable=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # Credits added (+) or removed (-)
    reason = db.Column(db.Text, nullable=False)  # Reason for credit change
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)  # Who made the change
    transaction_type = db.Column(SqlEnum('allocation', 'usage', 'transfer', 'refund', 'bonus', 'penalty', name='transaction_type'), nullable=False)
    reference_id = db.Column(UUID(as_uuid=True), nullable=True)  # Reference to related entity (project, task, etc.)
    reference_type = db.Column(db.String(50), nullable=True)  # Type of reference (project, task, etc.)
    notes = db.Column(db.Text, nullable=True)  # Additional notes

    def __repr__(self):
        return f'<CreditsLog {self.user_id}: {self.amount} credits>'

    def to_dict(self):
        """Convert CreditsLog object to a dictionary."""
        created_by_user = None
        if self.created_by:
            from models.user_model import User
            user = User.query.get(self.created_by)
            if user:
                created_by_user = {
                    'user_id': str(user.user_id),
                    'username': user.username,
                    'email': user.email
                }

        user_data = None
        if self.user_id:
            from models.user_model import User
            user = User.query.get(self.user_id)
            if user:
                user_data = {
                    'user_id': str(user.user_id),
                    'username': user.username,
                    'email': user.email
                }

        return {
            'id': str(self.id),
            'team_id': str(self.team_id),
            'user_id': str(self.user_id),
            'amount': self.amount,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': str(self.created_by) if self.created_by else None,
            'transaction_type': self.transaction_type,
            'reference_id': str(self.reference_id) if self.reference_id else None,
            'reference_type': self.reference_type,
            'notes': self.notes,
            'created_by_user': created_by_user,
            'user_data': user_data
        }

    @staticmethod
    def create(team_id, user_id, amount, reason, created_by=None, transaction_type='usage', 
               reference_id=None, reference_type=None, notes=None):
        """Create a new credits log entry"""
        log = CreditsLog(
            team_id=team_id,
            user_id=user_id,
            amount=amount,
            reason=reason,
            created_by=created_by,
            transaction_type=transaction_type,
            reference_id=reference_id,
            reference_type=reference_type,
            notes=notes
        )
        db.session.add(log)
        db.session.commit()
        return log

    @staticmethod
    def log_allocation(team_id, user_id, amount, allocated_by, notes=None):
        """Log credit allocation"""
        return CreditsLog.create(
            team_id=team_id,
            user_id=user_id,
            amount=amount,
            reason=f"Credit allocation of {amount} credits",
            created_by=allocated_by,
            transaction_type='allocation',
            notes=notes
        )

    @staticmethod
    def log_usage(team_id, user_id, amount, reason, reference_id=None, reference_type=None, created_by=None):
        """Log credit usage"""
        return CreditsLog.create(
            team_id=team_id,
            user_id=user_id,
            amount=-amount,  # Negative for usage
            reason=reason,
            created_by=created_by,
            transaction_type='usage',
            reference_id=reference_id,
            reference_type=reference_type
        )

    @staticmethod
    def log_transfer(from_team_id, from_user_id, to_team_id, to_user_id, amount, created_by, notes=None):
        """Log credit transfer between users"""
        # Log deduction from sender
        CreditsLog.create(
            team_id=from_team_id,
            user_id=from_user_id,
            amount=-amount,
            reason=f"Credit transfer to {to_user_id}",
            created_by=created_by,
            transaction_type='transfer',
            notes=notes
        )
        
        # Log addition to receiver
        return CreditsLog.create(
            team_id=to_team_id,
            user_id=to_user_id,
            amount=amount,
            reason=f"Credit transfer from {from_user_id}",
            created_by=created_by,
            transaction_type='transfer',
            notes=notes
        )

    @staticmethod
    def log_refund(team_id, user_id, amount, reason, created_by, reference_id=None, reference_type=None):
        """Log credit refund"""
        return CreditsLog.create(
            team_id=team_id,
            user_id=user_id,
            amount=amount,
            reason=reason,
            created_by=created_by,
            transaction_type='refund',
            reference_id=reference_id,
            reference_type=reference_type
        )

    @staticmethod
    def log_bonus(team_id, user_id, amount, reason, created_by, notes=None):
        """Log bonus credits"""
        return CreditsLog.create(
            team_id=team_id,
            user_id=user_id,
            amount=amount,
            reason=reason,
            created_by=created_by,
            transaction_type='bonus',
            notes=notes
        )

    @staticmethod
    def log_penalty(team_id, user_id, amount, reason, created_by, notes=None):
        """Log credit penalty"""
        return CreditsLog.create(
            team_id=team_id,
            user_id=user_id,
            amount=-amount,
            reason=reason,
            created_by=created_by,
            transaction_type='penalty',
            notes=notes
        )

    @staticmethod
    def get_user_credits_history(user_id, team_id=None, limit=50, offset=0):
        """Get credit history for a user"""
        query = CreditsLog.query.filter_by(user_id=user_id)
        if team_id:
            query = query.filter_by(team_id=team_id)
        return query.order_by(CreditsLog.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def get_team_credits_history(team_id, limit=50, offset=0):
        """Get credit history for a team"""
        return CreditsLog.query.filter_by(team_id=team_id)\
            .order_by(CreditsLog.created_at.desc())\
            .offset(offset).limit(limit).all()

    @staticmethod
    def log_credit_request(team_id, user_id, amount, notes=None):
        """Log credit request"""
        return CreditsLog.create(
            team_id=team_id,
            user_id=user_id,
            amount=amount,
            reason=f"Credit request for {amount} credits",
            created_by=user_id,
            transaction_type='allocation',
            reference_type='credit_request',
            notes=notes
        )

    @staticmethod
    def get_user_credits_summary(user_id, team_id=None):
        """Get credit summary for a user"""
        query = db.session.query(
            db.func.sum(CreditsLog.amount).label('total_credits'),
            db.func.count(CreditsLog.id).label('transaction_count')
        ).filter(CreditsLog.user_id == user_id)
        
        if team_id:
            query = query.filter(CreditsLog.team_id == team_id)
        
        result = query.first()
        return {
            'total_credits': result.total_credits or 0,
            'transaction_count': result.transaction_count or 0
        } 