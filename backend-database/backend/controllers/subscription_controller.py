# Add function to create Stripe portal session and redirect
from typing import Optional
import stripe
from flask import request, jsonify, current_app, url_for
from models.user_model import User, db
from models.user_subscription_model import UserSubscription
from sqlalchemy import func
from dateutil.relativedelta import relativedelta
from datetime import datetime
from utils.email_utils import send_outreach_confirmation_email
import logging
from models.promo_code_model import PromoCode
from models.coupon_usage_model import CouponUsage
from models.workspace_member_model import WorkspaceMember
from utils.stripe_utils import get_end_coupon_timestamp
from models.last_coupon_by_user_model import LastCouponByUser

class SubscriptionController:

    @staticmethod
    def create_checkout_session(user):
        try:
            current_app.logger.info(f"[Subscription] Incoming create_checkout_session request. User: {getattr(user, 'user_id', None)}, is_authenticated: {getattr(user, 'is_authenticated', None)}")

            # Validate request data
            if not request.json:
                current_app.logger.error("[Subscription] No JSON data provided")
                return {'error': 'No data provided'}, 400

            plan_type = request.json.get('plan_type')
            current_app.logger.info(f"[Subscription] Extracted plan_type: {plan_type}")

            if not plan_type:
                current_app.logger.error("[Subscription] No plan_type provided")
                return {'error': 'plan_type is required'}, 400

            price_id = current_app.config['STRIPE_PRICES'].get(plan_type)
            if not price_id:
                current_app.logger.error(f"[Subscription] Invalid plan_type provided: {plan_type}. Available plans: {list(current_app.config['STRIPE_PRICES'].keys())}")
                return {'error': f'Invalid plan type provided: {plan_type}. Available plans: {list(current_app.config["STRIPE_PRICES"].keys())}'}, 400

            # Validate Stripe configuration
            if not current_app.config.get('STRIPE_SECRET_KEY'):
                current_app.logger.error("[Subscription] STRIPE_SECRET_KEY not configured")
                return {'error': 'Payment system not configured'}, 500

            stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
            success_url = "https://app.saasquatchleads.com"
            cancel_url = "https://app.saasquatchleads.com/subscription"

            # Determine the Stripe mode based on plan_type
            if plan_type == 'call_outreach':
                stripe_mode = 'payment'  # For one-time payments
            else:
                stripe_mode = 'subscription' # For recurring subscriptions

            # Initialize parameters for checkout session
            checkout_session_params = {
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'mode': stripe_mode,
                'success_url': success_url,
                'cancel_url': cancel_url,
                'client_reference_id': str(user.user_id),
                'payment_method_types': [
                    'card',
                    'link',
                ],
                "allow_promotion_codes":True,
                'metadata': {
                    'plan_type': plan_type,
                    'user_id': str(user.user_id)
                }
            }

            # Add subscription_data only if in subscription mode
            if stripe_mode == 'subscription':
                checkout_session_params['subscription_data'] = {
                    'metadata': {
                        'plan_type': plan_type,
                        'user_id': str(user.user_id)
                    }
                }

            # Handle customer details for Stripe Checkout
            user_sub = UserSubscription.query.filter_by(user_id=user.user_id).first()
            if user_sub and user_sub.stripe_customer_id:
                checkout_session_params['customer'] = user_sub.stripe_customer_id
                current_app.logger.info(f"[Subscription] Found existing stripe_customer_id for user {user.user_id}")
            else:
                checkout_session_params['customer_email'] = user.email
                current_app.logger.info(f"[Subscription] No stripe_customer_id found for user {user.user_id}. Using email {user.email} for checkout.")

            checkout_session = stripe.checkout.Session.create(
                **checkout_session_params
            )
            current_app.logger.info(f"[Subscription] Stripe session created successfully for user {user.user_id}, plan {plan_type}")
            current_app.logger.info(f"commented code for the db updates starts ")
            current_app.logger.info(f"===================== WEBHOOK FUNCTION IS WORKING, WAITING FOR WEBHOOK TO UPDATE DB =====================")
            # --- DB update logic moved to webhook. The following is intentionally commented out ---
            # Always update or create UserSubscription for the selected plan
            # user.tier = plan_type
            # from models.user_subscription_model import UserSubscription
            # from models.plan_model import Plan
            # now = datetime.utcnow()
            # plan = Plan.query.filter(func.lower(Plan.plan_name) == plan_type.lower()).first()
            # if plan:
            #     expiration = None
            #     if plan.credit_reset_frequency == 'monthly':
            #         expiration = now + relativedelta(months=1)
            #     elif plan.credit_reset_frequency == 'annual':
            #         expiration = now + relativedelta(years=1)
            #     # Upsert logic: update if exists, else create
            #     user_sub = UserSubscription.query.filter_by(user_id=user.user_id).first()
            #     if user_sub:
            #         user_sub.plan_id = plan.plan_id
            #         user_sub.plan_name = plan.plan_name
            #         user_sub.credits_remaining = plan.initial_credits if plan.initial_credits is not None else 0
            #         user_sub.payment_frequency = plan.credit_reset_frequency if plan.credit_reset_frequency else 'monthly'
            #         user_sub.tier_start_timestamp = now
            #         user_sub.plan_expiration_timestamp = expiration
            #         user_sub.username = user.username
            #         current_app.logger.info(f"[Subscription] UserSubscription for user {user.user_id} updated to plan {plan_type}.")
            #     else:
            #         new_sub = UserSubscription(
            #             user_id=user.user_id,
            #             plan_id=plan.plan_id,
            #             plan_name=plan.plan_name,
            #             credits_remaining=plan.initial_credits if plan.initial_credits is not None else 0,
            #             payment_frequency=plan.credit_reset_frequency if plan.credit_reset_frequency else 'monthly',
            #             tier_start_timestamp=now,
            #             plan_expiration_timestamp=expiration,
            #             username=user.username
            #         )
            #         db.session.add(new_sub)
            #         current_app.logger.info(f"[Subscription] Created new UserSubscription for user {user.user_id} with plan {plan_type}.")
            # else:
            #     current_app.logger.error(f"[Subscription] Plan {plan_type} not found when updating/creating UserSubscription for user {user.user_id}.")
            # db.session.commit()
            # current_app.logger.info(f"[Subscription] User {user.user_id} tier updated to {user.tier} In db.")
            # --- End of commented block ---
            return {'sessionId': checkout_session.id}, 200
        except Exception as e:
            import traceback
            current_app.logger.error(f"[Subscription] Error creating checkout session: {e}\n{traceback.format_exc()}")
            return {'error': 'Error creating checkout session. Please try again later.'}, 500

    @staticmethod
    def handle_stripe_webhook(payload, sig_header):
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
        webhook_secret = current_app.config['STRIPE_WEBHOOK_SECRET']


        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            current_app.logger.info(f"Webhook received: {event['type']}")

            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                user_id = session.get('client_reference_id')
                plan_type = None

                current_app.logger.info(f"[Webhook] Processing checkout.session.completed for user_id: {user_id}")

                # Try to get plan_type from session metadata first (more reliable)
                if 'metadata' in session and session['metadata'].get('plan_type'):
                    plan_type = session['metadata']['plan_type']
                    current_app.logger.info(f"[Webhook] Got plan_type from metadata: {plan_type}")

                # Fallback: get from subscription metadata if session metadata doesn't exist
                if not plan_type and 'subscription' in session:
                    try:
                        subscription = stripe.Subscription.retrieve(session['subscription'])
                        if subscription.metadata and subscription.metadata.get('plan_type'):
                            plan_type = subscription.metadata['plan_type']
                            current_app.logger.info(f"[Webhook] Got plan_type from subscription metadata: {plan_type}")
                    except Exception as e:
                        current_app.logger.warning(f"[Webhook] Could not retrieve subscription metadata: {str(e)}")

                # Final fallback: get price_id from line items and map to plan_type
                if not plan_type:
                    try:
                        line_items = stripe.checkout.Session.list_line_items(session['id'])
                        if line_items and line_items.data:
                            price_id = line_items.data[0].price.id
                            # Map price_id to plan_type using config
                            for k, v in current_app.config['STRIPE_PRICES'].items():
                                if v == price_id:
                                    plan_type = k
                                    break
                            current_app.logger.info(f"[Webhook] Got plan_type from line items: {plan_type}")
                    except Exception as e:
                        current_app.logger.error(f"[Webhook] Error retrieving line items: {str(e)}")

                # Log payment method used
                if session.get('payment_intent'):
                    # One-time payment
                    payment_intent = stripe.PaymentIntent.retrieve(session['payment_intent'])
                    payment_method_type = payment_intent.payment_method_types[0] if payment_intent.payment_method_types else 'unknown'
                    current_app.logger.info(f"[Webhook] Payment completed using: {payment_method_type}")
                elif session.get('subscription'):
                    # Subscription: get the latest invoice
                    subscription = stripe.Subscription.retrieve(session['subscription'])
                    latest_invoice_id = subscription.get('latest_invoice')
                    if latest_invoice_id:
                        invoice = stripe.Invoice.retrieve(latest_invoice_id)
                        payment_intent_id = invoice.get('payment_intent')
                        if payment_intent_id:
                            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                            payment_method_type = payment_intent.payment_method_types[0] if payment_intent.payment_method_types else 'unknown'
                            current_app.logger.info(f"[Webhook] Subscription payment completed using: {payment_method_type}")
                        else:
                            current_app.logger.info("[Webhook] No payment_intent found on invoice; cannot log payment method type.")
                    else:
                        current_app.logger.info("[Webhook] No latest_invoice found on subscription; cannot log payment method type.")
                else:
                    current_app.logger.info("[Webhook] No payment_intent or subscription found in session; skipping payment method logging.")

                # Check if this is an outreach service payment
                if session.get('metadata') and session['metadata'].get('service_type') == 'phone_call_outreach':
                    current_app.logger.info(f"-------------[Webhook] Processing outreach payment for user_id: {user_id} DOING NOTHING")
                    # from controllers.outreach_controller import OutreachController
                    # if OutreachController.handle_outreach_payment_success(session):
                    #     current_app.logger.info(f"[Webhook] Successfully processed outreach payment for user {user_id}")
                    # else:
                    #     current_app.logger.error(f"[Webhook] Failed to process outreach payment for user {user_id}")
                 # Check if this is a pause subscription payment
                elif session.get('metadata') and session['metadata'].get('is_pause_subscription') == 'true':
                     current_app.logger.info(f"[Webhook] Processing pause subscription payment for user_id: {user_id}")
                     if SubscriptionController.handle_pause_subscription_success(session['metadata'], user_id):
                         current_app.logger.info(f"[Webhook] Successfully processed pause subscription for user {user_id}")
                     else:
                         current_app.logger.error(f"[Webhook] Failed to process pause subscription for user {user_id}")
                # Only proceed if we have both user_id and plan_type for subscription payments
                elif user_id and plan_type:
                    from models.user_model import User
                    user = User.query.get(user_id)
                    # Handle 'call_outreach' plan specifically
                    if plan_type == 'call_outreach':
                        from models.user_subscription_model import UserSubscription
                        user_sub = UserSubscription.query.filter_by(user_id=user_id).first()
                        if user_sub:
                            user_sub.is_call_outreach_cust = True
                            db.session.commit()
                            current_app.logger.info(f"[Webhook] User {user_id} subscribed to 'Pro Call Outreach'. is_call_outreach_cust set to True.")
                            # Send confirmation email
                            if user:
                                send_outreach_confirmation_email(user.email, user.username)
                                current_app.logger.info(f"[Webhook] Sent outreach confirmation email to user {user.username}.")
                            else:
                                current_app.logger.warning(f"[Webhook] User object not available for outreach confirmation email,{user.username} despite user_id being present.")
                        else:
                            current_app.logger.warning(f"[Webhook] UserSubscription not found for user {user_id} when processing 'call_outreach' payment.")
                        return jsonify({'status': 'success'}), 200 # Exit after handling call_outreach

                    if user:
                         #Check if this is a pause subscription
                         #if plan_type.startswith('pause_'):
                        #     # Handle pause subscription
                        #     if SubscriptionController.handle_pause_subscription_success(session['metadata'], user_id):
                        #         current_app.logger.info(f"[Webhook] Successfully processed pause subscription for user {user_id}")
                        #     else:
                        #         current_app.logger.error(f"[Webhook] Failed to process pause subscription for user {user_id}")
                        # else:
                            # Handle regular subscription
                        user.tier = plan_type
                        user.status = "active"
                        # Upsert UserSubscription as in create_checkout_session
                        from models.user_subscription_model import UserSubscription
                        from models.plan_model import Plan
                        from sqlalchemy import func
                        from dateutil.relativedelta import relativedelta
                        from datetime import datetime
                        now = datetime.utcnow()
                        # Map plan_type to correct plan name in database
                        plan_name_mapping = {
                            'bronze_annual': 'Bronze_Annual',
                            'silver_annual': 'Silver_Annual',
                            'gold_annual': 'Gold_Annual',
                            'platinum_annual': 'Platinum_Annual',
                            'bronze': 'Bronze',
                            'silver': 'Silver',
                            'gold': 'Gold',
                            'platinum': 'Platinum',
                            'student_monthly': 'Student Monthly',
                            'student_semester': 'Student Semester',
                            'student_annual': 'Student Annual',
                            'call_outreach': 'Pro Call Outreach'
                        }
                        mapped_plan_name = plan_name_mapping.get(plan_type, plan_type)
                        plan = Plan.query.filter(func.lower(Plan.plan_name) == mapped_plan_name.lower()).first()
                        if plan:
                            expiration = None
                            if plan.credit_reset_frequency == 'monthly':
                                expiration = now + relativedelta(months=1)
                            elif plan.credit_reset_frequency == 'annual':
                                expiration = now + relativedelta(years=1)
                            user_sub = UserSubscription.query.filter_by(user_id=user.user_id).first()
                            if user_sub:
                                user_sub.plan_id = plan.plan_id
                                user_sub.plan_name = plan.plan_name
                                user_sub.credits_remaining = plan.initial_credits if plan.initial_credits is not None else 0
                                user_sub.payment_frequency = plan.credit_reset_frequency if plan.credit_reset_frequency else 'monthly'
                                user_sub.tier_start_timestamp = now
                                user_sub.plan_expiration_timestamp = expiration
                                user_sub.stripe_customer_id = session.get('customer')
                                user_sub.username = user.username
                                user_sub.is_canceled = False
                                user_sub.canceled_at = None
                                user_sub.cancel_at_period_end = False
                                user_sub.is_paused = False
                                user_sub.pause_status = "none"
                                user_sub.pause_start_date = None
                                user_sub.pause_duration_days = None
                                user_sub.original_plan_days_remaining = None
                                user_sub.original_plan_id = None
                                user_sub.original_plan_name = None
                                user_sub.storage_subscription_id = None
                                user_sub.resume_schedule_id = None
                                current_app.logger.info(f"[Webhook] UserSubscription for user {user.user_id} updated to plan {plan_type}.")
                            else:
                                new_sub = UserSubscription(
                                    user_id=user.user_id,
                                    plan_id=plan.plan_id,
                                    plan_name=plan.plan_name,
                                    credits_remaining=plan.initial_credits if plan.initial_credits is not None else 0,
                                    payment_frequency=plan.credit_reset_frequency if plan.credit_reset_frequency else 'monthly',
                                    tier_start_timestamp=now,
                                    plan_expiration_timestamp=expiration,
                                    stripe_customer_id=session.get('customer'),
                                    username=user.username
                                )
                                db.session.add(new_sub)
                                current_app.logger.info(f"[Webhook] Created new UserSubscription for user {user.user_id} with plan {plan_type}.")
                            db.session.commit()
                            current_app.logger.info(f"[Webhook] User {user.user_id} tier updated to {user.tier} In db.")
                        else:
                            current_app.logger.error(f"[Webhook] Plan {plan_type} not found when updating/creating UserSubscription for user {user.user_id}.")
                    else:
                        current_app.logger.warning(f"[Webhook] User {user_id} not found for successful payment.")
                else:
                    current_app.logger.warning(f"[Webhook] Missing user_id or plan_type in session for successful payment.")

            elif event['type'] == 'checkout.session.async_payment_failed':
                session = event['data']['object']
                user_id = session.get('client_reference_id')
                current_app.logger.warning(f"[Webhook] Async payment failed for user {user_id}")
                if user_id:
                    from models.user_model import User
                    user = User.query.get(user_id)
                    if user:
                        user.tier = 'free'
                        db.session.commit()
                        current_app.logger.info(f"Reset user {user_id} to free tier due to payment failure")

            elif event['type'] == 'invoice.payment_failed':
                # Handle recurring payment failures
                invoice = event['data']['object']
                subscription_id = invoice.get('subscription')
                customer_id = invoice.get('customer')
                current_app.logger.warning(f"[Webhook] Invoice payment failed for subscription {subscription_id}")

                if customer_id:
                    try:
                        customer = stripe.Customer.retrieve(customer_id)
                        user = User.query.filter_by(email=customer.email).first()
                        if user:
                            current_app.logger.info(f"[Webhook] Recurring payment failed for user {user.user_id}")
                            # You can implement retry logic or downgrade logic here
                            # For now, we'll just log it
                    except Exception as e:
                        current_app.logger.error(f"Error processing payment failure: {str(e)}")

            elif event['type'] == 'payment_method.attached':
                # Log when customers add new payment methods
                payment_method = event['data']['object']
                customer_id = payment_method.get('customer')
                payment_method_type = payment_method.get('type')
                current_app.logger.info(f"[Webhook] New payment method ({payment_method_type}) attached to customer {customer_id}")

            elif event['type'] == 'customer.subscription.deleted':
                subscription = event['data']['object']
                metadata = subscription['metadata']
                user_id = metadata.get('user_id') if metadata else None
                customer_id = subscription.get('customer')
                if customer_id or user_id:
                    try:
                        from models.user_subscription_model import UserSubscription
                        from models.user_model import User
                        customer = None
                        user = None
                        if not user_id:
                            customer = stripe.Customer.retrieve(customer_id)
                            user = User.query.filter_by(email=customer.email).first()
                        else:
                            user = User.query.filter_by(user_id=user_id).first()

                        if user:
                            user_sub = UserSubscription.query.filter_by(user_id=user.user_id).first()

                            # Check if this was a scheduled cancellation
                            is_scheduled_cancel = (user_sub and
                                                 user_sub.payment_frequency and
                                                 '_scheduled_cancel' in user_sub.payment_frequency)

                            if is_scheduled_cancel:
                                current_app.logger.info(f"Processing scheduled cancellation for user {user.user_id} - subscription period has ended")
                            else:
                                current_app.logger.info(f"Processing immediate cancellation for user {user.user_id}")

                            # Now actually cancel and move to free tier
                            SubscriptionController._handle_local_cancellation(user, user_sub)
                            current_app.logger.info(f"Processed subscription cancellation for user {user.user_id}")
                    except Exception as e:
                        current_app.logger.error(f"Error processing subscription.deleted webhook: {str(e)}")

            elif event['type'] == 'customer.subscription.updated':
                subscription = event['data']['object']
                previous_attr = event['data']['previous_attributes']
                customer_id = subscription.get('customer')

                # Other way to get user subscription with associated user_id from subscription metadata
                user_id  = subscription['metadata'].get('user_id') if subscription.get('metadata') else None
                if customer_id or user_id:
                    try:
                        from models.user_subscription_model import UserSubscription
                        from models.user_model import User
                        customer = None
                        user = None
                        if not user_id:
                            customer = stripe.Customer.retrieve(customer_id)
                            user = User.query.filter_by(email=customer.email).first()
                        else:
                            user = User.query.filter_by(user_id=user_id).first()

                        if user:
                            user_sub = UserSubscription.query.filter_by(user_id=user.user_id).first()

                            # Handle cancel_at_period_end updates
                            if subscription.get('cancel_at_period_end'):
                                current_app.logger.info(f"Webhook: Subscription {subscription['id']} scheduled for cancellation at period end for user {user.user_id}")
                                current_app.logger.info(f"Webhook: cancel_at_period_end timestamp: {subscription.get('cancel_at')}")

                                # Mark the subscription as scheduled for cancellation
                                if user_sub and user_sub.payment_frequency and '_scheduled_cancel' not in user_sub.payment_frequency:
                                    user_sub.payment_frequency = f"{user_sub.payment_frequency}_scheduled_cancel"
                                    user_sub.cancel_at_period_end = True
                                    db.session.commit()
                                    current_app.logger.info(f"Webhook: Marked subscription as scheduled for cancellation for user {user.user_id}")

                            # Handle reactivation (when cancel_at_period_end is removed)
                            elif not subscription.get('cancel_at_period_end') and user_sub and user_sub.payment_frequency and '_scheduled_cancel' in user_sub.payment_frequency:
                                # Remove the scheduled cancellation marker
                                user_sub.payment_frequency = user_sub.payment_frequency.replace('_scheduled_cancel', '')
                                user_sub.cancel_at_period_end = False
                                db.session.commit()
                                current_app.logger.info(f"Webhook: Removed scheduled cancellation for user {user.user_id} - subscription reactivated")
                            
                            # Handle pause collection subscription
                            if subscription.get('pause_collection') and not previous_attr.get('pause_collection'):
                                current_app.logger.info(f"Webhook: Paused invoice for user {user.user_id} - subscription paused")
                            # If user resume
                            elif not subscription.get('pause_collection') and previous_attr.get('pause_collection'):
                                _, status_code = SubscriptionController.resume_subscription_early(user)
                                if status_code == 200:
                                    current_app.logger.info(f"Webhook: Resume subscription for user {user.user_id}")
                                else:
                                    current_app.logger.error(f"Error processing resume subscription for user {user.user_id}")
                                
                                is_annual = subscription['metadata'].get('is_annual') if subscription.get('metadata') else None
                                if is_annual == "true":
                                    from dateutil.relativedelta import relativedelta
                                    # Adding trial end to pause the Stripe payment
                                    next_billing_date = user_sub.plan_expiration_timestamp + relativedelta(days=1)
                                    stripe.Subscription.modify(
                                        subscription.id,
                                        trial_end=int(next_billing_date.timestamp()),
                                        proration_behavior="none"
                                    )
                                
                    except Exception as e:
                        current_app.logger.error(f"Error processing subscription.updated webhook: {str(e)}")

            elif event['type'] == 'payment_intent.succeeded':
                # Handle one-time payments like outreach service
                payment_intent = event['data']['object']
                if payment_intent.get('metadata') and payment_intent['metadata'].get('service_type') == 'phone_call_outreach':
                    current_app.logger.info(f"[Outreach] Payment intent succeeded for outreach service")
                    # This will be handled by checkout.session.completed for outreach
                    pass

            elif event['type'] == 'customer.updated':
                # Handle customer updates from portal
                customer = event['data']['object']
                current_app.logger.info(f"[Webhook] Customer updated: {customer.get('id')}")

                # Update local user information if needed
                try:
                    from models.user_model import User
                    user = User.query.filter_by(email=customer.get('email')).first()
                    if user:
                        # Update any relevant customer information
                        # Note: Don't use customer email as login credential as per Stripe docs
                        current_app.logger.info(f"[Webhook] Updated customer info for user {user.user_id}")
                except Exception as e:
                    current_app.logger.error(f"[Webhook] Error updating customer info: {str(e)}")

            elif event['type'] == 'payment_method.attached':
                # Handle payment method additions
                payment_method = event['data']['object']
                customer_id = payment_method.get('customer')
                payment_method_type = payment_method.get('type', 'unknown')
                current_app.logger.info(f"[Webhook] Payment method ({payment_method_type}) attached to customer {customer_id}")

            elif event['type'] == 'payment_method.detached':
                # Handle payment method removals
                payment_method = event['data']['object']
                customer_id = payment_method.get('customer')
                payment_method_type = payment_method.get('type', 'unknown')
                current_app.logger.info(f"[Webhook] Payment method ({payment_method_type}) detached from customer {customer_id}")

            elif event['type'] == 'customer.tax_id.created':
                # Handle tax ID creation
                tax_id = event['data']['object']
                customer_id = tax_id.get('customer')
                current_app.logger.info(f"[Webhook] Tax ID created for customer {customer_id}")

            elif event['type'] == 'customer.tax_id.updated':
                # Handle tax ID updates (validation status changes)
                tax_id = event['data']['object']
                customer_id = tax_id.get('customer')
                verification_status = tax_id.get('verification', {}).get('status')
                current_app.logger.info(f"[Webhook] Tax ID updated for customer {customer_id}, verification status: {verification_status}")

            elif event['type'] == 'customer.tax_id.deleted':
                # Handle tax ID deletion
                tax_id = event['data']['object']
                customer_id = tax_id.get('customer')
                current_app.logger.info(f"[Webhook] Tax ID deleted for customer {customer_id}")

            elif event['type'] == 'billing_portal.session.created':
                # Handle portal session creation (for logging/analytics)
                session = event['data']['object']
                customer_id = session.get('customer')
                current_app.logger.info(f"[Webhook] Billing portal session created for customer {customer_id}")

            elif event['type'] == 'billing_portal.configuration.created':
                # Handle portal configuration creation
                config = event['data']['object']
                current_app.logger.info(f"[Webhook] Billing portal configuration created: {config.get('id')}")

            elif event['type'] == 'billing_portal.configuration.updated':
                # Handle portal configuration updates
                config = event['data']['object']
                current_app.logger.info(f"[Webhook] Billing portal configuration updated: {config.get('id')}")
            
            elif event['type'] == 'invoice.paid':
                invoice = event['data']['object']
                invoice_with_discounts = stripe.Invoice.retrieve(invoice["id"], expand=["discounts", "discounts.coupon", "discounts.promotion_code"])

                subscription = invoice_with_discounts.parent.subscription_details.subscription
                user_id = invoice_with_discounts.parent.subscription_details.metadata.get("user_id", None)

                # Renew user's subscription every invoice paid
                if invoice.billing_reason == 'subscription_cycle':
                    from models.user_subscription_model import UserSubscription
                    from models.user_model import User
                    from models.plan_model import Plan
                    try:
                        user_sub = UserSubscription.query.filter_by(user_id=user_id).first()
                        
                        if user_sub:
                            user = User.query.get(user_sub.user_id)
                            plan = Plan.query.get(user_sub.plan_id)
                            
                            if user and plan:
                                # Call the new renewal logic
                                SubscriptionController._handle_subscription_renewal(user, user_sub, plan)
                            else:
                                current_app.logger.error(f"Could not find user or plan for subscription renewal. User ID: {user_sub.user_id}")
                        else:
                            current_app.logger.error(f"Received renewal invoice but could not find UserSubscription for customer: {customer_id}")

                    except Exception as e:
                        current_app.logger.error(f"Error processing subscription renewal for invoice {invoice.id}: {e}")
                        db.session.rollback()

                # Adding coupon/promo code usage
                if user_id and invoice_with_discounts.get("discounts"):
                    try:
                        from datetime import datetime
                        # Check if a discount was applied
                        discount_obj = invoice_with_discounts.discounts[0]
                        promo_code_obj = discount_obj.promotion_code
                        coupon_obj = promo_code_obj.coupon
                        
                        # 1. Upsert (update or insert) the Coupon details in our DB
                        promo_record = PromoCode.query.filter_by(stripe_promo_id=promo_code_obj.id).first()
                        if not promo_record:
                            promo_record = PromoCode(stripe_promo_id=promo_code_obj.id)
                        
                        promo_record.code = promo_code_obj.code
                        promo_record.stripe_coupon_id = coupon_obj.id
                        promo_record.stripe_coupon_name = coupon_obj.name
                        promo_record.times_redeemed = promo_code_obj.times_redeemed
                        promo_record.amount_off = coupon_obj.amount_off
                        promo_record.percent_off = coupon_obj.percent_off
                        promo_record.max_redemptions = promo_code_obj.max_redemptions
                        promo_record.currency = coupon_obj.currency
                        promo_record.duration = coupon_obj.duration
                        promo_record.livemode = coupon_obj.livemode
                        promo_record.duration_in_months = coupon_obj.duration_in_months
                        promo_record.is_active = promo_code_obj.active
                        promo_record.expires_at = datetime.fromtimestamp(promo_code_obj.expires_at) if promo_code_obj.expires_at else None
                        promo_record.first_time_transaction = promo_code_obj.restrictions.first_time_transaction
                        promo_record.minimum_amount =  promo_code_obj.restrictions.minimum_amount
                        promo_record.minimum_amount_currency =  promo_code_obj.restrictions.minimum_amount_currency
                        db.session.add(promo_record)
                        db.session.flush() # Flush to get the promo_record.id

                        # 2. Create a historical log entry for this usage
                        usage_log = CouponUsage(
                            user_id=user_id,
                            promo_code_id=promo_record.id,
                            livemode=promo_code_obj.livemode,
                            stripe_subscription_id=subscription
                        )

                        # Upsert the LastCouponByUser record to track the latest applied coupon
                        last_coupon_record = LastCouponByUser.query.filter_by(user_id=user_id).first()
                        if not last_coupon_record:
                            last_coupon_record = LastCouponByUser(user_id=user_id)

                        last_coupon_record.stripe_coupon_id = coupon_obj.id
                        last_coupon_record.currency = coupon_obj.currency
                        last_coupon_record.amount_off = coupon_obj.amount_off
                        last_coupon_record.percent_off = coupon_obj.percent_off
                        last_coupon_record.promo_code = promo_code_obj.code
                        last_coupon_record.stripe_subscription_id = subscription
                        last_coupon_record.stripe_invoice_id = invoice.id
                        last_coupon_record.livemode = promo_code_obj.livemode

                        # Count when the discount expired for the subscription
                        finished_timestamp = get_end_coupon_timestamp(discount_obj.start, coupon_obj.duration, coupon_obj.duration_in_months)

                        last_coupon_record.expires_at = datetime.fromtimestamp(finished_timestamp) if finished_timestamp else None

                        # Add the new or updated record to the session.
                        db.session.add(last_coupon_record)
                        db.session.add(usage_log)
                        db.session.flush() 
                        
                        db.session.commit()
                        
                        # Update subscription metadata to add discount data
                        subscription_obj = stripe.Subscription.retrieve(subscription)
                        updated_metadata = subscription_obj.metadata
                        updated_metadata['is_discounted'] = "true"
                        expires_at = None
                        

                        if finished_timestamp:
                            expires_at = str(int(finished_timestamp))
                        else:
                            expires_at = 'Never'
                    
                        updated_metadata['coupon_id'] = coupon_obj.id
                        updated_metadata['promo_code'] = promo_code_obj.code
                        if coupon_obj.amount_off:
                            updated_metadata['amount_off'] = coupon_obj.amount_off
                        if coupon_obj.percent_off:
                            updated_metadata['percent_off'] = coupon_obj.percent_off
                        updated_metadata['currency'] = coupon_obj.currency
                        updated_metadata['discount_finished_timestamp'] = expires_at
                        
                        stripe.Subscription.modify(
                            subscription,
                            metadata=updated_metadata
                        )
                        current_app.logger.info(f"[Webhook] Successfully logged coupon usage for cuatomer {user_id} with coupon {coupon_obj.id}")

                    except Exception as e:
                        current_app.logger.error(f"[Webhook] Error processing coupon logic for customer {user_id}: {e}")
                        db.session.rollback()

                # If discount not applied, set false and null to discount-related data
                if not invoice_with_discounts.get("discounts"):
                    try:
                        subscription_obj = stripe.Subscription.retrieve(subscription)
                        updated_metadata = subscription_obj.metadata
                        updated_metadata['is_discounted'] = "false"
                        # Does not include other discount-related data 
                        stripe.Subscription.modify(
                            subscription,
                            metadata=updated_metadata
                        )
                    except Exception as e:
                        current_app.logger.error(f"[Webhook] Error updating metadata discount of subscription {subscription}")




            # Add other Stripe event types as needed (e.g., invoice.payment_failed for recurring payments)

        except ValueError as e:
            current_app.logger.error(f"Webhook error: Invalid payload - {str(e)}")
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError as e:
            current_app.logger.error(f"Webhook error: Invalid signature - {str(e)}")
            return jsonify({'error': 'Invalid signature'}), 400
        except Exception as e:
            import traceback
            current_app.logger.error(f"Webhook error: {str(e)}\n{traceback.format_exc()}")
            return jsonify({'error': 'Internal server error'}), 500

        return jsonify({'status': 'success'}), 200

    @staticmethod
    def _handle_successful_payment(session):
        try:
            user_id = session.get('client_reference_id')
            if not user_id:
                current_app.logger.warning("No user_id found in session")
                return

            user = User.query.get(user_id)
            if not user:
                current_app.logger.warning(f"User {user_id} not found")
                return

            # Get line items and extract price ID
            line_items = stripe.checkout.Session.list_line_items(session.id)
            if not line_items or not line_items.data:
                current_app.logger.warning("No line items found for session")
                return

            price_id = line_items.data[0].price.id

            # Map price_id to subscription tier, including the new Platinum tier
            price_to_tier = {
                current_app.config['STRIPE_PRICES']['gold']: 'gold',
                current_app.config['STRIPE_PRICES']['silver']: 'silver',
                current_app.config['STRIPE_PRICES']['bronze']: 'bronze',
                current_app.config['STRIPE_PRICES']['platinum']: 'platinum', # Added Platinum tier
                current_app.config['STRIPE_PRICES']['bronze_annual']: 'bronze_annual',
                current_app.config['STRIPE_PRICES']['silver_annual']: 'silver_annual',
                current_app.config['STRIPE_PRICES']['gold_annual']: 'gold_annual',
                current_app.config['STRIPE_PRICES']['platinum_annual']: 'platinum_annual',
            }

            new_tier = price_to_tier.get(price_id)
            print(f" this is the new ties from handle succesfull {new_tier}")
            if not new_tier:
                current_app.logger.warning(f"Invalid price_id: {price_id}")
                return

            # Update the user's tier instead of subscription_tier
            user.tier = new_tier
            db.session.commit()
            current_app.logger.info(f"Successfully updated user {user_id} to tier {new_tier}")

        except Exception as e:
            current_app.logger.info(f" changes not commited error ")
            current_app.logger.error(f"Error handling successful payment for session {session.id}: {str(e)}")
            db.session.rollback()

    @staticmethod
    def get_current_user_subscription_info(user):
        """
        Returns a dictionary with the current user's subscription, plan, and user info (selected fields only).
        """
        from models.user_subscription_model import UserSubscription
        from models.plan_model import Plan
        from models.user_model import User
        import logging

        user_id = user.get_id()
        user_obj = User.query.filter_by(user_id=user_id).first()
        if not user_obj:
            return {'error': 'User not found'}, 404

        user_sub = UserSubscription.query.filter_by(user_id=user_id).first()
        # Inherit subscription from company admin if not found and user is a company member
        if not user_sub and user_obj.company_id:
            admin_user = User.query.filter_by(company_id=user_obj.company_id, is_company_admin=True).first()
            if admin_user:
                user_sub = UserSubscription.query.filter_by(user_id=admin_user.user_id).first()
        if not user_sub:
            if getattr(user_obj, 'role', None) == 'company_member':
                # Try to get Free plan for default
                free_plan = Plan.query.filter(Plan.plan_name.ilike('Free')).first()
                plan_data = None
                if free_plan:
                    plan_data = {
                        'cost_per_lead': float(free_plan.cost_per_lead) if free_plan.cost_per_lead is not None else None,
                        'features_json': free_plan.features_json,
                        'credit_reset_frequency': free_plan.credit_reset_frequency,
                        'initial_credits': free_plan.initial_credits
                    }
                subscription_data = {
                    'credits_remaining': 0,
                    'payment_frequency': 'monthly',
                    'plan_name': 'Free',
                    'tier_start_timestamp': None,
                    'plan_expiration_timestamp': None,
                    'username': user_obj.username,
                    'is_scheduled_for_cancellation': False,
                    'is_paused': False,
                    'pause_status': 'none',
                    'pause_end_date': None,
                    'original_plan_name': None,
                    'original_plan_days_remaining': None,
                    'can_be_reactivated': False,
                    'credit_source': 'personal_subscription'
                }
                logging.info(f"[subscription_info] user_id={user_id}, credits_remaining=0, credit_source=personal_subscription (default, company_member)")
                return {
                    'user': {
                        'user_id': str(user_obj.user_id),
                        'email': user_obj.email
                    },
                    'subscription': subscription_data,
                    'plan': plan_data
                }, 200
            else:
                return {'error': 'User subscription not found'}, 404

        plan = None
        if user_sub.plan_id:
            plan = Plan.query.filter_by(plan_id=user_sub.plan_id).first()

        # Check if subscription is scheduled for cancellation (using Stripe portal data)
        is_scheduled_for_cancellation = getattr(user_sub, 'cancel_at_period_end', False)

        # Clean payment frequency for display
        display_payment_frequency = user_sub.payment_frequency
        # Remove any legacy scheduled cancel markers
        if display_payment_frequency and '_scheduled_cancel' in display_payment_frequency:
            display_payment_frequency = display_payment_frequency.replace('_scheduled_cancel', '')

        # Only include selected fields
        user_data = {
            'user_id': str(user_obj.user_id),
            'email': user_obj.email
        }
        subscription_data = {
            'credits_remaining': user_sub.credits_remaining,
            'payment_frequency': display_payment_frequency,
            'plan_name': user_sub.plan_name,
            'tier_start_timestamp': user_sub.tier_start_timestamp.isoformat() if user_sub.tier_start_timestamp else None,
            'plan_expiration_timestamp': user_sub.plan_expiration_timestamp.isoformat() if user_sub.plan_expiration_timestamp else None,
            'username': user_sub.username,
            'is_scheduled_for_cancellation': is_scheduled_for_cancellation,
            'is_paused': getattr(user_sub, 'is_paused', False),
            'pause_status': getattr(user_sub, 'pause_status', 'none'),
            'pause_end_date': user_sub.pause_end_date.isoformat() if getattr(user_sub, 'pause_end_date', None) else None,
            'original_plan_name': getattr(user_sub, 'original_plan_name', None),
            'original_plan_days_remaining': getattr(user_sub, 'original_plan_days_remaining', None),  # Also add this
            'can_be_reactivated': False,  # Reactivation is now handled through Stripe Customer Portal
            'credit_source': 'personal_subscription'  # default
        }
        credit_source = 'personal_subscription'
        if user_obj.company_id:
            from models.company_credit_allocation_model import CompanyCreditAllocation
            allocation = CompanyCreditAllocation.get_active_allocation(user_obj.company_id, user_obj.user_id)
            if allocation:
                subscription_data['credits_remaining'] = allocation.credits_allocated - allocation.credits_used
                subscription_data['credit_source'] = 'company_allocation'
                credit_source = 'company_allocation'
        plan_data = None
        if plan:
            plan_data = {
                'cost_per_lead': float(plan.cost_per_lead) if plan.cost_per_lead is not None else None,
                'features_json': plan.features_json,
                'credit_reset_frequency': plan.credit_reset_frequency,
                'initial_credits': plan.initial_credits
            }

        # Add credits from team assigned credit
        memberships = WorkspaceMember.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).all()

        total_team_credits = 0
        for m in memberships:
            total_team_credits += m.get_remaining_credits()

        subscription_data['credits_remaining'] += total_team_credits


        # Logging for debug
        logging.info(f"[subscription_info] user_id={user_id}, credits_remaining={subscription_data['credits_remaining']}, credit_source={credit_source}")

        return {
            'user': user_data,
            'subscription': subscription_data,
            'plan': plan_data
        }, 200


    # @staticmethod
    # def is_subscription_scheduled_for_cancellation(user):
    #     """Check if user's subscription is scheduled for cancellation
    #     NOTE: This method is commented out as cancellation status is now managed through Stripe Customer Portal
    #     """
    #     from models.user_subscription_model import UserSubscription

    #     user_sub = UserSubscription.query.filter_by(user_id=user.user_id).first()
    #     if not user_sub:
    #         return False

    #     return (user_sub.payment_frequency and
    #             '_scheduled_cancel' in user_sub.payment_frequency)

    @staticmethod
    def payment_success_handler(user):
        """
        Handle payment success logic and return a JSON response with a redirect URL.
        """
        # You can add any additional logic here if needed (e.g., logging, updating user, etc.)
        return {
            'message': 'Your subscription has been activated successfully!',
            'redirect_url': 'https://app.saasquatchleads.com/'
        }, 200

    @staticmethod
    def payment_cancel_handler(user):
        """
        Handle payment cancel logic and return a JSON response with a redirect URL.
        """
        # You can add any additional logic here if needed (e.g., logging, updating user, etc.)
        return {
            'message': 'Payment cancelled. You can choose a plan when you are ready.',
            'redirect_url': 'https://app.saasquatchleads.com/subscription'
        }, 200

    @staticmethod
    def cancel_subscription(user, cancellation_type='immediate', feedback=None, comment=None):
        """
        Cancels a user's subscription, either immediately or at the period end,
        and updates both Stripe and the local database.
        """
        try:
            stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
            user_sub = UserSubscription.query.filter_by(user_id=user.user_id).first()

            if not user_sub or user.tier == 'free':
                return {'error': 'User does not have an active paid subscription to cancel.'}, 400

            stripe_subscription = SubscriptionController._find_active_stripe_subscription(user, user_sub)

            if not stripe_subscription:
                # If no Stripe subscription is found, we can only perform a local cancellation
                current_app.logger.warning(f"No active Stripe subscription found for user {user.user_id}. Performing local cancellation only.")
                return SubscriptionController._handle_local_cancellation(user, user_sub)
            
            
            if cancellation_type == 'immediate':
                # Cancel the subscription in Stripe immediately.
                stripe.Subscription.cancel(stripe_subscription.id)
                current_app.logger.info(f"Subscription {stripe_subscription.id} cancelled in Stripe for user {user.user_id}.")
                
                # Update the local database to reflect immediate cancellation.
                return SubscriptionController._handle_local_cancellation(user, user_sub)

            elif cancellation_type == 'period_end':
                # Tell Stripe to cancel the subscription at the end of the current period.
                updated_subscription = stripe.Subscription.modify(
                    stripe_subscription.id,
                    cancel_at_period_end=True,
                    cancellation_details={'comment': comment or '', 'feedback': feedback or 'other'}
                )
                current_app.logger.info(f"Subscription {stripe_subscription.id} scheduled for cancellation in Stripe for user {user.user_id}.")
                
                # Update the local database to reflect the scheduled cancellation.
                user.status = 's_cancelled'
                user_sub.cancel_at_period_end = True
                user_sub.is_canceled = False 
                db.session.commit()
                
                cancel_date = datetime.fromtimestamp(updated_subscription.cancel_at)
                return {
                    'message': f'Subscription will be canceled at the end of the billing period on {cancel_date.strftime("%B %d, %Y")}.',
                    'status': 'scheduled_for_cancellation'
                }, 200

            else:
                return {'error': 'Invalid cancellation type specified.'}, 400

        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe API error during cancellation for user {user.user_id}: {str(e)}")
            return {'error': f'A payment processing error occurred: {e.user_message}'}, 500
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error canceling subscription for user {user.user_id}: {str(e)}", exc_info=True)
            return {'error': 'An internal server error occurred during cancellation.'}, 500

    @staticmethod
    def _handle_local_cancellation(user, user_sub):
        """
        Handle cancellation in local database only
        """
        try:
            current_app.logger.info(f"_handle_local_cancellation called for user {user.user_id}")
            from models.plan_model import Plan
            from datetime import datetime

            # Reset user to free tier
            user.tier = 'free'

            # Update subscription to free plan
            free_plan = Plan.query.filter(func.lower(Plan.plan_name) == 'free').first()
            if free_plan:
                user_sub.plan_id = free_plan.plan_id
                user_sub.plan_name = free_plan.plan_name
                user_sub.credits_remaining = free_plan.initial_credits if free_plan.initial_credits is not None else 5
                # Clean up any scheduled cancellation marker
                user_sub.payment_frequency = 'monthly'
                user_sub.tier_start_timestamp = datetime.utcnow()
                user_sub.plan_expiration_timestamp = None
            else:
                # If no free plan exists, set basic defaults
                user_sub.plan_id = None
                user_sub.plan_name = 'Free'
                user_sub.credits_remaining = 5
                # Clean up any scheduled cancellation marker
                user_sub.payment_frequency = 'monthly'
                user_sub.tier_start_timestamp = datetime.utcnow()
                user_sub.plan_expiration_timestamp = None

            # Set cancellation fields
            user_sub.is_canceled = True
            user_sub.canceled_at = datetime.utcnow()
            current_app.logger.info(f"Set is_canceled=True and canceled_at for user {user.user_id} in user_subscriptions.")

            # user.is_active = False
            user.status = 'cancelled'

            db.session.commit()
            current_app.logger.info(f"Successfully canceled subscription locally for user {user.user_id}")
            current_app.logger.info("Returning success response from _handle_local_cancellation.")
            return {
                'message': 'Subscription canceled successfully. You have been moved to the free plan.',
                'new_tier': 'free',
                'credits_remaining': user_sub.credits_remaining
            }, 200

        except Exception as e:
            current_app.logger.error(f"Error in local cancellation for user {user.user_id}: {str(e)}")
            current_app.logger.info("Returning error response from _handle_local_cancellation.")
            db.session.rollback()
            return {'error': 'Error processing cancellation'}, 500


    @staticmethod
    def reactivate_subscription(user):
        """  
        Reactivates a subscription that was scheduled for cancellation.
        """
        try:
            stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
            user_sub = UserSubscription.query.filter_by(user_id=user.user_id).first()

            if not user_sub:
                return {'error': 'No subscription found for this user.'}, 404

            # Check the reliable flag in the database first
            if not user_sub.cancel_at_period_end:
                return {'error': 'Subscription is not scheduled for cancellation.'}, 400

            # Find the corresponding Stripe subscription 
            stripe_subscription = SubscriptionController._find_active_stripe_subscription(user, user_sub)

            if not stripe_subscription:
                return {'error': 'No active Stripe subscription found to reactivate.'}, 404
            
            
            # Tell Stripe to reverse the cancellation
            stripe.Subscription.modify(
                stripe_subscription.id,
                cancel_at_period_end=False
            )
            current_app.logger.info(f"Reactivated subscription {stripe_subscription.id} in Stripe for user {user.user_id}.")

            # Update the local database to reflect the active status
            user.status = 'active'
            user_sub.cancel_at_period_end = False
            # If you used a suffix in payment_frequency, remove it
            if '_scheduled_cancel' in user_sub.payment_frequency:
                user_sub.payment_frequency = user_sub.payment_frequency.replace('_scheduled_cancel', '')
            
            db.session.commit()

            return {
                'message': 'Subscription has been successfully reactivated.',
                'status': 'reactivated'
            }, 200

        except stripe.error.StripeError as e:
            current_app.logger.error(f"Stripe API error during reactivation for user {user.user_id}: {str(e)}")
            return {'error': f'A payment processing error occurred: {getattr(e, "user_message", str(e))}'}, 500
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error reactivating subscription for user {user.user_id}: {str(e)}", exc_info=True)
            return {'error': 'An internal server error occurred during reactivation.'}, 500

    @staticmethod
    def _handle_subscription_renewal(user, user_sub, plan):
        """
        Helper function to renew a user's subscription upon successful payment.
        Resets credits and extends the expiration date.
        """
        from datetime import datetime, timezone
        from dateutil.relativedelta import relativedelta

        credits_to_add = plan.initial_credits if plan and plan.initial_credits is not None else 0
        user_sub.credits_remaining += credits_to_add
        
        now = datetime.now(timezone.utc)
        
        new_expiration = None
        if plan and plan.credit_reset_frequency == 'monthly':
            new_expiration = now + relativedelta(months=1)
        elif plan and plan.credit_reset_frequency == 'annual':
            new_expiration = now + relativedelta(years=1)
            
        user_sub.plan_expiration_timestamp = new_expiration
        
        user.status = 'active'
        user_sub.is_canceled = False
        user_sub.canceled_at = None
        user_sub.cancel_at_period_end = False
        
        db.session.commit()
        
        current_app.logger.info(
            f"Subscription renewed for user {user.user_id}. "
            f"Added {credits_to_add} credits. "
            f"New expiration: {new_expiration}."
        )

    @staticmethod
    def create_pause_checkout_session(user, pause_duration):
        """
        Create a Stripe checkout session for pause subscription
        """
        try:
            current_app.logger.info(
                f"[Pause] Creating pause checkout session for user {user.user_id}, duration: {pause_duration}"
            )

            # Validate pause duration
            duration_mapping = {
                'pause_30_days': {
                    'days': 30,
                    'price_key': 'pause_30'
                },
                'pause_60_days': {
                    'days': 60,
                    'price_key': 'pause_60'
                },
                'pause_90_days': {
                    'days': 90,
                    'price_key': 'pause_90'
                }
            }

            if pause_duration not in duration_mapping:
                current_app.logger.error(
                    f"[Pause] Invalid pause duration: {pause_duration}")
                return {'error': 'Invalid pause duration'}, 400

            duration_info = duration_mapping[pause_duration]
            price_id = current_app.config['STRIPE_PRICES'].get(
                duration_info['price_key'])

            if not price_id:
                current_app.logger.error(
                    f"[Pause] Price ID not found for {duration_info['price_key']}"
                )
                return {
                    'error': 'Pause subscription not configured properly'
                }, 500

            # Get current user subscription
            from models.user_subscription_model import UserSubscription
            user_sub = UserSubscription.query.filter_by(
                user_id=user.user_id).first()

            if not user_sub:
                current_app.logger.error(
                    f"[Pause] No subscription found for user {user.user_id}")
                return {'error': 'No active subscription found'}, 404

            # Check if user is on free tier (but not already paused)
            if user.tier == 'free' and not getattr(user_sub, 'is_paused',
                                                   False):
                current_app.logger.error(
                    f"[Pause] User {user.user_id} is on free tier and not paused"
                )
                return {'error': 'Cannot pause free tier subscription'}, 400

            # Check if already paused
            if getattr(user_sub, 'pause_status',
                       None) in ['pending', 'active']:
                current_app.logger.error(
                    f"[Pause] User {user.user_id} subscription already paused")
                return {'error': 'Subscription is already paused'}, 400

            stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
            success_url = "https://app.saasquatchleads.com"
            cancel_url = "https://app.saasquatchleads.com/pause_subscription"

            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(user.user_id),
                payment_method_types=['card', 'link'],
                metadata={
                    'user_id': str(user.user_id),
                    'is_pause_subscription': 'true',
                    'pause_duration': pause_duration,
                    'pause_days': str(duration_info['days'])
                })

            current_app.logger.info(
                f"[Pause] Checkout session created successfully for user {user.user_id}"
            )
            return {'sessionId': checkout_session.id}, 200

        except Exception as e:
            current_app.logger.error(
                f"[Pause] Error creating pause checkout session: {str(e)}")
            return {'error': 'Failed to create pause checkout session'}, 500

    @staticmethod
    def handle_pause_subscription_success(metadata, user_id):
        """
        Handle successful pause subscription payment - instant activation
        """
        try:
            current_app.logger.info(
                f"[Pause] Processing pause subscription success for user {user_id}"
            )

            from models.user_subscription_model import UserSubscription
            from models.user_model import User
            from models.plan_model import Plan
            from datetime import datetime, timedelta

            user = User.query.get(user_id)
            if not user:
                current_app.logger.error(f"[Pause] User {user_id} not found")
                return False

            user_sub = UserSubscription.query.filter_by(
                user_id=user_id).first()
            if not user_sub:
                current_app.logger.error(
                    f"[Pause] Subscription not found for user {user_id}")
                return False

            pause_duration = metadata.get('pause_duration')
            pause_days = int(metadata.get('pause_days', 0))

            # Add pause collection into Stripe user's subscription to stop generate invoices
            sub = SubscriptionController._find_active_stripe_subscription_by_user_id(user_id)
            if not sub:
                current_app.logger.error(
                    f"[Pause] Stripe subscription not found for User {user_id}."
                )
                return False
            
            # Handle date for expiration, pause, and billing 
            pause_end_timestamp = datetime.now() + relativedelta(months=pause_days//30,days=1) 
            new_expiration_timestamp = user_sub.plan_expiration_timestamp + relativedelta(months=pause_days//30)

            # Adding pause collection into Stripe subscription with different behavior based on the frequency payment
            if user_sub.payment_frequency == "monthly":
                stripe.Subscription.modify(
                    sub.id,
                    pause_collection={
                        "behavior": "mark_uncollectible",
                        "resumes_at": int(pause_end_timestamp.timestamp())
                    }
                )
            else:
                sub.metadata.update({
                    "is_annual": "true",
                })
                stripe.Subscription.modify(
                    sub.id,
                    pause_collection={
                        "behavior": "mark_uncollectible",
                        "resumes_at": int(pause_end_timestamp.timestamp())
                    },
                    metadata=sub.metadata
                )


            if user_sub.plan_name == 'Free':
                current_app.logger.warning(
                    f"[Pause] User {user_id} is already on the free plan. No action needed for pausing."
                )
                return True

            # Calculate remaining days in current subscription
            now = datetime.utcnow()

            if user_sub.plan_expiration_timestamp:
                # Calculate remaining days from now until expiration
                remaining_days = max(0, (user_sub.plan_expiration_timestamp -
                                         now).days)
            else:
                # If no expiration date, assume monthly plan with remaining days
                days_since_start = (
                    now - user_sub.tier_start_timestamp
                ).days if user_sub.tier_start_timestamp else 0
                remaining_days = max(0, 30 -
                                     days_since_start)  # Assume 30-day cycle

            user_sub.plan_expiration_timestamp =  new_expiration_timestamp

            # Save original plan information before pausing
            user_sub.original_plan_id = user_sub.plan_id
            user_sub.original_plan_name = user_sub.plan_name
            user_sub.original_plan_days_remaining = remaining_days

            # Update subscription with pause information - INSTANT ACTIVATION
            user_sub.pause_status = 'active'
            user_sub.pause_start_date = now
            user_sub.pause_duration_days = pause_days
            user_sub.pause_end_date = pause_end_timestamp

            # Switch to free plan immediately
            free_plan = Plan.query.filter(
                func.lower(Plan.plan_name) == 'free').first()
            if free_plan:
                user_sub.plan_id = free_plan.plan_id
                user_sub.plan_name = free_plan.plan_name
                user_sub.credits_remaining = 0  # No credits during pause

            user.status = 'pause'
            user.tier = 'free'
            user_sub.is_paused = True

            db.session.commit()

            current_app.logger.info(
                f"[Pause] Successfully activated pause for user {user_id} instantly"
            )
            return True

        except Exception as e:
            current_app.logger.error(
                f"[Pause] Error processing pause subscription success: {str(e)}"
            )
            db.session.rollback()
            return False

    @staticmethod
    def _find_active_stripe_subscription(user, user_sub):
        """
        Reliably finds a user's active Stripe subscription.
        Priority 1: Uses the stored stripe_customer_id.
        Priority 2: Falls back to searching by user_id in metadata.
        """
        # Priority 1: Find via the stored customer ID (most reliable)
        if user_sub.stripe_customer_id:
            try:
                subscriptions = stripe.Subscription.list(
                    customer=user_sub.stripe_customer_id,
                    status='active',
                    limit=1
                )
                if subscriptions.data:
                    current_app.logger.info(f"Found active subscription via stripe_customer_id for user {user.user_id}")
                    return subscriptions.data[0]
            except Exception as e:
                current_app.logger.error(f"Error finding subscription by customer_id {user_sub.stripe_customer_id}: {e}")

        # Priority 2: Fallback to searching metadata (your existing logic)
        current_app.logger.info(f"Could not find subscription via customer_id. Falling back to metadata search for user {user.user_id}.")
        return SubscriptionController._find_active_stripe_subscription_by_user_id(user.user_id)
    

    @staticmethod
    def _find_active_stripe_subscription_by_user_id(user_id: str) -> Optional[stripe.Subscription]:
        try:
            query = f"status:'active' AND metadata['user_id']:'{user_id}'"
            res = stripe.Subscription.search(query=query)
            subscriptions = res.data
            if len(subscriptions) == 0:
                return None
            
            latest_timestamp = 0
            latest_sub = None
            # Find latest Stripe user's subscription by creation date
            for sub in subscriptions:
                if sub.created > latest_timestamp:
                    latest_timestamp = sub.created
                    latest_sub = sub
        
            return latest_sub            

        except Exception as e:
            current_app.logger.error(f"Error during retrieving Stripe user's subscriptions: {e}")
            return None

    @staticmethod
    def activate_pause_subscription(user_id):
        """
        Activate pause subscription 
        """
        try:
            current_app.logger.info(
                f"[Pause] Activating pause for user {user_id}")

            from models.user_subscription_model import UserSubscription
            from models.user_model import User
            from models.plan_model import Plan
            from datetime import datetime

            user = User.query.get(user_id)
            if not user:
                current_app.logger.error(f"[Pause] User {user_id} not found")
                return False

            user_sub = UserSubscription.query.filter_by(
                user_id=user_id).first()
            if not user_sub or user_sub.pause_status != 'pending':
                current_app.logger.error(
                    f"[Pause] Invalid pause status for user {user_id}")
                return False

            # Save original plan information
            if not user_sub.original_plan_id:
                user_sub.original_plan_id = user_sub.plan_id
            if not user_sub.original_plan_name:
                user_sub.original_plan_name = user_sub.plan_name

            # Downgrade to free tier
            free_plan = Plan.query.filter(
                func.lower(Plan.plan_name) == 'free').first()
            if free_plan:
                user_sub.plan_id = free_plan.plan_id
                user_sub.plan_name = free_plan.plan_name
                user_sub.credits_remaining = 0  # No credits during pause

            user.tier = 'free'
            user_sub.pause_status = 'active'

            db.session.commit()

            current_app.logger.info(
                f"[Pause] Successfully activated pause for user {user_id}")
            return True

        except Exception as e:
            current_app.logger.error(
                f"[Pause] Error activating pause: {str(e)}")
            db.session.rollback()
            return False

    @staticmethod
    def resume_subscription_early(user):
        """
        Resume subscription before the scheduled end date - instant resume with no refund
        """
        try:
            current_app.logger.info(
                f"[Resume] Early resume requested for user {user.user_id}")

            from models.user_subscription_model import UserSubscription
            from models.plan_model import Plan
            from datetime import datetime, timedelta

            user_sub = UserSubscription.query.filter_by(
                user_id=user.user_id).first()
            if not user_sub:
                current_app.logger.error(
                    f"[Resume] No subscription found for user {user.user_id}")
                return {'error': 'No subscription found'}, 404

            if not getattr(user_sub, 'pause_status',
                           None) or user_sub.pause_status not in ['active']:
                current_app.logger.error(
                    f"[Resume] Subscription not paused for user {user.user_id}"
                )
                return {'error': 'Subscription is not paused'}, 400

            # Restore original plan
            if user_sub.original_plan_id:
                original_plan = Plan.query.get(user_sub.original_plan_id)
                if original_plan:
                    user_sub.plan_id = user_sub.original_plan_id
                    user_sub.plan_name = user_sub.original_plan_name or original_plan.plan_name
                    user_sub.credits_remaining = original_plan.initial_credits or 0

                    # Calculate new expiration date with remaining days
                    now = datetime.utcnow()
                    if user_sub.original_plan_days_remaining:
                        user_sub.plan_expiration_timestamp = now + timedelta(
                            days=user_sub.original_plan_days_remaining)

                    # Update user tier based on original plan
                    plan_to_tier_mapping = {
                        'Bronze': 'bronze',
                        'Silver': 'silver',
                        'Gold': 'gold',
                        'Platinum': 'platinum',
                        'Bronze_Annual': 'bronze_annual',
                        'Silver_Annual': 'silver_annual',
                        'Gold_Annual': 'gold_annual',
                        'Platinum_Annual': 'platinum_annual',
                        'Student Semester': 'student_semester',
                        'Student Annual': 'student_annual',
                        'Pro Call Outreach': 'call_outreach',
                        'Student Monthly':'student_monthly'
                    }
                    
                    original_tier = plan_to_tier_mapping.get(original_plan.plan_name, 'free')
                    user.tier = original_tier
                    user.status = "active"
                    
                    current_app.logger.info(
                        f"[Resume] Restored user {user.user_id} to tier {original_tier} from plan {original_plan.plan_name}"
                    )
                else:
                    current_app.logger.error(
                        f"[Resume] Original plan not found for plan_id {user_sub.original_plan_id}"
                    )
            else:
                current_app.logger.warning(
                    f"[Resume] No original_plan_id found for user {user.user_id}"
                )
                    
                   

            # Reset pause fields
            user_sub.pause_status = 'completed'
            user_sub.is_paused = False
            user_sub.pause_end_date = None
            user_sub.original_plan_id = None
            user_sub.original_plan_name = None
            user_sub.original_plan_days_remaining = None

            db.session.commit()

            # Resume payment of Stripe user'subscription
            sub = SubscriptionController._find_active_stripe_subscription_by_user_id(user.user_id)
            if not sub:
                current_app.logger.error(
                    f"[Resume] Stripe subscription not found for User {user.user_id}."
                )
                raise Exception("Stripe subscription not found")
            
            stripe.Subscription.modify(
                sub.id,
                pause_collection=''
            )

            current_app.logger.info(
                f"[Resume] Successfully resumed subscription for user {user.user_id}"
            )
            return {
                'message':
                'Subscription resumed successfully. Note: Storage fees are non-refundable even with early resume.',
                'new_tier': user.tier,
                'credits_remaining': user_sub.credits_remaining,
                'plan_name': user_sub.plan_name
            }, 200

        except Exception as e:
            current_app.logger.error(
                f"[Resume] Error resuming subscription: {str(e)}")
            db.session.rollback()
            return {'error': 'Error resuming subscription'}, 500

    @staticmethod
    def auto_resume_subscription(user_id):
        """
        Automatically resume subscription after pause period ends
        """
        try:
            current_app.logger.info(
                f"[AutoResume] Auto resuming subscription for user {user_id}")

            from models.user_model import User
            user = User.query.get(user_id)
            if not user:
                return False

            return SubscriptionController.resume_subscription_early(
                user)[1] == 200

        except Exception as e:
            current_app.logger.error(
                f"[AutoResume] Error auto resuming subscription: {str(e)}")
            return False

    @staticmethod
    def check_and_restore_paused_subscriptions():
        """
        Check for expired pause subscriptions and restore them automatically
        """
        try:
            from models.user_subscription_model import UserSubscription
            from models.user_model import User
            from datetime import datetime

            current_app.logger.info(
                "[AutoResume] Checking for expired pause subscriptions")

            # Find all active paused subscriptions that have exceeded their pause period
            now = datetime.utcnow()
            expired_pauses = UserSubscription.query.filter(
                UserSubscription.pause_status == 'active',
                UserSubscription.pause_end_date <= now).all()

            for user_sub in expired_pauses:
                user = User.query.get(user_sub.user_id)
                if user:
                    current_app.logger.info(
                        f"[AutoResume] Auto-resuming subscription for user {user.user_id}"
                    )
                    result, status_code = SubscriptionController.resume_subscription_early(
                        user)
                    if status_code == 200:
                        current_app.logger.info(
                            f"[AutoResume] Successfully auto-resumed subscription for user {user.user_id}"
                        )
                    else:
                        current_app.logger.error(
                            f"[AutoResume] Failed to auto-resume subscription for user {user.user_id}: {result}"
                        )

            current_app.logger.info(
                f"[AutoResume] Processed {len(expired_pauses)} expired pause subscriptions"
            )
            return True

        except Exception as e:
            current_app.logger.error(
                f"[AutoResume] Error checking and restoring paused subscriptions: {str(e)}"
            )
            return False