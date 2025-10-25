from functools import wraps
from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for
from flask_login import current_user
from controllers.coupon_controller import CouponController
from models.user_model import User
from models.user_subscription_model import UserSubscription

coupon_bp = Blueprint('coupon', __name__)

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (not current_user.is_admin() and current_user.role != 'developer'):
            return jsonify({"error": "Unauthorized access"}), 403
        return f(*args, **kwargs)
    return decorated_function

@coupon_bp.route('/api/coupons/sync-db', methods=['POST'])
@super_admin_required
def sync_db():
    try: 
        CouponController.sync_stripe_coupon_usage_with_db()
        return jsonify({
            "status": "success",
            "message": "Coupon data from Stripe is already synced with database"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Error syncing Stripe data with database: {str(e)}"
        })

@coupon_bp.route('/coupons/apply-promo-to-user/<user_id>', methods=['GET','POST'])
@super_admin_required
def apply_promo_to_user(user_id:str):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('user_management.user_management'))

    subscription = UserSubscription.query.get(user_id)
    if not subscription:
        flash("This user does not have an active subscription to apply a code to.", 'danger')
        return redirect(url_for('coupon.apply_promo_to_user', user_id=user.user_id))

    if request.method == 'POST':
        promo_code = request.form.get("promo_code")
        if not promo_code:
            flash("You must provide a promotion code.", 'warning')
            return redirect(url_for('coupon.apply_promo_to_user', user_id=user.user_id))

        res = CouponController.apply_promo_code_to_user_subscription(user_id, promo_code)
        
        if res.get("success"):
            flash(f"Successfully applied promo code '{promo_code}' to {user.username}.", 'success')
            return redirect(url_for('user_management.user_management'))
        else:
            flash(f"Error applying code: {res.get('error', 'Unknown error')}", 'danger')
            return redirect(url_for('coupon.apply_promo_to_user', user_id=user.user_id))
        
    return render_template(
        'admin/apply_coupon.html',
        user=user,
        subscription=subscription
    )