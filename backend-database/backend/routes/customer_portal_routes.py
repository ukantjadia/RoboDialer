from flask import Blueprint, request, jsonify, current_app, redirect, render_template, flash, url_for
from flask_login import login_required, current_user
import stripe
from models.user_model import User
from models.user_subscription_model import UserSubscription
from models.lead_model import db
from controllers.subscription_controller import SubscriptionController
from datetime import datetime

customer_portal_bp = Blueprint('customer_portal', __name__)

def sync_customer_data(customer_id, user_id):
    """Sync customer data from Stripe to local database"""
    try:
        current_app.logger.info(f"Syncing customer data for customer {customer_id}")

        # Set Stripe API key
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

        # Retrieve customer from Stripe with expanded data
        customer = stripe.Customer.retrieve(
            customer_id,
            expand=['invoice_settings.default_payment_method']
        )

        # Get user subscription
        user_subscription = UserSubscription.query.filter_by(user_id=user_id).first()
        if not user_subscription:
            current_app.logger.warning(f"User subscription not found for user {user_id}")
            return False

        current_app.logger.info(f"Customer data: {customer}")

        # Update customer data
        user_subscription.stripe_customer_id = customer.id
        user_subscription.phone_number = customer.get('phone')
        user_subscription.preferred_locales = ','.join(customer.get('preferred_locales', []))
        user_subscription.currency = customer.get('currency')
        user_subscription.customer_portal_last_updated = datetime.utcnow()

        # Update billing address
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
            default_pm = invoice_settings.get('default_payment_method')
            if default_pm:
                user_subscription.invoice_settings_default_payment_method = default_pm.id if hasattr(default_pm, 'id') else str(default_pm)

        # Get all subscriptions for this customer (active, past_due, etc.)
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            limit=10,
            expand=['data.default_payment_method']
        )

        # Find the most recent active or past_due subscription
        active_subscription = None
        for sub in subscriptions.data:
            if sub.status in ['active', 'past_due', 'trialing']:
                active_subscription = sub
                break

        if active_subscription:
            current_app.logger.info(f"Found active subscription: {active_subscription.id}")
            user_subscription.subscription_status = active_subscription.status
            start_ts = active_subscription.get('current_period_start')
            end_ts = active_subscription.get('current_period_end')

            user_subscription.current_period_start = datetime.fromtimestamp(start_ts) if start_ts else None
            user_subscription.current_period_end = datetime.fromtimestamp(end_ts) if end_ts else None
            user_subscription.cancel_at_period_end = active_subscription.get('cancel_at_period_end', False)

            # Update payment method from subscription
            default_payment_method = active_subscription.get('default_payment_method')
            if default_payment_method:
                if hasattr(default_payment_method, 'id'):
                    # Already expanded
                    payment_method = default_payment_method
                else:
                    # Need to retrieve
                    payment_method = stripe.PaymentMethod.retrieve(default_payment_method)

                user_subscription.payment_method_id = payment_method.id
                user_subscription.payment_method_type = payment_method.type

                if payment_method.type == 'card' and hasattr(payment_method, 'card'):
                    card = payment_method.card
                    user_subscription.payment_method_last4 = card.last4
                    user_subscription.payment_method_brand = card.brand
        else:
            # No active subscription, try to get payment methods directly from customer
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type='card',
                limit=1
            )

            if payment_methods.data:
                payment_method = payment_methods.data[0]
                user_subscription.payment_method_id = payment_method.id
                user_subscription.payment_method_type = payment_method.type

                if payment_method.type == 'card':
                    card = payment_method.card
                    user_subscription.payment_method_last4 = card.last4
                    user_subscription.payment_method_brand = card.brand

        # Set invoice email enabled (default to True)
        user_subscription.invoice_email_enabled = True

        db.session.commit()
        current_app.logger.info(f"Successfully synced customer data for user {user_id}")
        return True

    except Exception as e:
        current_app.logger.error(f"Error syncing customer data: {str(e)}")
        db.session.rollback()
        return False


@customer_portal_bp.route('/api/create-customer-portal-session', methods=['POST'])
@login_required
def create_customer_portal_session():
    """Create a Stripe customer portal session for the authenticated user"""
    try:
        current_app.logger.info(
            f"[Customer Portal] Creating portal session for user {current_user.user_id}"
        )

        # Set Stripe API key
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

        # Get return URL from request or use default
        data = request.json or {}
        return_url = data.get('return_url',
                              'https://app.saasquatchleads.com/subscription')

        # Find or create Stripe customer
        customer = None

        # Try to find existing customer by email
        try:
            customers = stripe.Customer.list(email=current_user.email, limit=5)
            if customers.data:
                customer = customers.data[0]
                current_app.logger.info(
                    f"[Customer Portal] Found existing Stripe customer {customer.id}"
                )
        except Exception as e:
            current_app.logger.warning(
                f"[Customer Portal] Error searching for customer: {str(e)}")

        # Create customer if not found
        if not customer:
            try:
                customer = stripe.Customer.create(
                    email=current_user.email,
                    name=current_user.username,
                    metadata={'user_id': str(current_user.user_id)})
                current_app.logger.info(
                    f"[Customer Portal] Created new Stripe customer {customer.id}"
                )
            except Exception as e:
                current_app.logger.error(
                    f"[Customer Portal] Error creating customer: {str(e)}")
                return jsonify(
                    {'error': 'Failed to create customer portal session'}), 500

        # Create portal session
        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=customer.id,
                return_url=return_url,
            )

            current_app.logger.info(
                f"[Customer Portal] Created portal session {portal_session.id}"
            )

            # Sync customer data after creating portal session
            sync_success = sync_customer_data(customer.id, current_user.user_id)
            if not sync_success:
                current_app.logger.warning(f"[Customer Portal] Sync failed but continuing with portal session")

            return jsonify({
                'url': portal_session.url,
                'session_id': portal_session.id,
                'sync_status': 'success' if sync_success else 'failed'
            }), 200

        except Exception as e:
            current_app.logger.error(
                f"[Customer Portal] Error creating portal session: {str(e)}")
            return jsonify(
                {'error': 'Failed to create customer portal session'}), 500

    except Exception as e:
        current_app.logger.error(
            f"[Customer Portal] Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@customer_portal_bp.route('/api/force-sync-customer-data', methods=['POST'])
@login_required
def force_sync_customer_data():
    """Force sync customer data from Stripe for debugging"""
    try:
        current_app.logger.info(f"[Customer Portal] Force sync requested for user {current_user.user_id}")

        # Set Stripe API key
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

        # Find or create Stripe customer
        customers = stripe.Customer.list(email=current_user.email, limit=5)
        if not customers.data:
            return jsonify({'error': 'No Stripe customer found'}), 404

        customer = customers.data[0]
        current_app.logger.info(f"[Customer Portal] Found customer: {customer.id}")

        # Force sync
        sync_success = sync_customer_data(customer.id, current_user.user_id)

        if sync_success:
            # Get updated subscription data
            user_subscription = UserSubscription.query.filter_by(user_id=current_user.user_id).first()
            return jsonify({
                'message': 'Customer data synced successfully',
                'customer_id': customer.id,
                'subscription_data': user_subscription.to_dict() if user_subscription else None
            }), 200
        else:
            return jsonify({'error': 'Failed to sync customer data'}), 500

    except Exception as e:
        current_app.logger.error(f"[Customer Portal] Error in force sync: {str(e)}")
        return jsonify({'error': f'Failed to sync customer data: {str(e)}'}), 500


@customer_portal_bp.route('/api/sync-customer-data', methods=['POST'])
@login_required
def sync_customer_data_endpoint():
    """Manually sync customer data from Stripe"""
    try:
        current_app.logger.info(
            f"[Customer Portal] Manual sync requested for user {current_user.user_id}"
        )

        # Set Stripe API key
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

        # Find Stripe customer
        customers = stripe.Customer.list(email=current_user.email, limit=5)
        if not customers.data:
            return jsonify({'error': 'Stripe customer not found'}), 404

        customer = customers.data[0]

        # Sync customer data
        sync_success = sync_customer_data(customer.id, current_user.user_id)

        if sync_success:
            return jsonify({
                'message': 'Customer data synced successfully',
                'customer_id': customer.id
            }), 200
        else:
            return jsonify({'error': 'Failed to sync customer data'}), 500

    except Exception as e:
        current_app.logger.error(
            f"[Customer Portal] Error syncing customer data: {str(e)}"
        )
        return jsonify({'error': 'Failed to sync customer data'}), 500


@customer_portal_bp.route('/customer_portal')
@login_required
def customer_portal():
    """Redirect directly to Stripe customer portal."""
    try:
        # Create Stripe customer portal session and redirect
        return redirect_to_stripe_portal()
    except Exception as e:
        flash(f'Error accessing customer portal: {str(e)}', 'error')
        return redirect(url_for('main.index'))


def redirect_to_stripe_portal():
    """Helper function to redirect to Stripe customer portal."""
    try:
        # Create portal session
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

        # Find or create customer
        # if not customer:
        #     customer = stripe.Customer.create(
        #         email=current_user.email,
        #         name=current_user.username,
        #         metadata={'user_id': str(current_user.user_id)})

        latest_active_sub = SubscriptionController._find_active_stripe_subscription_by_user_id(current_user.user_id)
        if not latest_active_sub:
            current_app.logger.error(
                f"[Customer Portal] No customer and subscription found on Stripe: {str(e)}"
            )
            
            return jsonify({'error': 'No customer data and subscription data on Stirpe '}), 500

        customer_id = latest_active_sub.customer

        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url='https://sandboxdev.saasquatchleads.com/subscription',
        )

        # Sync customer data before redirect
        sync_customer_data(customer_id, current_user.user_id)

        # Redirect to portal
        return redirect(portal_session.url)

    except Exception as e:
        current_app.logger.error(
            f"[Customer Portal] Error in form handler: {str(e)}")
        flash('Error accessing customer portal.', 'error')
        return redirect(url_for('main.index'))
