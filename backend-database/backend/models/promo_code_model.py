from models.lead_model import db
from datetime import datetime, timezone

class PromoCode(db.Model):
    __tablename__ = 'promo_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    stripe_coupon_id = db.Column(db.String(255), nullable=False, index=True)
    stripe_coupon_name = db.Column(db.String(255), nullable=True)
    stripe_promo_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    code = db.Column(db.String(255), nullable=True)
    times_redeemed = db.Column(db.Integer, nullable=False, default=0)
    amount_off = db.Column(db.Numeric(10, 2), nullable=True) # In USD, $10.00
    percent_off = db.Column(db.Numeric(5, 2), nullable=True) # e.g., 25.000 for 25%
    currency = db.Column(db.String(3), nullable=True)
    duration = db.Column(db.String(50), nullable=False) # 'once', 'repeating', 'forever'
    duration_in_months = db.Column(db.Integer, nullable=True) # For 'repeating' duration
    max_redemptions = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    livemode = db.Column(db.Boolean, nullable=False) # True if live, False if in test mode
    expires_at = db.Column(db.DateTime, nullable=True)
    synced_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    # restrictions from stripe setting
    first_time_transaction = db.Column(db.Boolean, nullable=False)
    minimum_amount =  db.Column(db.Integer, nullable=True)
    minimum_amount_currency =  db.Column(db.String(3), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'stripe_coupon_id': self.stripe_coupon_id,
            'stripe_coupon_name': self.stripe_coupon_name,
            'stripe_promo_id': self.stripe_promo_id,
            'name': self.name,
            'times_redeemed': self.times_redeemed,
            'amount_off': self.amount_off,
            'percent_off': str(self.percent_off) if self.percent_off else None,
            'currency': self.currency,
            'duration': self.duration,
            'duration_in_months': self.duration_in_months,
            'max_redemptions': self.max_redemptions,
            'is_active': self.is_active,
            'livemode': self.livemode,
        }