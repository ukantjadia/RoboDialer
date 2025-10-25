from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models.user_subscription_model import UserSubscription
from models.lead_model import db
from controllers.subscription_controller import SubscriptionController
import logging
import stripe

subscription_bp = Blueprint('subscription', __name__)

# @subscription_bp.route('/api/subscription/decrement_credits', methods=['POST'])
# # @login_required
# def decrement_credits():
#     """
#     Decrease credits_remaining for the currently logged in user.
#     Body: { "amount": 1 }
#     """
#     data = request.json or {}
#     amount = int(data.get('amount', 1))
#     if amount < 1:
#         return jsonify({"error": "Amount must be >= 1"}), 400

#     user_sub = UserSubscription.query.filter_by(user_id=str(current_user.user_id)).first()
#     if not user_sub:
#         return jsonify({"error": "User subscription not found"}), 404

#     if user_sub.credits_remaining < amount:
#         return jsonify({"error": "Not enough credits"}), 400

#     user_sub.credits_remaining -= amount
#     db.session.commit()
#     return jsonify({
#         "message": f"Credits decreased by {amount}",
#         "credits_remaining": user_sub.credits_remaining
#     })

@subscription_bp.route('/api/subscription/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create a Stripe checkout session for subscription"""
    try:
        response, status_code = SubscriptionController.create_checkout_session(current_user)
        return jsonify(response), status_code
    except Exception as e:
        current_app.logger.error(f"Error in create_checkout_session route: {str(e)}")
        return jsonify({'error': 'Failed to create checkout session'}), 500

@subscription_bp.route('/api/subscription/info', methods=['GET'])
@login_required
def get_subscription_info():
    """Get current user subscription information"""
    try:
        response, status_code = SubscriptionController.get_current_user_subscription_info(current_user)
        return jsonify(response), status_code
    except Exception as e:
        current_app.logger.error(f"Error in get_subscription_info route: {str(e)}")
        return jsonify({'error': 'Failed to get subscription info'}), 500

@subscription_bp.route('/api/subscription/credits', methods=['GET'])
@login_required
def get_credits():
    user_sub = UserSubscription.query.filter_by(user_id=str(current_user.user_id)).first()
    if not user_sub:
        return jsonify({"credits_remaining": 0})
    return jsonify({"credits_remaining": user_sub.credits_remaining})

# @subscription_bp.route('/api/subscription/cancel', methods=['POST'])
# @login_required
# def cancel_subscription():
#     """Cancel user subscription
#     NOTE: This route is commented out as cancellation is now handled through Stripe Customer Portal
#     """
#     try:
#         data = request.json or {}
#         cancellation_type = data.get('type', 'immediate')  # 'immediate' or 'period_end'
#         feedback = data.get('feedback')  # Optional feedback reason
#         comment = data.get('comment')    # Optional comment

#         current_app.logger.info(f"[Cancel API] User {current_user.user_id} requesting {cancellation_type} cancellation")

#         if cancellation_type not in ['immediate', 'period_end']:
#             return jsonify({'error': 'Invalid cancellation type. Use "immediate" or "period_end"'}), 400

#         response, status_code = SubscriptionController.cancel_subscription(
#             current_user,
#             cancellation_type=cancellation_type,
#             feedback=feedback,
#             comment=comment
#         )

#         current_app.logger.info(f"[Cancel API] Response for user {current_user.user_id}: status={status_code}, response={response}")
#         return jsonify(response), status_code

#     except Exception as e:
#         current_app.logger.error(f"[Cancel API] Error canceling subscription for user {current_user.user_id}: {str(e)}")
#         return jsonify({'error': 'Internal server error'}), 500

# @subscription_bp.route('/api/subscription/reactivate', methods=['POST'])
# @login_required
# def reactivate_subscription():
#     """Reactivate canceled subscription
#     NOTE: This route is commented out as reactivation is now handled through Stripe Customer Portal
#     """
#     try:
#         current_app.logger.info(f"[Reactivate API] User {current_user.user_id} requesting subscription reactivation")

#         response, status_code = SubscriptionController.reactivate_subscription(current_user)

#         current_app.logger.info(f"[Reactivate API] Response for user {current_user.user_id}: status={status_code}, response={response}")
#         return jsonify(response), status_code

#     except Exception as e:
#         current_app.logger.error(f"[Reactivate API] Error reactivating subscription for user {current_user.user_id}: {str(e)}")
#         return jsonify({'error': 'Internal server error'}), 500

@subscription_bp.route('/api/subscription/pause', methods=['POST'])
@login_required
def pause_subscription():
    """Pause user subscription"""
    try:
        data = request.json or {}
        pause_duration = data.get('pause_duration')

        current_app.logger.info(
            f"[Pause API] User {current_user.user_id} requesting pause with duration: {pause_duration}"
        )

        if not pause_duration:
            return jsonify({'error': 'pause_duration is required'}), 400

        response, status_code = SubscriptionController.create_pause_checkout_session(
            current_user, pause_duration)
        return jsonify(response), status_code

    except Exception as e:
        current_app.logger.error(
            f"[Pause API] Error pausing subscription for user {current_user.user_id}: {str(e)}"
        )
        return jsonify({'error': 'Internal server error'}), 500


@subscription_bp.route('/api/subscription/resume', methods=['POST'])
@login_required
def resume_subscription():
    """Resume paused subscription early"""
    try:
        current_app.logger.info(
            f"[Resume API] User {current_user.user_id} requesting early resume"
        )

        response, status_code = SubscriptionController.resume_subscription_early(
            current_user)
        return jsonify(response), status_code

    except Exception as e:
        current_app.logger.error(
            f"[Resume API] Error resuming subscription for user {current_user.user_id}: {str(e)}"
        )
        return jsonify({'error': 'Internal server error'}), 500
    
@subscription_bp.route('/webhook', methods=['POST'])
def subscription_webhook():
    """Handle Stripe webhook events for subscriptions"""
    current_app.logger.info(f"[Webhook] Webhook received")

    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('stripe-signature')

    if not sig_header:
        current_app.logger.error("[Webhook] Missing stripe-signature header")
        return jsonify({'error': 'Missing stripe-signature header'}), 400

    # Log the webhook receipt
    current_app.logger.info(
        "[Webhook] Stripe webhook received. Processing event in handler.")

    try:
        response, status_code = SubscriptionController.handle_stripe_webhook(
            payload, sig_header)
        return response, status_code
    except Exception as e:
        current_app.logger.error(
            f"[Webhook] Error processing webhook: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500

# @subscription_bp.route('/api/subscription/test-cancel', methods=['GET'])
# @login_required
# def test_cancel_access():
#     """Test endpoint to check if cancellation is possible"""
#     try:
#         from models.user_subscription_model import UserSubscription
#         user_sub = UserSubscription.query.filter_by(user_id=current_user.user_id).first()

#         return jsonify({
#             'user_id': str(current_user.user_id),
#             'email': current_user.email,
#             'tier': current_user.tier,
#             'has_subscription': bool(user_sub),
#             'subscription_details': {
#                 'plan_name': user_sub.plan_name if user_sub else None,
#                 'payment_frequency': user_sub.payment_frequency if user_sub else None,
#                 'credits_remaining': user_sub.credits_remaining if user_sub else None
#             } if user_sub else None
#         }), 200
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500