from typing import Dict, Optional, Union
import stripe
from flask import current_app
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from utils.stripe_utils import get_end_coupon_timestamp
from models.last_coupon_by_user_model import LastCouponByUser
from models.lead_model import db
from sqlalchemy.dialects.postgresql import insert

class CouponController:

    @staticmethod
    def get_all_promo_codes() -> list[stripe.PromotionCode]:
        try:
            res = stripe.PromotionCode.list()
            promotion_codes = res.data
            formatted_dt_promo_codes = []
            for promo_code in promotion_codes:
                promo_code.expires_at = CouponController._format_timestamp_to_datetime(promo_code.expires_at)
                formatted_dt_promo_codes.append(promo_code)
            return formatted_dt_promo_codes
        except Exception as e:
            current_app.logger.error(f"Error retrieving promotion codes from Stripe")
            return []

    
    # Use this first to get user_id associated with discount
    @staticmethod
    def get_all_invoices_with_discount():
        invoices_with_discounts = []

        # Get invoices in batches of 100
        has_more = True
        starting_after = None

        while has_more:
            try:
                invoice_batch = stripe.Invoice.list(
                    status='paid',
                    starting_after=starting_after,
                    expand=['data.discounts', 'data.discounts.promotion_code']
                )
                
                # Filter invoices with discounts
                for invoice in invoice_batch.data:
                    if invoice.discounts:
                        # Check if any discount uses a promotion code
                        for discount in invoice.discounts:
                            if hasattr(discount, 'promotion_code') and discount.promotion_code:
                                invoice_parent_metadata = invoice.parent.subscription_details.metadata
                                end_timestamp = get_end_coupon_timestamp(discount.start, discount.coupon.duration, discount.coupon.duration_in_months)
                                invoices_with_discounts.append({
                                    'promotion_code': discount.promotion_code.code,
                                    'amount_off': discount.coupon.amount_off,
                                    'percent_off': discount.coupon.percent_off,
                                    'discount_id': discount.id,
                                    'user_id': invoice_parent_metadata.get('user_id', None),
                                    'coupon_id': discount.coupon.id ,
                                    'end_timestamp': end_timestamp,
                                    'invoice_id': invoice.id,
                                    'subscription_id': invoice.parent.subscription_details.subscription,
                                    'currency':discount.coupon.currency,
                                    'livemode': invoice.livemode,
                                    'start_timestamp':discount.start
                                })
                                break
                # Prepare for next batch if there are more
                has_more = invoice_batch.has_more
                if has_more and invoice_batch.data:
                    starting_after = invoice_batch.data[-1].id
            except Exception as e:
                current_app.logger.error("Error when retrieving invoices with discount data")

        return invoices_with_discounts

    # In future if we want to get whether user has applied coupon, we do this to get faster result
    @staticmethod
    def get_all_subscriptions_with_metadata_discount():
        subscriptions_metadata_discounts = []

        has_more = True
        query = "status:'active' AND metadata['is_discounted']:'true'"
        subscription_batch = stripe.Subscription.search(
            query=query,
            limit=100
        )

        page = subscription_batch

        while has_more:
            try:
                for subscription in page.data:
                    subscriptions_metadata_discounts.append(subscription.metadata)

                if page.has_more:
                    page = stripe.Subscription.search(
                        query=query,
                        limit=100,
                        page=page.next_page

                    )
                else:
                    has_more = False

            except Exception as e:
                current_app.logger.error("Error when retrieving invoices with discount data")

        return subscriptions_metadata_discounts

    @staticmethod
    def _format_timestamp_to_datetime(timestamp:int) -> Optional[str]:
        if timestamp:
            return datetime.fromtimestamp(timestamp).strftime('%b %d, %Y %I:%M %p')
        return None
    
    @staticmethod
    def sync_stripe_coupon_usage_with_db():
        invoices = CouponController.get_all_invoices_with_discount()
        latest_discounts = {}
        for item in invoices:
            user_id = item['user_id']
            end_timestamp = item['end_timestamp']
            if user_id not in latest_discounts or end_timestamp > latest_discounts[user_id]['end_timestamp']:
                latest_discounts[user_id] = item

        latest_discounts_list = list(latest_discounts.values())
        current_app.logger.info(f"Preparing to sync {len(latest_discounts_list)} latest coupon usages to database.")

        if not latest_discounts_list:
            current_app.logger.info("No new coupon usages to sync. Exiting.")
            return

        try:
            # Step 2: Prepare data for the bulk upsert
            prepared_data = []
            for discount in latest_discounts_list:
                # Convert timestamps to timezone-aware datetime objects for PostgreSQL
                expires_at = datetime.fromtimestamp(discount['end_timestamp']) if discount['end_timestamp'] else None
                applied_at = datetime.fromtimestamp(discount['start_timestamp']) if discount['start_timestamp'] else None
                
                prepared_data.append({
                    'user_id': discount['user_id'],
                    'stripe_coupon_id': discount['coupon_id'],
                    'currency': discount['currency'],
                    'amount_off': discount['amount_off'],
                    'percent_off': discount['percent_off'],
                    'promo_code': discount['promotion_code'],
                    'stripe_subscription_id': discount['subscription_id'],
                    'stripe_invoice_id': discount['invoice_id'],
                    'livemode': discount['livemode'],
                    'expires_at': expires_at,
                    'applied_at': applied_at,
                })

            # Step 3: Construct and execute the bulk upsert statement
            # Use the PostgreSQL dialect for the ON CONFLICT clause
            insert_stmt = insert(LastCouponByUser).values(prepared_data)
            
            # The on_conflict_do_update clause is based on the 'user_id' unique column
            on_conflict_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['user_id'],
                # 'excluded' refers to the values of the row that was just attempted to be inserted
                set_=dict(
                    stripe_coupon_id=insert_stmt.excluded.stripe_coupon_id,
                    currency=insert_stmt.excluded.currency,
                    amount_off=insert_stmt.excluded.amount_off,
                    percent_off=insert_stmt.excluded.percent_off,
                    promo_code=insert_stmt.excluded.promo_code,
                    stripe_subscription_id=insert_stmt.excluded.stripe_subscription_id,
                    stripe_invoice_id=insert_stmt.excluded.stripe_invoice_id,
                    livemode=insert_stmt.excluded.livemode,
                    expires_at=insert_stmt.excluded.expires_at,
                    applied_at=insert_stmt.excluded.applied_at
                )
            )
            
            # Execute the statement
            db.session.execute(on_conflict_stmt)
            db.session.commit()
            
            current_app.logger.info(f"Successfully synced {len(latest_discounts_list)} records to database.")

        except Exception as e:
            db.session.rollback()  # Rollback transaction on error to prevent partial writes
            current_app.logger.error(f"Error during coupon usage sync: {e}")
            raise e


    @staticmethod
    def apply_promo_code_to_user_subscription(user_id:str, code:str) -> Dict[str, Union[bool, str]]:
        promo_code = CouponController._find_active_promo_code(code)
        if not promo_code:
            current_app.logger.info(f"Not found promo code on Stripe: {code}")
            return {
                "success": False,
                "error": "Not found promo code on Stripe"
            }
        
        user_sub = CouponController._find_active_subscription_by_user_id(user_id)
        if not user_sub:
            current_app.logger.info(f"Not found user's subscription with user_id: {user_id}")
            return {
                "success": False,
                "error": "Not found user's subscription based on user_id"
            }
        
        try:
            updated_subscription = stripe.Subscription.modify(
                id=user_sub.id,
                discounts=[
                    {"promotion_code": promo_code.id}
                ]
            )
            
            coupon = promo_code.coupon
            expires_at = get_end_coupon_timestamp(
                int(datetime.now().timestamp()), 
                coupon.duration, 
                coupon.duration_in_months
            )

            data_to_upsert = {
                'user_id': user_id,
                'stripe_coupon_id': coupon.id,
                'currency': coupon.currency,
                'amount_off': coupon.amount_off,
                'percent_off': coupon.percent_off,
                'promo_code': promo_code.code,
                'stripe_subscription_id': updated_subscription.id,
                'stripe_invoice_id': updated_subscription.latest_invoice, \
                'livemode': promo_code.livemode,
                'expires_at': datetime.fromtimestamp(expires_at) if expires_at else None,
                'applied_at': datetime.now(timezone.utc),
            }

            insert_stmt = insert(LastCouponByUser).values(data_to_upsert)
            on_conflict_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['user_id'],
                set_=data_to_upsert
            )
            db.session.execute(on_conflict_stmt)
            db.session.commit()
            
            current_app.logger.info(f"Successfully applied promo code '{code}' and synced DB for user {user_id}.")

            return {
                "success": True,
                "error": ""
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error when trying to apply promo code {code}  to user's subscription with user_id {user_id}: {e}")
            return {
                "success": False,
                "error": f"Error when trying to apply promo code: {str(e)}"
            }

    @staticmethod
    def _find_active_promo_code(code:str) -> Optional[stripe.PromotionCode]:
        try:
            res = stripe.PromotionCode.list(code=code, active=True)
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            current_app.logger.error(f"Error during searching Stripe promo code: {e}")
            return None
        
    @staticmethod
    def _find_active_subscription_by_user_id(user_id:str) -> Optional[stripe.Subscription]:
        try:
            query = f"status:'active' AND metadata['user_id']:'{user_id}'"
            res = stripe.Subscription.search(query=query, limit=1)
            if res.data:
                return res.data[0]
            return None
        except Exception as e:
            current_app.logger.error(f"Error during retrieving Stripe user's subscriptions: {e}")
            return None
