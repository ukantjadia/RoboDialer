
from flask import Blueprint, request, jsonify, current_app
import stripe
import json
from datetime import datetime
from models.lead_model import db
from models.user_subscription_model import UserSubscription
from models.user_model import User

stripe_webhook_bp = Blueprint('stripe_webhook', __name__)

@stripe_webhook_bp.route('/api/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events for customer portal updates"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')

    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        current_app.logger.error(f"Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        current_app.logger.error(f"Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    current_app.logger.info(f"Received Stripe webhook event: {event['type']}")

    try:
        # Handle different event types
        if event['type'] == 'customer.updated':
            handle_customer_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            handle_payment_failed(event['data']['object'])
        elif event['type'] == 'payment_method.attached':
            handle_payment_method_attached(event['data']['object'])
        elif event['type'] == 'setup_intent.succeeded':
            handle_setup_intent_succeeded(event['data']['object'])
        else:
            current_app.logger.info(f"Unhandled event type: {event['type']}")

        return jsonify({'success': True}), 200

    except Exception as e:
        current_app.logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': 'Webhook processing failed'}), 500

def handle_customer_updated(customer):
    """Handle customer.updated webhook event"""
    try:
        current_app.logger.info(f"Processing customer.updated for customer {customer['id']}")
        
        # Find user by email first, then try to find by customer ID in user_subscriptions
        user = User.query.filter_by(email=customer.get('email')).first()
        
        if not user:
            # Try to find user by stripe_customer_id
            user_subscription = UserSubscription.query.filter_by(stripe_customer_id=customer['id']).first()
            if user_subscription:
                user = User.query.filter_by(user_id=user_subscription.user_id).first()
        
        if not user:
            current_app.logger.warning(f"User not found for customer {customer['id']}")
            return

        user_subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
        if not user_subscription:
            current_app.logger.warning(f"User subscription not found for user {user.user_id}")
            return

        current_app.logger.info(f"Updating customer data from webhook: {customer}")

        # Update customer portal fields
        user_subscription.stripe_customer_id = customer['id']
        user_subscription.phone_number = customer.get('phone')
        user_subscription.preferred_locales = ','.join(customer.get('preferred_locales', [])) if customer.get('preferred_locales') else None
        user_subscription.currency = customer.get('currency')
        user_subscription.customer_portal_last_updated = datetime.utcnow()

        # Update billing address if available
        address = customer.get('address')
        if address:
            user_subscription.billing_address_line1 = address.get('line1')
            user_subscription.billing_address_line2 = address.get('line2')
            user_subscription.billing_address_city = address.get('city')
            user_subscription.billing_address_state = address.get('state')
            user_subscription.billing_address_postal_code = address.get('postal_code')
            user_subscription.billing_address_country = address.get('country')

        # Update invoice settings
        invoice_settings = customer.get('invoice_settings', {})
        if invoice_settings:
            default_payment_method = invoice_settings.get('default_payment_method')
            user_subscription.invoice_settings_default_payment_method = default_payment_method

        # Set invoice email enabled
        user_subscription.invoice_email_enabled = True

        db.session.commit()
        current_app.logger.info(f"Successfully updated customer data for user {user.user_id} via webhook")

    except Exception as e:
        current_app.logger.error(f"Error in handle_customer_updated: {str(e)}")
        db.session.rollback()
        raise

def handle_subscription_updated(subscription):
    """Handle customer.subscription.updated webhook event"""
    try:
        current_app.logger.info(f"Processing subscription.updated for subscription {subscription['id']}")
        
        customer_id = subscription['customer']
        
        # Set Stripe API key
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
        customer = stripe.Customer.retrieve(customer_id)
        
        # Find user by email or customer ID
        user = User.query.filter_by(email=customer.email).first()
        if not user:
            user_subscription = UserSubscription.query.filter_by(stripe_customer_id=customer_id).first()
            if user_subscription:
                user = User.query.filter_by(user_id=user_subscription.user_id).first()
        
        if not user:
            current_app.logger.warning(f"User not found for customer {customer_id}")
            return

        user_subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
        if not user_subscription:
            current_app.logger.warning(f"User subscription not found for user {user.user_id}")
            return

        current_app.logger.info(f"Updating subscription data from webhook: {subscription}")

        # Update subscription status and period
        user_subscription.subscription_status = subscription['status']
        user_subscription.current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
        user_subscription.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
        user_subscription.cancel_at_period_end = subscription.get('cancel_at_period_end', False)
        user_subscription.customer_portal_last_updated = datetime.utcnow()

        # Update cancellation status
        if subscription['status'] == 'canceled':
            user_subscription.is_canceled = True
            user_subscription.canceled_at = datetime.utcnow()
        elif subscription['status'] == 'active' and user_subscription.is_canceled:
            user_subscription.is_canceled = False
            user_subscription.canceled_at = None

        # Update payment method information
        default_payment_method = subscription.get('default_payment_method')
        if default_payment_method:
            try:
                payment_method = stripe.PaymentMethod.retrieve(default_payment_method)
                user_subscription.payment_method_id = payment_method.id
                user_subscription.payment_method_type = payment_method.type
                
                if payment_method.type == 'card' and hasattr(payment_method, 'card'):
                    card = payment_method.card
                    user_subscription.payment_method_last4 = card.last4
                    user_subscription.payment_method_brand = card.brand
            except Exception as pm_error:
                current_app.logger.error(f"Error retrieving payment method: {pm_error}")

        # Update customer ID if not set
        if not user_subscription.stripe_customer_id:
            user_subscription.stripe_customer_id = customer_id

        db.session.commit()
        current_app.logger.info(f"Successfully updated subscription data for user {user.user_id} via webhook")

    except Exception as e:
        current_app.logger.error(f"Error in handle_subscription_updated: {str(e)}")
        db.session.rollback()
        raise

def handle_subscription_deleted(subscription):
    """Handle customer.subscription.deleted webhook event"""
    try:
        current_app.logger.info(f"Processing subscription.deleted for subscription {subscription['id']}")
        
        customer_id = subscription['customer']
        customer = stripe.Customer.retrieve(customer_id)
        
        user = User.query.filter_by(email=customer.email).first()
        if not user:
            current_app.logger.warning(f"User not found for customer {customer_id}")
            return

        user_subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
        if not user_subscription:
            current_app.logger.warning(f"User subscription not found for user {user.user_id}")
            return

        # Mark subscription as canceled
        user_subscription.is_canceled = True
        user_subscription.canceled_at = datetime.utcnow()
        user_subscription.subscription_status = 'canceled'
        user_subscription.customer_portal_last_updated = datetime.utcnow()

        db.session.commit()
        current_app.logger.info(f"Marked subscription as canceled for user {user.user_id}")

    except Exception as e:
        current_app.logger.error(f"Error in handle_subscription_deleted: {str(e)}")
        db.session.rollback()

def handle_payment_succeeded(invoice):
    """Handle invoice.payment_succeeded webhook event"""
    try:
        current_app.logger.info(f"Processing payment_succeeded for invoice {invoice['id']}")
        
        customer_id = invoice['customer']
        customer = stripe.Customer.retrieve(customer_id)
        
        user = User.query.filter_by(email=customer.email).first()
        if not user:
            current_app.logger.warning(f"User not found for customer {customer_id}")
            return

        user_subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
        if not user_subscription:
            current_app.logger.warning(f"User subscription not found for user {user.user_id}")
            return

        # Update payment status and last updated timestamp
        user_subscription.customer_portal_last_updated = datetime.utcnow()
        
        # If subscription was canceled due to payment failure, reactivate it
        if user_subscription.is_canceled and user_subscription.subscription_status in ['past_due', 'unpaid']:
            user_subscription.is_canceled = False
            user_subscription.canceled_at = None
            user_subscription.subscription_status = 'active'

        db.session.commit()
        current_app.logger.info(f"Updated payment status for user {user.user_id}")

    except Exception as e:
        current_app.logger.error(f"Error in handle_payment_succeeded: {str(e)}")
        db.session.rollback()

def handle_payment_failed(invoice):
    """Handle invoice.payment_failed webhook event"""
    try:
        current_app.logger.info(f"Processing payment_failed for invoice {invoice['id']}")
        
        customer_id = invoice['customer']
        customer = stripe.Customer.retrieve(customer_id)
        
        user = User.query.filter_by(email=customer.email).first()
        if not user:
            current_app.logger.warning(f"User not found for customer {customer_id}")
            return

        user_subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
        if not user_subscription:
            current_app.logger.warning(f"User subscription not found for user {user.user_id}")
            return

        # Update payment failure status
        user_subscription.subscription_status = 'past_due'
        user_subscription.customer_portal_last_updated = datetime.utcnow()

        db.session.commit()
        current_app.logger.info(f"Updated payment failure status for user {user.user_id}")

    except Exception as e:
        current_app.logger.error(f"Error in handle_payment_failed: {str(e)}")
        db.session.rollback()

def handle_payment_method_attached(payment_method):
    """Handle payment_method.attached webhook event"""
    try:
        current_app.logger.info(f"Processing payment_method.attached for payment method {payment_method['id']}")
        
        customer_id = payment_method['customer']
        customer = stripe.Customer.retrieve(customer_id)
        
        user = User.query.filter_by(email=customer.email).first()
        if not user:
            current_app.logger.warning(f"User not found for customer {customer_id}")
            return

        user_subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
        if not user_subscription:
            current_app.logger.warning(f"User subscription not found for user {user.user_id}")
            return

        # Update payment method information
        user_subscription.payment_method_id = payment_method['id']
        user_subscription.payment_method_type = payment_method['type']
        user_subscription.customer_portal_last_updated = datetime.utcnow()
        
        if payment_method['type'] == 'card':
            card = payment_method['card']
            user_subscription.payment_method_last4 = card['last4']
            user_subscription.payment_method_brand = card['brand']

        db.session.commit()
        current_app.logger.info(f"Updated payment method for user {user.user_id}")

    except Exception as e:
        current_app.logger.error(f"Error in handle_payment_method_attached: {str(e)}")
        db.session.rollback()

def handle_setup_intent_succeeded(setup_intent):
    """Handle setup_intent.succeeded webhook event"""
    try:
        current_app.logger.info(f"Processing setup_intent.succeeded for setup intent {setup_intent['id']}")
        
        customer_id = setup_intent['customer']
        if not customer_id:
            return
            
        customer = stripe.Customer.retrieve(customer_id)
        
        user = User.query.filter_by(email=customer.email).first()
        if not user:
            current_app.logger.warning(f"User not found for customer {customer_id}")
            return

        user_subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
        if not user_subscription:
            current_app.logger.warning(f"User subscription not found for user {user.user_id}")
            return

        # Update last updated timestamp
        user_subscription.customer_portal_last_updated = datetime.utcnow()

        db.session.commit()
        current_app.logger.info(f"Updated setup intent status for user {user.user_id}")

    except Exception as e:
        current_app.logger.error(f"Error in handle_setup_intent_succeeded: {str(e)}")
        db.session.rollback()
