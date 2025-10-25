from models.lead_model import db
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone

# One-to-one with user table
class LastCouponByUser(db.Model):
    __tablename__ = 'last_coupon_by_users'

    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False, index=True, primary_key=True)
    stripe_coupon_id = db.Column(db.String(255), nullable=False, index=True)
    currency = db.Column(db.String(3), nullable=True)
    amount_off = db.Column(db.Numeric(10, 2), nullable=True) # In cent, $10.00
    percent_off = db.Column(db.Numeric(5, 2), nullable=True) # e.g., 25.0 for 25%
    promo_code = db.Column(db.String(255), nullable=False)
    stripe_subscription_id = db.Column(db.String(255), nullable=False, index=True)
    stripe_invoice_id = db.Column(db.String(255), nullable=False)
    livemode = db.Column(db.Boolean, nullable=False) # True if it's in live environment, False if in test mode
    expires_at = db.Column(db.DateTime, nullable=True) # When the discount expires for the user's subscription, null it is forever discount coupon
    applied_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
