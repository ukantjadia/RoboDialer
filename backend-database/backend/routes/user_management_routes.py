from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from models.user_model import User
from models.user_subscription_model import UserSubscription
from models.lead_model import db
from models.credit_transfer_log_model import CreditTransferLog
from functools import wraps
from datetime import datetime, timedelta
from models.user_lead_drafts_model import UserLeadDraft
from utils.decorators import role_required
import uuid
from models.last_coupon_by_user_model import LastCouponByUser

user_management_bp = Blueprint('user_management', __name__)

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (not current_user.is_admin() and current_user.role != 'developer'):
            return jsonify({"error": "Unauthorized access"}), 403
        return f(*args, **kwargs)
    return decorated_function

@user_management_bp.route('/admin/users')
@login_required
@super_admin_required
def user_management():
    """Render the user management page"""
    return render_template('admin/user_management.html')

@user_management_bp.route('/api/admin/users')
@login_required
@super_admin_required
def get_users():
    """Get all users with their subscription information"""
    current_app.logger.info(f"Fetching all users and their subscription info by admin: {current_user.username}")

    try:
        # Get all users, subscriptions, and coupons in separate queries
        users = User.query.all()
        subscriptions = UserSubscription.query.all()
        coupons = LastCouponByUser.query.all()
        subscription_dict = {sub.user_id: sub for sub in subscriptions}
        coupon_dict = {coupon.user_id: coupon for coupon in coupons}

        user_list = []
        for user in users:
            try:
                subscription = subscription_dict.get(user.user_id)
                user_data = {
                    'id': str(user.user_id),
                    'username': user.username,
                    'email': user.email,
                    'is_active': user.is_active,
                    'role': user.role,
                    'tier': user.tier,
                    'status': user.status,
                    'is_email_verified': user.is_email_verified if hasattr(user, 'is_email_verified') else False,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'subscription': {
                        'plan': subscription.plan_name if subscription else None,
                        'status': 'active' if subscription and subscription.plan_expiration_timestamp and subscription.plan_expiration_timestamp > datetime.utcnow() else 'inactive',
                        'credits': subscription.credits_remaining if subscription else 0,
                        'expires_at': subscription.plan_expiration_timestamp.isoformat() if subscription and subscription.plan_expiration_timestamp else None,
                        'is_canceled': subscription.is_canceled if subscription else False,
                        'is_scheduled_for_cancellation': subscription.payment_frequency and '_scheduled_cancel' in subscription.payment_frequency if subscription else False,
                        'payment_frequency': subscription.payment_frequency if subscription else None,
                        'is_paused': getattr(subscription, 'is_paused', False) if subscription else False,
                        'pause_status': getattr(subscription, 'pause_status', 'none') if subscription else 'none',
                        'pause_start_date': subscription.pause_start_date.isoformat() if subscription and getattr(subscription, 'pause_start_date', None) else None,
                        'pause_end_date': subscription.pause_end_date.isoformat() if subscription and getattr(subscription, 'pause_end_date', None) else None,
                        'pause_duration_days': getattr(subscription, 'pause_duration_days', None) if subscription else None
                    } if subscription else {
                        'plan': None,
                        'status': 'inactive',
                        'credits': 0,
                        'expires_at': None,
                        'is_canceled': False,
                        'is_scheduled_for_cancellation': False,
                        'payment_frequency': None,
                        'is_paused': False,
                        'pause_status': 'none',
                        'pause_start_date': None,
                        'pause_end_date': None,
                        'pause_duration_days': None
                    },
                    'coupon': {
                        'has_active_coupon': False,
                        'promo_code': None,
                        'discount_type': None,
                        'discount_value': None,
                        'expires_at': None,
                        'applied_at': None
                    }
                }

                # Add coupon information if exists
                coupon = coupon_dict.get(user.user_id)
                if coupon:
                    is_active = coupon.expires_at is None or (coupon.expires_at and coupon.expires_at > datetime.utcnow())
                    user_data['coupon'] = {
                        'has_active_coupon': is_active,
                        'promo_code': coupon.promo_code,
                        'discount_type': 'amount' if coupon.amount_off else 'percent',
                        'discount_value': float(coupon.amount_off) if coupon.amount_off else float(coupon.percent_off),
                        'currency': coupon.currency,
                        'expires_at': coupon.expires_at.isoformat() if coupon.expires_at else None,
                        'applied_at': coupon.applied_at.isoformat() if coupon.applied_at else None,
                        'stripe_coupon_id': coupon.stripe_coupon_id,
                        'stripe_subscription_id': coupon.stripe_subscription_id
                    }

                user_list.append(user_data)
            except Exception as e:
                current_app.logger.error(f"Error processing user {user.user_id}, {user.username}: {str(e)}")
                continue

        current_app.logger.info(f"Total users processed: {len(user_list)}")
        return jsonify({
            'total': len(user_list),
            'users': user_list
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching users: {str(e)}")
        return jsonify({'error': 'Failed to fetch users'}), 500

# @user_management_bp.route('/api/admin/users_simple')
# @login_required
# # @super_admin_required
# def get_users_simple():
#     """Get all users with their subscription information (simple version, matching original keys) in batches of 200"""
#     from models.user_model import User
#     from models.user_subscription_model import UserSubscription
#     from datetime import datetime

#     batch_size = 200
#     offset = 0
#     user_list = []
#     try:
#         while True:
#             users = User.query.offset(offset).limit(batch_size).all()
#             if not users:
#                 break
#             for idx, user in enumerate(users, start=offset+1):
#                 try:
#                     current_app.logger.info(f"Processed user {idx}: {user.username}")
#                     subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
#                     user_data = {
#                         'id': str(user.user_id),
#                         'username': user.username or "",
#                         'email': user.email or "",
#                         'is_active': bool(user.is_active),
#                         'role': user.role or "user",
#                         'created_at': user.created_at.isoformat() if user.created_at else None,
#                         'subscription': {
#                             'plan': subscription.plan_name if subscription else None,
#                             'status': 'active' if subscription and subscription.plan_expiration_timestamp and subscription.plan_expiration_timestamp > datetime.utcnow() else 'inactive',
#                             'credits': subscription.credits_remaining if subscription else 0,
#                             'expires_at': subscription.plan_expiration_timestamp.isoformat() if subscription and subscription.plan_expiration_timestamp else None
#                         } if subscription else {
#                             'plan': None,
#                             'status': 'inactive',
#                             'credits': 0,
#                             'expires_at': None
#                         }
#                     }
#                     user_list.append(user_data)
#                     current_app.logger.info(f"Processed user {idx}: {user.username}")
#                 except Exception as e:
#                     current_app.logger.error(f"Error processing user {getattr(user, 'user_id', 'unknown')}, {getattr(user, 'username', 'unknown')}: {str(e)}")
#                     continue
#             offset += batch_size
#     except Exception as e:
#         current_app.logger.error(f"Error fetching users or subscriptions: {str(e)}")
#         return jsonify({'error': 'Failed to fetch users'}), 500

#         current_app.logger.info(f"Total users processed: {len(user_list)}")
#         return jsonify({
#             'count': len(user_list),
#             'users': user_list
#         })
#     except Exception as e:
#         current_app.logger.error(f"Error fetching users or subscriptions: {str(e)}")
#         return jsonify({'error': 'Failed to fetch users'}), 500

@user_management_bp.route('/api/admin/users/<user_id>/subscription', methods=['PUT'])
@login_required
@super_admin_required
def update_subscription(user_id):
    """Update a user's subscription"""
    data = request.get_json()
    user = User.query.get_or_404(user_id)

    subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
    if not subscription:
        subscription = UserSubscription(user_id=user.user_id)
        db.session.add(subscription)

    if 'plan' in data:
        subscription.plan_name = data['plan']
    if 'status' in data:
        if data['status'] == 'active':
            subscription.plan_expiration_timestamp = datetime.utcnow() + timedelta(days=30)  # Default to 30 days
        else:
            subscription.plan_expiration_timestamp = datetime.utcnow()
    if 'credits' in data:
        subscription.credits_remaining = data['credits']
    if 'expires_at' in data:
        subscription.plan_expiration_timestamp = datetime.fromisoformat(data['expires_at'])

    db.session.commit()
    return jsonify({"message": "Subscription updated successfully"})

@user_management_bp.route('/api/admin/users/<user_id>/add_credits', methods=['POST'])
@login_required
@super_admin_required
def add_user_credits(user_id):
    """Add credits to a user's account (admin only)"""
    try:
        data = request.get_json()
        credits_to_add = data.get('credits', 0)
        reason = data.get('reason', 'not given')

        if credits_to_add <= 0:
            return jsonify({"error": "Credits to add must be greater than 0"}), 400

        user = User.query.get_or_404(user_id)

        # Prevent admin from adding credits to their own account
        if str(user.user_id) == str(current_user.user_id):
            return jsonify({"error": "You cannot add credits to your own account via this admin route"}), 400

        subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
        if not subscription:
            # Create subscription if it doesn't exist
            subscription = UserSubscription(user_id=user.user_id)
            db.session.add(subscription)

        # Add credits
        old_credits = subscription.credits_remaining or 0
        subscription.credits_remaining = old_credits + credits_to_add

        # Create credit transfer log entry
        transfer_log = CreditTransferLog(
            company_id=user.company_id,  # Use user's company_id
            from_user_id=current_user.user_id,  # Admin who transferred
            to_user_id=user.user_id,  # User who received
            amount=credits_to_add,
            note=reason
        )
        db.session.add(transfer_log)

        # Log the credit addition
        current_app.logger.info(f"Admin {current_user.username} ({current_user.user_id}) added {credits_to_add} credits to user {user.username} ({user.user_id}). Reason: {reason}. Old credits: {old_credits}, New credits: {subscription.credits_remaining}")

        db.session.commit()

        return jsonify({
            "message": f"Successfully added {credits_to_add} credits to {user.username}",
            "old_credits": old_credits,
            "new_credits": subscription.credits_remaining,
            "credits_added": credits_to_add
        })

    except Exception as e:
        current_app.logger.error(f"Error adding credits to user {user_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Failed to add credits: {str(e)}"}), 500

@user_management_bp.route('/api/admin/add-credits-by-email', methods=['POST'])
@login_required
@role_required('admin')
def add_credits_by_email():
    """Add 2000 credits to user account by email (admin role only)"""
    try:
        # Check if current user is admin
        if not current_user.is_admin():
            return jsonify({"error": "Only admin role can use this endpoint"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON payload required"}), 400

        email = data.get('email')
        if not email:
            return jsonify({"error": "Email is required in payload"}), 400

        # Find user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"error": f"User with email '{email}' not found"}), 404

        credits_to_add = 2000  # Fixed amount for admin
        reason = f'Admin bulk credit addition (2000 credits) by {current_user.username}'

        subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
        if not subscription:
            # Create subscription if it doesn't exist
            subscription = UserSubscription(
                user_id=user.user_id,
                credits_remaining=credits_to_add,
                username=user.username
            )
            db.session.add(subscription)
            old_credits = 0
        else:
            # Add credits to existing subscription
            old_credits = subscription.credits_remaining or 0
            subscription.credits_remaining = old_credits + credits_to_add

        # Log the credit addition
        current_app.logger.info(f"Admin {current_user.username} ({current_user.user_id}) added {credits_to_add} credits to user {user.username} ({user.user_id}) via email {email}. Reason: {reason}. Old credits: {old_credits}, New credits: {subscription.credits_remaining}")

        db.session.commit()

        return jsonify({
            "message": f"Successfully added {credits_to_add} credits to user {user.username}",
            "old_credits": old_credits,
            "new_credits": subscription.credits_remaining,
            "credits_added": credits_to_add,
            "target_user": user.username,
            "target_email": email,
            "admin_user": current_user.username
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error adding bulk credits by email: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Failed to add credits: {str(e)}"}), 500

@user_management_bp.route('/api/admin/users/<user_id>/toggle-status', methods=['POST'])
@login_required
@super_admin_required
def toggle_user_status(user_id):
    """Toggle a user's active status"""
    user = User.query.get_or_404(user_id)
    if str(user.user_id) == str(current_user.user_id):
        return jsonify({"error": "Cannot deactivate your own account"}), 400

    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({"message": "User status updated successfully", "is_active": user.is_active})

@user_management_bp.route('/api/admin/users/<user_id>/set_email_verified', methods=['POST'])
@login_required
@super_admin_required
def set_user_email_verified(user_id):
    """Set a user's email verification status (admin only)"""
    try:
        data = request.get_json()
        is_email_verified = data.get('is_email_verified', False)

        if not isinstance(is_email_verified, bool):
            return jsonify({"error": "is_email_verified must be a boolean value"}), 400

        user = User.query.get_or_404(user_id)

        # Prevent admin from changing their own email verification status
        if str(user.user_id) == str(current_user.user_id):
            return jsonify({"error": "You cannot change your own email verification status via this admin route"}), 400

        # Update the email verification status
        old_status = user.is_email_verified if hasattr(user, 'is_email_verified') else False
        user.is_email_verified = is_email_verified

        # Log the change
        current_app.logger.info(f"Admin {current_user.username} ({current_user.user_id}) changed email verification status for user {user.username} ({user.user_id}) from {old_status} to {is_email_verified}")

        db.session.commit()

        return jsonify({
            "message": f"Successfully updated email verification status for {user.username}",
            "old_status": old_status,
            "new_status": is_email_verified,
            "user_id": str(user.user_id)
        })

    except Exception as e:
        current_app.logger.error(f"Error updating email verification status for user {user_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Failed to update email verification status: {str(e)}"}), 500

@user_management_bp.route('/admin/user-drafts')
@login_required
@super_admin_required
def user_draft():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '', type=str)

    # First get the base query
    query = User.query

    # Apply search filter if search term exists
    if search:
        search_pattern = f"%{search}%"
        query = query.filter((User.username.ilike(search_pattern)) | (User.email.ilike(search_pattern)))

    # Get total before pagination for accurate count
    total = query.count()

    # Then apply pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items

    user_list = []
    for user in users:
        try:
            # Check if user has any drafts
            has_drafts = UserLeadDraft.query.filter_by(user_id=user.user_id, is_deleted=False).first() is not None
            user_list.append({
                'id': str(user.user_id),
                'username': user.username,
                'email': user.email,
                'tier': user.tier,
                'has_draft': has_drafts  # Add this flag
            })
        except Exception as e:
            print(f"Error querying drafts for user_id={user.user_id}: {e}")
            import traceback; traceback.print_exc()
            user_list.append({
                'id': str(user.user_id),
                'username': user.username,
                'email': user.email,
                'tier': user.tier,
                'has_draft': False
            })

    # Calculate total pages
    pages = (total + per_page - 1) // per_page

    # Calculate pagination display range
    max_display = 2
    start_page = max(1, page - max_display)
    end_page = min(pages, start_page + max_display * 2)
    start_page = max(1, end_page - max_display * 2)

    # Calculate start and end index for showing entries
    start_index = (page - 1) * per_page + 1
    end_index = min((page - 1) * per_page + per_page, total)

    return render_template('admin/user_draft.html',
                         users=user_list,
                         page=page,
                         per_page=per_page,
                         total=total,
                         pages=pages,
                         start_page=start_page,
                         end_page=end_page,
                         start_index=start_index,
                         end_index=end_index,
                         search=search)

@user_management_bp.route('/admin/user-drafts/<user_id>')
@login_required
@super_admin_required
def user_draft_by_user(user_id):
    drafts = UserLeadDraft.query.filter_by(user_id=user_id, is_deleted=False).all()

    draft_list = []
    for d in drafts:
        draft_dict = d.to_dict()
        user = User.query.get(d.user_id)

        draft_dict['username'] = user.username if user else '-'
        draft_dict['email'] = user.email if user else '-'
        draft_dict['tier'] = user.tier if user and hasattr(user, 'tier') else '-'
        draft_list.append(draft_dict)

    user = User.query.get(user_id)
    return render_template('admin/user_draft.html', drafts=draft_list, selected_user=user)

@user_management_bp.route('/api/admin/user-drafts/<user_id>', methods=['GET'])
@login_required
@super_admin_required
def api_admin_user_drafts(user_id):
    """API: Get all drafts for a specific user (admin only) with pagination"""
    from models.user_lead_drafts_model import UserLeadDraft
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    pagination = UserLeadDraft.query.filter_by(user_id=user_id, is_deleted=False).order_by(UserLeadDraft.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    drafts = pagination.items
    return jsonify({
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
        "drafts": [d.to_dict() for d in drafts]
    })

@user_management_bp.route('/api/admin/users/<user_id>/apply_promo', methods=['POST'])
@login_required
@super_admin_required
def apply_promo_to_user(user_id):
    """Apply promo code to user's subscription (admin only)"""
    from controllers.coupon_controller import CouponController

    try:
        data = request.get_json()
        promo_code = data.get('promo_code', '').strip()

        if not promo_code:
            return jsonify({"error": "Promo code is required"}), 400

        user = User.query.get_or_404(user_id)

        # Prevent admin from applying promo to their own account
        if str(user.user_id) == str(current_user.user_id):
            return jsonify({"error": "You cannot apply promo codes to your own account"}), 400

        # Apply the promo code using the controller
        result = CouponController.apply_promo_code_to_user_subscription(str(user.user_id), promo_code)

        if result["success"]:
            # Log the promo code application
            current_app.logger.info(f"Admin {current_user.username} ({current_user.user_id}) applied promo code '{promo_code}' to user {user.username} ({user.user_id})")

            return jsonify({
                "message": f"Successfully applied promo code '{promo_code}' to {user.username}",
                "promo_code": promo_code,
                "user_id": str(user.user_id)
            })
        else:
            return jsonify({"error": result["error"]}), 400

    except Exception as e:
        current_app.logger.error(f"Error applying promo code to user {user_id}: {str(e)}")
        return jsonify({"error": f"Failed to apply promo code: {str(e)}"}), 500