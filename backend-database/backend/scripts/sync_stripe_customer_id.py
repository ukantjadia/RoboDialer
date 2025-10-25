import os
import sys
import stripe
from datetime import datetime

# Add parent directory to path to run script independently
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  
from models.user_subscription_model import UserSubscription
from models.lead_model import db

def _find_latest_active_subscription(user_id: str):
    """
    Searches Stripe for the most recent active subscription for a given user_id in metadata.
    """
    try:
        query = f"status:'active' AND metadata['user_id']:'{user_id}'"
        
        subscriptions = stripe.Subscription.search(query=query, limit=10)
        
        latest_sub = None
        latest_timestamp = 0

        for sub in subscriptions.auto_paging_iter():
            if sub.created > latest_timestamp:
                latest_timestamp = sub.created
                latest_sub = sub
        
        return latest_sub

    except Exception as e:
        print(f"  - Stripe API error for user {user_id}: {e}")
        return None

def sync_missing_customer_ids():
    """
    Finds user subscriptions missing a Stripe Customer ID and backfills it
    by searching Stripe's API.
    """
    app = create_app()
    with app.app_context():
        print("Starting sync process for missing Stripe Customer IDs...")
        
        subs_to_fix = UserSubscription.query.filter(
            UserSubscription.stripe_customer_id == None,
            UserSubscription.plan_id != 1
        ).all()

        if not subs_to_fix:
            print("No subscriptions found that require a customer ID sync. All records are up to date.")
            return

        print(f"Found {len(subs_to_fix)} user subscriptions to process.")
        
        updated_count = 0
        not_found_count = 0

        for user_sub in subs_to_fix:
            print(f"Processing User ID: {user_sub.user_id}...")
            
            stripe_sub = _find_latest_active_subscription(str(user_sub.user_id))
            
            if stripe_sub and stripe_sub.customer:
            
                user_sub.stripe_customer_id = stripe_sub.customer
                print(f"  -> Found Stripe Customer ID: {stripe_sub.customer}. Staging for update.")
                updated_count += 1
            else:
                print(f"  -> WARNING: No active Stripe subscription found for user {user_sub.user_id}.")
                not_found_count += 1
        
        if updated_count > 0:
            print(f"\nCommitting {updated_count} updates to the database...")
            try:
                db.session.commit()
                print("Database successfully updated.")
            except Exception as e:
                db.session.rollback()
                print(f"DATABASE ERROR: Failed to commit changes. All updates have been rolled back. Reason: {e}")
        else:
            print("\nNo records were updated.")

        print("\n--- Sync Summary ---")
        print(f"Total subscriptions checked: {len(subs_to_fix)}")
        print(f"Successfully updated: {updated_count}")
        print(f"Not found in Stripe: {not_found_count}")

if __name__ == '__main__':
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    if not stripe.api_key:
        raise ValueError("STRIPE_SECRET_KEY environment variable not set.")
        
    sync_missing_customer_ids()