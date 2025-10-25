from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone

class CouponUsage(db.Model):
    __tablename__ = 'coupon_usages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False, index=True)
    promo_code_id = db.Column(db.Integer, db.ForeignKey('promo_codes.id'), nullable=False)
    stripe_subscription_id = db.Column(db.String(255), nullable=False, index=True)
    livemode = db.Column(db.Boolean, nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

