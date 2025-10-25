# routes/credit_routes.py

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from utils.decorators import credit_required, credit_required_v2
from controllers.subscription_controller import SubscriptionController
# Import your CreditController if you want to use it for more logic
# from controllers.credit_controller import CreditController

credit_bp = Blueprint('credit', __name__)

@credit_bp.route('/api/user/deduct_credit/<string:lead_id>', methods=['POST'])
@login_required
@credit_required_v2(cost=1)
def deduct_credit_for_lead(lead_id):
    """
    Deduct 1 credit from the current user's account for a specific lead.
    Endpoint: POST /api/user/deduct_credit/<lead_id>
    Requires: User to be logged in and have at least 1 credit.
    Returns: JSON with status, message, and lead_id.
    """
    # You can add additional logic here if you want to use lead_id for something
    response = {
        "status": "success",
        "message": f"1 credit deducted successfully for lead {lead_id}.",
        "lead_id": lead_id
    }
    return jsonify(response), 200

@credit_bp.route('/api/user/subscription_info', methods=['GET'])
@login_required
def get_user_subscription_info():
    """
    Get the current user's subscription, plan, and user info.
    Endpoint: GET /api/user/subscription_info
    Returns: JSON with user, subscription, and plan details.
    """
    data, status = SubscriptionController.get_current_user_subscription_info(current_user)
    return jsonify(data), status

@credit_bp.route('/api/plans/all', methods=['GET'])
@login_required
def get_all_plans():
    """
    Get all available plans for the Choose Plan page.
    Returns: List of plans with all relevant details.
    """
    from models.plan_model import Plan
    from sqlalchemy import func

    user_role = getattr(current_user, 'role', None)
    if user_role and user_role.lower() == 'student':
        # Only show student plans in the order list
        order = ['student monthly', 'student semester', 'student annual', 'free', 'bronze', 'silver', 'gold', 'enterprise', 'platinum', 'bronze_annual', 'silver_annual', 'gold_annual', 'platinum_annual']
        plans = Plan.query.filter(func.lower(Plan.plan_name).in_(order)).all()
        def plan_sort_key(plan):
            name = plan.plan_name.lower()
            if name in order:
                return (order.index(name), 0)
            return (len(order), name)
        plans = sorted([plan for plan in plans if plan.plan_name.lower() in order], key=plan_sort_key)
    else:
        # Only show non-student plans in the order list
        order = ['free', 'bronze', 'silver', 'gold', 'enterprise', 'platinum', 'bronze_annual', 'silver_annual', 'gold_annual', 'platinum_annual','pro call outreach']
        plans = Plan.query.filter(func.lower(Plan.plan_name).in_(order)).all()
        def plan_sort_key(plan):
            name = plan.plan_name.lower()
            if name in order:
                return (order.index(name), 0)
            return (len(order), name)
        plans = sorted([plan for plan in plans if plan.plan_name.lower() in order], key=plan_sort_key)

    plan_list = []
    for plan in plans:
        plan_list.append({
            "plan_name": plan.plan_name,
            "monthly_price": float(plan.monthly_price) if plan.monthly_price is not None else "Custom",
            "annual_price": float(plan.annual_price) if plan.annual_price is not None else "Custom",
            "monthly_lead_quota": plan.monthly_lead_quota if plan.monthly_lead_quota is not None else "Custom",
            "annual_lead_quota": plan.annual_lead_quota if plan.annual_lead_quota is not None else "Custom",
            "cost_per_lead": float(plan.cost_per_lead) if plan.cost_per_lead is not None else "~",
            "has_ai_features": plan.has_ai_features,
            "initial_credits": plan.initial_credits if plan.initial_credits is not None else "Custom",
            "credit_reset_frequency": plan.credit_reset_frequency,
            "features": plan.features_json,  # This is already a JSON/dict
            "description": plan.description
        })
    return jsonify({"plans": plan_list}), 200

@credit_bp.route('/api/plans/upgrade', methods=['GET'])
@login_required
def get_upgrade_plans():
    """
    Get available plans for upgrade, only those in the defined order list for students and non-students.
    Returns: List of plans with all relevant details.
    """
    from models.plan_model import Plan
    from sqlalchemy import func

    user_role = getattr(current_user, 'role', None)
    if user_role and user_role.lower() == 'student':
        # Only show student plans in the order list
        order = ['student monthly', 'student semester', 'student annual', 'bronze', 'silver', 'gold', 'enterprise', 'platinum', 'bronze_annual', 'silver_annual', 'gold_annual', 'platinum_annual']
        plans = Plan.query.filter(func.lower(Plan.plan_name).in_(order)).all()
        def plan_sort_key(plan):
            name = plan.plan_name.lower()
            if name in order:
                return (order.index(name), 0)
            return (len(order), name)
        plans = sorted([plan for plan in plans if plan.plan_name.lower() in order], key=plan_sort_key)
    else:
        # Only show non-student plans in the order list
        order = ['pro call outreach', 'bronze', 'silver', 'gold', 'enterprise', 'platinum', 'bronze_annual', 'silver_annual', 'gold_annual', 'platinum_annual']
        plans = Plan.query.filter(func.lower(Plan.plan_name).in_(order)).all()
        def plan_sort_key(plan):
            name = plan.plan_name.lower()
            if name in order:
                return (order.index(name), 0)
            return (len(order), name)
        plans = sorted([plan for plan in plans if plan.plan_name.lower() in order], key=plan_sort_key)

    plan_list = []
    for plan in plans:
        plan_list.append({
            "plan_name": plan.plan_name,
            "monthly_price": float(plan.monthly_price) if plan.monthly_price is not None else "Custom",
            "annual_price": float(plan.annual_price) if plan.annual_price is not None else "Custom",
            "monthly_lead_quota": plan.monthly_lead_quota if plan.monthly_lead_quota is not None else "Custom",
            "annual_lead_quota": plan.annual_lead_quota if plan.annual_lead_quota is not None else "Custom",
            "cost_per_lead": float(plan.cost_per_lead) if plan.cost_per_lead is not None else "~",
            "has_ai_features": plan.has_ai_features,
            "initial_credits": plan.initial_credits if plan.initial_credits is not None else "Custom",
            "credit_reset_frequency": plan.credit_reset_frequency,
            "features": plan.features_json,  # This is already a JSON/dict
            "description": plan.description
        })
    return jsonify({"plans": plan_list}), 200