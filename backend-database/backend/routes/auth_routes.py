from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, current_app
from controllers.auth_controller import AuthController
from controllers.subscription_controller import SubscriptionController
from flask_login import login_required, current_user, login_user, logout_user
from utils.decorators import role_required
from models.user_model import User
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os
from models.user_subscription_model import UserSubscription
from models.edit_lead_drafts_model import EditLeadDraft
from models.user_lead_drafts_model import UserLeadDraft
from models.lead_model import Lead, db
from models.audit_logs_model import AuditLog
from sqlalchemy.orm import joinedload


auth_bp = Blueprint('auth', __name__)

# Get secret key from environment or use a default for development
SECRET_KEY = os.environ.get('SECRET_KEY')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        # return redirect("https://app.saasquatchleads.com/")

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        success, message = AuthController.login(username, password)

        if success:
            flash(message, 'success')
            # return redirect("https://app.saasquatchleads.com/")
            return redirect(url_for('main.index'))
        else:
            flash(message, 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
# @login_required
# @role_required('admin', 'developer')
def signup():
    """Handle user registration - Only admin and developer can create accounts"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        company = request.form.get('company', '')  # Get company from form

        # Default role is 'user', but admin can change it
        role = request.form.get('role', 'user')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('auth/signup.html')

        success, message = AuthController.register(username, email, password, role, company)

        if success:
            flash(message, 'success')
            # If admin creates a user, redirect to user management
            # if current_user.is_admin():
            #     return redirect(url_for('auth.manage_users'))

            # Log in the newly created user
            user = User.query.filter_by(email=email).first()
            if user:
                login_user(user)

            # Redirect to choose plan page after successful signup
            return redirect(url_for('auth.choose_plan'))
        else:
            flash(message, 'danger')

    return render_template('auth/signup.html')


# @auth_bp.route('/logout')
# @login_required
# def logout():
#     """Handle user logout"""
#     success, message = AuthController.logout()

#     if success:
#         flash(message, 'success')
#     else:
#         flash(message, 'danger')

#     return redirect(url_for('auth.login'))

@auth_bp.route('/manage_users')
@login_required
@role_required('admin', 'developer')
def manage_users():
    """Manage users - accessible to admins and developers"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # Get all users for admin/developer section WITH subscription data
    all_users = User.query.options(joinedload(User.subscription)).all()

    # Get regular users with pagination WITH subscription data
    regular_users_query = User.query.options(joinedload(User.subscription)).filter(
        User.role.in_(['user', 'student', 'tester'])
    )

    # Apply search if provided
    search = request.args.get('search', '').strip()
    if search:
        regular_users_query = regular_users_query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.company.ilike(f'%{search}%')
            )
        )

    # Apply pagination
    regular_users_pagination = regular_users_query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    regular_users = regular_users_pagination.items

    return render_template('auth/manage_users.html',
                         users=all_users,
                         regular_users=regular_users,
                         page=page,
                         per_page=per_page,
                         total_pages=regular_users_pagination.pages,
                         total_users=regular_users_pagination.total)

@auth_bp.route('/api/auth/regular_users')
@login_required
@role_required('admin', 'developer')
def api_regular_users():
    """API endpoint for paginated regular users"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '').strip()

        # Query regular users WITH subscription data
        query = User.query.options(joinedload(User.subscription)).filter(
            User.role.in_(['user', 'student', 'tester'])
        )

        # Apply search if provided
        if search:
            search_term = f"%{search}%"
            current_app.logger.debug(f"Applying search filter with term: {search_term}")

            query = query.filter(
                db.or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.company.ilike(search_term),
                    User.role.ilike(search_term)
                )
            )

            # Log the SQL query for debugging
            current_app.logger.debug(f"SQL Query: {query}")

        # Order by creation date, newest first
        query = query.order_by(User.created_at.desc())

        # Apply pagination
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        users = pagination.items

        response_data = {
            'users': [{
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'company': user.company,
                'role': user.role,
                'created_at': user.created_at.strftime('%Y-%m-%d'),
                'subscription': {
                    'plan_name': user.subscription.plan_name if user.subscription else 'Free',
                    'tier': user.tier,
                    'has_subscription': user.subscription is not None and user.subscription.plan_name != 'Free'
                } if user.subscription else {
                    'plan_name': 'Free',
                    'tier': user.tier,
                    'has_subscription': False
                }
            } for user in users],
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages,
            'total_users': pagination.total
        }

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error in api_regular_users: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An error occurred while fetching users',
            'message': str(e)
        }), 500

@auth_bp.route('/update_user_role', methods=['POST'])
@login_required
@role_required('admin', 'developer')
def update_user_role():
    """Update user role - only accessible to admins"""
    user_id = request.form.get('user_id')
    role = request.form.get('role')

    if not user_id or not role:
        flash('Missing required fields', 'danger')
        return redirect(url_for('auth.manage_users'))

    # Validate role
    valid_roles = ['admin', 'developer', 'user', 'student', 'tester']
    if role not in valid_roles:
        flash(f'Invalid role. Must be one of: {", ".join(valid_roles)}', 'danger')
        return redirect(url_for('auth.manage_users'))

    try:
        user = User.query.get(user_id)
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('auth.manage_users'))

        user.role = role
        db.session.commit()
        flash(f'Role for {user.username} updated to {role}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating role: {str(e)}', 'danger')

    return redirect(url_for('auth.manage_users'))

@auth_bp.route('/api/auth/check_user_data/<string:user_id>', methods=['GET'])
@login_required
@role_required('admin', 'developer')
def check_user_data(user_id):
    """Check what data a user has before deletion"""
    try:
        # Get the user
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Count associated data
        drafts_count = db.session.query(EditLeadDraft).filter_by(user_id=user_id).count()
        user_lead_drafts_count = db.session.query(UserLeadDraft).filter_by(user_id=user_id).count()
        audit_logs_count = db.session.query(AuditLog).filter_by(user_id=user_id).count()
        subscription_count = db.session.query(UserSubscription).filter_by(user_id=user_id).count()

        has_data = drafts_count > 0 or user_lead_drafts_count > 0 or audit_logs_count > 0 or subscription_count > 0

        return jsonify({
            'has_data': has_data,
            'drafts_count': drafts_count,
            'user_lead_drafts_count': user_lead_drafts_count,
            'leads_count': 0,  # Leads are not user-specific
            'audit_logs_count': audit_logs_count,
            'subscription_count': subscription_count
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error checking user data for {user_id}: {str(e)}")
        return jsonify({'error': 'An error occurred while checking user data'}), 500

@auth_bp.route('/api/auth/delete_user/<string:user_id>', methods=['DELETE'])
@login_required
@role_required('admin', 'developer')
def delete_user(user_id):
    """Delete a user and all their associated data"""
    try:
        # Get the user to delete
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Don't allow deleting yourself
        if user.user_id == current_user.user_id:
            return jsonify({'error': 'Cannot delete your own account'}), 403

        username = user.username

        # Delete all associated data in the correct order to avoid foreign key violations
        try:
            # Delete drafts first (these are user-specific)
            drafts_deleted = EditLeadDraft.query.filter_by(user_id=user_id).delete()

            # Delete user lead drafts (these are user-specific)
            user_lead_drafts_deleted = UserLeadDraft.query.filter_by(user_id=user_id).delete()

            # Delete audit logs (these are user-specific)
            audit_logs_deleted = AuditLog.query.filter_by(user_id=user_id).delete()

            # Delete user subscription using delete() method
            subscription_deleted = UserSubscription.query.filter_by(user_id=user_id).delete()

            # Finally delete the user
            db.session.delete(user)

            # Commit all changes
            db.session.commit()

            return jsonify({
                'message': f'User "{username}" and all associated data deleted successfully',
                'user_id': user_id,
                'deleted_data': {
                    'drafts': drafts_deleted,
                    'user_lead_drafts': user_lead_drafts_deleted,
                    'leads': 0,  # Leads are not user-specific
                    'audit_logs': audit_logs_deleted,
                    'subscription': subscription_deleted
                }
            }), 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error during data deletion for user {user_id}: {str(e)}")
            return jsonify({'error': f'Error deleting user data: {str(e)}'}), 500

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user {user_id}: {str(e)}")
        return jsonify({'error': 'An error occurred while deleting the user'}), 500

@auth_bp.route('/api/ping-auth', methods=["GET"])
@login_required
def ping_auth():
    return '', 204

@auth_bp.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/auth/login', methods=['POST'])
def login_api():
    """Login to get access token"""
    data = request.json

    if not data:
        return jsonify({"error": "No input data provided"}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        current_app.logger.warning(f"API login failed - Missing email or password, Domain: {request.host}")
        return jsonify({"error": "Email and password are required"}), 400

    # Use the controller for email-based login (includes sandbox checks)
    success, message = AuthController.login_by_email(email, password)

    if success:
        # Get the user for response
        user = User.query.filter_by(email=email).first()
        current_app.logger.info(f"API login successful - Email: {email}, Username: {user.username if user else 'None'}, Domain: {request.host}")
        return jsonify({
            "message": "Login successful",
            "user": user.to_dict() if user else None
        })
    else:
        current_app.logger.warning(f"API login failed - Email: {email}, Message: {message}, Domain: {request.host}")
        return jsonify({"error": message}), 401



@auth_bp.route('/api/auth/register', methods=['POST'])
def register_api():
    """Register a new user via API"""
    data = request.json

    if not data:
        return jsonify({"error": "No input data provided"}), 400

    email = data.get('email')
    password = data.get('password')
    username = data.get('username', '')
    role = data.get('role', 'user')  # Default role is user
    company = data.get('company', '') # Get company from JSON payload
    linkedin_url = data.get('linkedin_url', '') # Get linkedin_url from JSON payload

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Call the AuthController.register function
    success, message = AuthController.register(username, email, password, role, company, linkedin_url)

    if success:
        # Fetch the newly created user to log them in if needed for API flow
        user = User.query.filter_by(email=email).first()
        if user:
            login_user(user) # Log in the user with Flask-Login

        return jsonify({
            "message": "Registration successful",
            "user": user.to_dict() if user else None # Return user data if fetched
        }), 201

    else:
        # Registration failed, return the error message from the controller
        return jsonify({"error": message}), 400 # Use 400 for bad request/validation errors

@auth_bp.route('/api/auth/user', methods=['GET'])
@login_required
def get_user_info():
    """Get current user information"""
    from models.user_subscription_model import UserSubscription

    user_sub = UserSubscription.query.filter_by(user_id=current_user.user_id).first()
    is_paused = getattr(user_sub, 'is_paused', False) if user_sub else False
    pause_end_date = user_sub.pause_end_date.isoformat() if user_sub and getattr(user_sub, 'pause_end_date', None) else None

    return jsonify({
        "id": current_user.user_id,
        "email": current_user.email,
        "name": current_user.username,
        "role": current_user.role,
        "tier": current_user.tier,
        "is_paused": is_paused,
        "pause_end_date": pause_end_date
    })

@auth_bp.route('/api/auth/logout', methods=['POST'])
@login_required
def logout_api():
    """Logout user"""
    logout_user()
    return jsonify({"message": "Logout successful"})

@auth_bp.route('/api/auth/users', methods=['GET'])
@login_required
@role_required('admin', 'developer')
def api_list_users():
    """API: List all users (admin/developer only)"""
    users = User.query.all()
    return jsonify({
        "users": [
            {
                "id": u.user_id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "company": getattr(u, 'company', None)
            } for u in users
        ]
    })

@auth_bp.route('/api/auth/user/<string:user_id>', methods=['DELETE'])
@login_required
@role_required('admin', 'developer')
def api_delete_user(user_id):
    """API: Delete user by id (admin/developer only, cannot delete self)"""
    if str(user_id) == str(current_user.user_id):
        return jsonify({"error": "You cannot delete your own account"}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": f"User {user.username} has been deleted"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/api/auth/user/<string:user_id>/role', methods=['PUT'])
@login_required
@role_required('admin', 'developer')
def api_update_user_role(user_id):
    """API: Update user role (admin/developer only)"""
    data = request.json
    role = data.get('role') if data else None
    valid_roles = ['admin', 'developer', 'user', 'student', 'tester']
    if not role or role not in valid_roles:
        return jsonify({"error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    try:
        user.role = role
        db.session.commit()
        return jsonify({"message": f"Role for {user.username} updated to {role}"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/choose_plan')
@login_required
def choose_plan():
    """Render the plan selection page"""
    from models.plan_model import Plan
    from controllers.subscription_controller import SubscriptionController

    # Get all available plans
    plans = Plan.query.all()

    # Get current user subscription info
    subscription_info, status_code = SubscriptionController.get_current_user_subscription_info(current_user)

    if status_code == 200:
        current_plan = subscription_info.get('subscription', {}).get('plan_name', 'Free')
        current_credits = subscription_info.get('subscription', {}).get('credits_remaining', 0)
    else:
        current_plan = 'Free'
        current_credits = 0

    return render_template('auth/choose_plan.html',
                         plans=plans,
                         current_plan=current_plan,
                         current_credits=current_credits,
                         user_tier=current_user.tier)

@auth_bp.route('/pause_subscription')
@login_required
def pause_subscription_page():
    """Render the subscription pause page"""
    from controllers.subscription_controller import SubscriptionController

    # Get current user subscription info
    subscription_info, status_code = SubscriptionController.get_current_user_subscription_info(current_user)

    if status_code != 200:
        flash('No active subscription found.', 'info')
        return redirect(url_for('auth.choose_plan'))

    # Check if user is paused (they should be able to access this page to resume)
    is_paused = subscription_info.get('subscription', {}).get('is_paused', False)
    pause_status = subscription_info.get('subscription', {}).get('pause_status', 'none')

    # Allow access if user is paused or has an active paid tier
    if current_user.tier == 'free' and not is_paused and pause_status != 'active':
        flash('You are on the free plan and cannot pause.', 'info')
        return redirect(url_for('auth.choose_plan'))

    return render_template('auth/pause_subscription.html',
                         subscription_info=subscription_info,
                         user_tier=current_user.tier)

@auth_bp.route('/create-pause-checkout-session', methods=['POST'])
@login_required
def create_pause_checkout_session():
    """Create a Stripe checkout session for pause subscription"""
    try:
        data = request.json or {}
        pause_duration = data.get('pause_duration')

        if not pause_duration:
            return jsonify({'error': 'pause_duration is required'}), 400

        response, status_code = SubscriptionController.create_pause_checkout_session(current_user, pause_duration)
        return jsonify(response), status_code

    except Exception as e:
        current_app.logger.error(f"Error creating pause checkout session: {str(e)}")
        return jsonify({'error': 'Failed to create pause checkout session'}), 500
def create_pause_checkout_session():
    """Create a Stripe checkout session for pause subscription"""
    if not request.json:
        return jsonify({'error': 'No data provided'}), 400

    pause_duration = request.json.get('pause_duration')
    if not pause_duration:
        return jsonify({'error': 'pause_duration is required'}), 400

    # Call the controller method
    response, status_code = SubscriptionController.create_pause_checkout_session(current_user, pause_duration)
    return jsonify(response), status_code

# @auth_bp.route('/upgrade_account')
# @login_required
# def upgrade_account():
#     return render_template('auth/upgrade_account.html')


# @auth_bp.route('/cancel-subscription')
# @login_required
# def cancel_subscription():
#     """Show cancellation form"""
#     try:
#         # Get current subscription info
#         subscription_info, status_code = SubscriptionController.get_current_user_subscription_info(current_user)

#         if status_code != 200:
#             flash('Unable to retrieve subscription information.', 'error')
#             return redirect(url_for('auth.choose_plan'))

#         # Check if user can see this page (either active subscription or scheduled for cancellation)
#         is_scheduled = subscription_info.get('subscription', {}).get('is_scheduled_for_cancellation', False)
#         is_canceled = subscription_info.get('subscription', {}).get('is_canceled', False)

#         # Only show this page if user has an active subscription or one scheduled for cancellation
#         if current_user.tier == 'free' and not is_scheduled:
#             flash('You are already on the free plan.', 'info')
#             return redirect(url_for('auth.choose_plan'))

#         return render_template('auth/cancel_subscription.html', subscription_info=subscription_info)
#     except Exception as e:
#         current_app.logger.error(f"Error showing cancellation form: {str(e)}")
#         flash('An error occurred. Please try again.', 'error')
#         return redirect(url_for('auth.choose_plan'))

# def cancel_subscription_page():
#     """Render the subscription cancellation page"""
#     from controllers.subscription_controller import SubscriptionController

#     # Get current user subscription info
#     subscription_info, status_code = SubscriptionController.get_current_user_subscription_info(current_user)

#     if status_code != 200:
#         flash('No active subscription found.', 'info')
#         return redirect(url_for('auth.choose_plan'))

#     # Check if user is already on free tier
#     if current_user.tier == 'free':
#         flash('You are already on the free plan.', 'info')
#         return redirect(url_for('auth.choose_plan'))

#     return render_template('auth/cancel_subscription.html',
#                          subscription_info=subscription_info,
#                          user_tier=current_user.tier)

@auth_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create a Stripe checkout session"""
    # Call the controller method
    response, status_code = SubscriptionController.create_checkout_session(current_user)
    return jsonify(response), status_code

@auth_bp.route('/manage_subscriptions')
@login_required
@role_required('admin')
def manage_subscriptions():
    """Manage user subscriptions - Admin only"""
    users = User.query.all()
    return render_template('auth/manage_subscriptions.html', users=users)

# @auth_bp.route('/update_subscription', methods=['POST'])
# @login_required
# @role_required('admin')
# def update_subscription():
#     """Update user subscription tier - Admin only"""
#     user_id = request.form.get('user_id')
#     subscription_tier = request.form.get('subscription_tier')

#     try:
#         user = User.query.get(user_id)
#         if user:
#             user.subscription_tier = subscription_tier
#             db.session.commit()
#             flash(f'Subscription updated for {user.username} to {subscription_tier}', 'success')
#         else:
#             flash('User not found', 'danger')
#     except Exception as e:
#         db.session.rollback()
#         flash(f'Error updating subscription: {str(e)}', 'danger')

#     return redirect(url_for('auth.manage_subscriptions'))

def handle_successful_payment(session):
    try:
        user_id = session.get('client_reference_id')
        if not user_id:
            print("No user_id found in session")
            return

        user = User.query.get(user_id)
        if not user:
            print(f"User {user_id} not found")
            return

        # Get line items and extract price ID
        line_items = stripe.checkout.Session.list_line_items(session.id)
        if not line_items or not line_items.data:
            print("No line items found")
            return

        price_id = line_items.data[0].price.id

        # Map price_id to subscription tier
        price_to_tier = {
            current_app.config['STRIPE_PRICES']['gold']: 'gold',
            current_app.config['STRIPE_PRICES']['silver']: 'silver',
            current_app.config['STRIPE_PRICES']['bronze']: 'bronze'
        }

        new_tier = price_to_tier.get(price_id)
        if not new_tier:
            print(f"Invalid price_id: {price_id}")
            return

        user.subscription_tier = new_tier
        db.session.commit()
        print(f"Successfully updated user {user_id} to tier {new_tier}")

    except Exception as e:
        print(f"Error handling payment: {str(e)}")
        db.session.rollback()

@auth_bp.route('/api/auth/update_user', methods=['POST'])
@login_required
def update_user_info():
    """Update current user's username, email, and/or password"""
    data = request.json or {}
    user = current_user
    updated = False
    errors = []
    updated_fields = []

    if 'username' in data:
        user.username = data['username']
        updated = True
        updated_fields.append('username')
    if 'email' in data:
        user.email = data['email']
        updated = True
        updated_fields.append('email')
    if 'password' in data:
        try:
            user.set_password(data['password'])
            updated = True
            updated_fields.append('password')
        except Exception as e:
            errors.append(f"Password update failed: {str(e)}")
    if 'company' in data:
        user.company = data['company']
        updated = True
        updated_fields.append('company')
    if 'linkedin_url' in data:
        user.linkedin_url = data['linkedin_url']
        updated = True
        updated_fields.append('linkedin_url')

    if updated:
        try:
            try:
                current_app.logger.info(f"[User Update] User {user.user_id} attempting to update fields: {updated_fields}")
            except Exception as log_e:
                print(f"[User Update] Logging failed: {log_e}")
            db.session.commit()
            try:
                current_app.logger.info(f"[User Update] User {user.user_id} updated fields: {updated_fields} successfully.")
            except Exception as log_e:
                print(f"[User Update] Logging failed: {log_e}")
            return jsonify({
                "message": "User info updated successfully",
                "user": user.to_dict()
            }), 200
        except Exception as e:
            db.session.rollback()
            try:
                current_app.logger.error(f"[User Update] Failed to update user {user.user_id}: {str(e)}")
            except Exception as log_e:
                print(f"[User Update] Logging failed: {log_e}")
            return jsonify({"error": f"Failed to update user: {str(e)}"}), 500
    else:
        try:
            current_app.logger.warning(f"[User Update] No valid fields to update for user {user.user_id}. Errors: {errors}")
        except Exception as log_e:
            print(f"[User Update] Logging failed: {log_e}")
        return jsonify({"error": "No valid fields to update", "details": errors}), 400

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    success, message = AuthController.verify_email(token)
    current_app.logger.info(f"Email verification result: {success}, message: {message}")
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('auth.login'))

@auth_bp.route('/send-verification')
@login_required
def send_verification():
    AuthController.send_verification_email(current_user)
    flash('Verification email sent!', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            AuthController.send_password_reset_email(user)
        flash('If your email is registered, a reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        new_password = request.form.get('password')
        success, message = AuthController.reset_password(token, new_password)
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', token=token)

# API: Send verification email (for logged-in user)
@auth_bp.route('/api/auth/send-verification', methods=['POST'])
@login_required
def api_send_verification():
    try:
        AuthController.send_verification_email(current_user)
        return jsonify({"message": "Verification email sent!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API: Verify email with token
@auth_bp.route('/api/auth/verify-email/<token>', methods=['POST'])
def api_verify_email(token):
    success, message = AuthController.verify_email(token)
    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 400

# API: Forgot password (request reset email)
@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({"error": "Email is required."}), 400
    user = User.query.filter_by(email=email).first()
    if user:
        AuthController.send_password_reset_email(user)
    # Always return success to avoid leaking user existence
    return jsonify({"message": "If your email is registered, a reset link has been sent."}), 200



# API: Reset password with token
@auth_bp.route('/api/auth/reset-password/<token>', methods=['POST'])
def api_reset_password(token):
    data = request.get_json()
    new_password = data.get('password')
    if not new_password:
        return jsonify({"error": "Password is required."}), 400
    success, message = AuthController.reset_password(token, new_password)
    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 400

@auth_bp.route('/api/auth/check-student-email', methods=['POST'])
@login_required
def check_student_email():
    """
    API endpoint to check if the current user's email is a student email.
    If it is, the user's role is updated to 'student'.
    """
    from controllers.student_verification_controller import is_student_email, set_user_as_student

    current_app.logger.info(f"Student email check initiated for user {current_user.user_id} ({current_user.email}).")
    is_student = is_student_email(current_user.email)

    if not is_student:
        current_app.logger.info(f"User {current_user.user_id} ({current_user.email}) does not have a student email.")
        return jsonify({
            "is_student": False,
            "message": "The email associated with your account is not recognized as a student email."
        }), 200

    if current_user.role == 'student':
        current_app.logger.info(f"User {current_user.user_id} is already registered as a student.")
        return jsonify({
            "is_student": True,
            "message": "Your account is already registered as a student account."
        }), 200

    if set_user_as_student(current_user):
        current_app.logger.info(f"Successfully updated user {current_user.user_id} role to 'student'.")
        return jsonify({
            "is_student": True,
            "message": "Success! Your account has been updated to a student account."
        }), 200
    else:
        current_app.logger.error(f"Failed to update database for user {current_user.user_id} to set role as student.")
        return jsonify({
            "is_student": False,
            "message": "Could not update your account. Please contact support."
        }), 500

@auth_bp.route('/api/auth/user/<string:user_id>/cancel_subscription', methods=['POST'])
@login_required
@role_required('admin', 'developer')
def api_cancel_user_subscription(user_id):
    """API: Cancel user subscription (admin/developer only)"""
    data = request.json or {}
    cancellation_type = data.get('cancellation_type', 'immediate') # Default to immediate
    feedback = data.get('feedback')
    comment = data.get('comment')

    try:
        current_app.logger.info(f"[Admin Cancel] Admin {current_user.user_id} ({current_user.email}) attempting to cancel subscription for user {user_id} with cancellation_type={cancellation_type}, feedback={feedback}, comment={comment}")
        if str(user_id) == str(current_user.user_id):
            current_app.logger.warning(f"[Admin Cancel] Admin {current_user.user_id} tried to cancel their own subscription via admin route.")
            return jsonify({"error": "You cannot cancel your own account via this admin route. Please use the user-facing cancellation route."}), 400

        user = User.query.get(user_id)
        if not user:
            current_app.logger.warning(f"[Admin Cancel] User {user_id} not found for cancellation.")
            return jsonify({"error": "User not found"}), 404

        # Ensure the target user has a subscription to cancel
        from models.user_subscription_model import UserSubscription
        user_sub = UserSubscription.query.filter_by(user_id=user.user_id).first()
        if not user_sub or user.tier == 'free':
            current_app.logger.warning(f"[Admin Cancel] User {user_id} does not have an active paid subscription to cancel.")
            return jsonify({"error": f"User {user.username} does not have an active paid subscription to cancel."}), 400

        response, status_code = SubscriptionController.cancel_subscription(user, cancellation_type, feedback, comment)
        current_app.logger.info(f"[Admin Cancel] Cancellation result for user {user_id}: {response}, status {status_code}")
        return jsonify(response), status_code
    except Exception as e:
        current_app.logger.error(f"[Admin Cancel] Error canceling subscription for user {user_id} by admin {current_user.user_id}: {str(e)}")
        db.session.rollback() # Ensure rollback in case of error
        return jsonify({"error": f"Failed to cancel subscription: {str(e)}"}), 500

@auth_bp.route('/api/auth/user/<string:user_id>/reactivate_subscription', methods=['POST'])
@login_required
@role_required('admin', 'developer')
def api_reactivate_user_subscription(user_id):
    """API: Reactivate user subscription (admin/developer only)"""
    try:
        current_app.logger.info(f"[Admin Reactivation] Admin {current_user.user_id} ({current_user.email}) attempting to reactivate subscription for user {user_id}")
        if str(user_id) == str(current_user.user_id):
            current_app.logger.warning(f"[Admin Reactivation] Admin {current_user.user_id} tried to reactivate their own subscription via admin route.")
            return jsonify({"error": "You cannot reactivate your own account via this admin route."}), 400

        user = User.query.get(user_id)
        if not user:
            current_app.logger.warning(f"[Admin Reactivation] User {user_id} not found for reactivation.")
            return jsonify({"error": "User not found"}), 404

        response, status_code = SubscriptionController.reactivate_subscription(user)
        current_app.logger.info(f"[Admin Reactivation] Reactivation result for user {user_id}: {response}, status {status_code}")
        return jsonify(response), status_code
    except Exception as e:
        current_app.logger.error(f"[Admin Reactivation] Error reactivating subscription for user {user_id} by admin {current_user.user_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Failed to reactivate subscription: {str(e)}"}), 500