from functools import wraps
from flask import flash, redirect, url_for, jsonify, request
from flask_login import current_user
import logging
# Assuming db is accessible from the models package, specifically where Lead model is defined
from models.lead_model import db # Import db
from models.user_subscription_model import UserSubscription # Import UserSubscription
from models.workspace_member_model import WorkspaceMember
from models.credits_log_model import CreditsLog

def role_required(*roles):
    """
    Decorator to restrict access to specific roles.
    Usage: @role_required('admin') or @role_required('admin', 'developer')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'danger')
                return redirect(url_for('auth.login'))

            if current_user.role not in roles:
                flash(f'Access denied. Required role: {", ".join(roles)}', 'danger')
                return redirect(url_for('main.index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def credit_required(cost=1):
    """Decorator to check if the user has enough credits and deducts them on success, but skips check for admin and developer roles."""
    skip_roles = ['admin', 'developer']
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'status': 'error', 'message': 'Authentication required.'}), 401

            # If the user's role is in skip_roles, skip credit check
            if hasattr(current_user, 'role') and current_user.role in skip_roles:
                return f(*args, **kwargs)

            user_id = current_user.get_id()
            
            # Check if user is part of a company
            if hasattr(current_user, 'company_id') and current_user.company_id:
                # Use company credits
                from controllers.company_controller import CompanyController
                success, result = CompanyController.use_company_credits(user_id, cost)
                if not success:
                    return jsonify({'status': 'error', 'message': result}), 402
                
                # Execute the original function
                response = f(*args, **kwargs)
                logging.info(f"Successfully used {cost} company credits for user {user_id}")
                return response
            else:
                # Use individual credits
                user_subscription = UserSubscription.query.filter_by(user_id=user_id).first()

                # Ensure user has a subscription and enough credits
                if not user_subscription:
                     logging.error(f"User {user_id} attempting to access @credit_required route without a subscription.")
                     return jsonify({'status': 'error', 'message': 'User subscription not found.'}), 500

                if user_subscription.credits_remaining < cost:
                     return jsonify({'status': 'error', 'message': 'Insufficient credits.'}), 402

                # Execute the original function
                response = f(*args, **kwargs)

                # If the function executed successfully (didn't raise an exception), deduct credits
                try:
                    user_subscription.credits_remaining -= cost
                    db.session.commit()
                    logging.info(f"Successfully deducted {cost} credits for user {user_id}. Remaining credits: {user_subscription.credits_remaining}")
                except Exception as e:
                    db.session.rollback()
                    logging.error(f"Failed to deduct credits for user {user_id}: {str(e)}")
                    # Decide how to handle deduction failure - currently logs but doesn't stop response

                return response
        return decorated_function
    return decorator

def credit_required_v2(cost:int=1, type:str=None):
    """
    Decorator that checks and deducts credits using the new priority system
    (Workspace -> Personal), while still skipping checks for admins/developers
    and handling company credits separately.
    Args:
        cost: The credits cost of the used service. 
        type: The name of the used service. Example: 'email_gen', 'apollo_scraper', 'web_scraper', etc.
    """
    skip_roles = ['admin', 'developer']
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'status': 'error', 'message': 'Authentication required.'}), 401

            if hasattr(current_user, 'role') and current_user.role in skip_roles:
                return f(*args, **kwargs)
            
            # Check if the request has a JSON body and get the 'type' from it.
            # If no type was in the body, fall back to the decorator's argument.
            final_service_type = type
            if request.is_json and request.get_json():
                final_service_type = request.get_json().get('type')


            if hasattr(current_user, 'company_id') and current_user.company_id:
                from controllers.company_controller import CompanyController
                success, result = CompanyController.use_company_credits(current_user.user_id, cost, final_service_type)
                if not success:
                    return jsonify({'status': 'error', 'message': result}), 402
                logging.info(f"Successfully used {cost} company credits for user {current_user.user_id}")
                return f(*args, **kwargs)
            else:
                try:
                    success, message = _deduct_credits_with_priority(current_user, cost, final_service_type)
                    
                    if not success:
                        return jsonify({'status': 'error', 'message': message}), 402
                    
                    return f(*args, **kwargs)

                except Exception as e:
                    db.session.rollback()
                    logging.error(f"A critical error occurred during credit deduction for user {current_user.user_id}: {str(e)}")
                    return jsonify({'status': 'error', 'message': 'An internal error occurred while processing credits.'}), 500
        
        return decorated_function
    return decorator

def _deduct_credits_with_priority(user, cost: int, service_type: str = None):
    """
    Deducts credits with a priority system: Workspace first, then Personal.
    
    If the user is in multiple workspaces, it uses the one with the most
    available credits.

    Returns: (bool, str) -> (success, message)
    """
    # Priority 1: Try to use Workspace Credits
    
    # Find all active memberships for the user
    memberships = WorkspaceMember.query.filter_by(
        user_id=user.user_id, 
        is_active=True
    ).all()
    
    # Filter for memberships where the user has enough allocated credits
    sufficient_memberships = [
        m for m in memberships if m.get_remaining_credits() >= cost
    ]
    
    if sufficient_memberships:
        best_membership = sorted(
            sufficient_memberships, 
            key=lambda m: m.get_remaining_credits(), 
            reverse=True
        )[0]
        
        best_membership.credits_used += cost
        
        # Log the usage for auditing
        CreditsLog.log_usage(
            team_id=best_membership.workspace_id,
            user_id=user.user_id,
            amount=cost,
            reason=f"Used {cost} credits for {service_type or 'a service'}.",
            reference_type=service_type,
        )
        db.session.commit()
        logging.info(f"Successfully deducted {cost} credits from workspace {best_membership.workspace_id} for user {user.user_id}.")
        return (True, "Deducted from workspace credits.")

    # Priority 2: Fallback to Personal Subscription Credits
    
    user_subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()

    if user_subscription and (
        'platinum' in str(user.tier).lower() or 
        'platinum' in str(user_subscription.plan_name).lower()
    ):
        # If they are Platinum, skip the deduction and return success immediately.
        logging.info(f"Skipping credit deduction for Platinum user {user.user_id}.")
        return (True, "Platinum plan, credits not required.")

    if user_subscription and user_subscription.credits_remaining >= cost:
        user_subscription.credits_remaining -= cost
        CreditsLog.log_usage(
            team_id=None,
            user_id=user.user_id,
            amount=cost,
            reason=f"Used {cost} personal credits for {service_type or 'a service'}.",
            reference_type=service_type 
        )
        db.session.commit()
        logging.info(f"Successfully deducted {cost} credits from personal subscription for user {user.user_id}.")
        return (True, "Deducted from personal credits.")

    
    return (False, "Insufficient credits.")

def filter_lead_data_by_plan():
    """
    Decorator to filter and mask lead data based on the user's subscription plan.
    Assumes the decorated function returns a list of Lead model instances.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Ensure user and subscription are available
            if not current_user.is_authenticated:
                 return jsonify({'status': 'error', 'message': 'Authentication required.'}), 401

            user_id = current_user.get_id()
            user_subscription = UserSubscription.query.filter_by(user_id=user_id).first()

            if not user_subscription:
                logging.error(f"filter_lead_data_by_plan decorator used for user {user_id} without a valid user subscription.")
                return jsonify({'status': 'error', 'message': 'User subscription not found.'}), 500 # Or handle as appropriate

            # Execute the original function to get leads (expected to return a list of Lead model instances)
            leads = f(*args, **kwargs)

            user_plan_name = user_subscription.plan_name

            processed_leads = []
            for lead in leads:
                # Define fields for different plans
                if user_plan_name == 'Free':
                    # Fields for Free plan (limited and masked contact info)
                    allowed_fields = [
                        'lead_id', 'company', 'industry', 'street', 'city', 'state',
                        'bbb_rating', 'phone', 'website', 'owner_email'
                    ]

                    # Mask sensitive data
                    masked_phone = '********' + (lead.phone[-4:] if lead.phone and len(lead.phone) > 4 else lead.phone or '')
                    # Mask email: show first char, then ***, then @domain if available
                    masked_email_parts = (lead.owner_email or '').split('@')
                    if len(masked_email_parts) > 1:
                        masked_email = f"{masked_email_parts[0][0] if masked_email_parts[0] else ''}***@{masked_email_parts[1]}"
                    else:
                        masked_email = f"{masked_email_parts[0][0] if masked_email_parts[0] else ''}***@"

                    processed_lead = {}
                    for field in allowed_fields:
                        if field == 'phone':
                            processed_lead[field] = masked_phone
                        elif field == 'owner_email':
                            processed_lead[field] = masked_email
                        elif hasattr(lead, field):
                             # Use getattr to get the value from the Lead object
                             processed_lead[field] = getattr(lead, field)
                        # Fields not present on the model will be skipped

                    processed_leads.append(processed_lead)

                else:
                    # Fields for other plans (use to_dict for full representation)
                    # If you need a specific set of columns for paid plans, define another list here
                    processed_leads.append(lead.to_dict()) # Assuming Lead model has a to_dict method

            return jsonify(processed_leads), 200
        return decorated_function
    return decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def developer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (current_user.role != 'developer' and not current_user.is_admin()):
            return jsonify({'error': 'Developer or admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function