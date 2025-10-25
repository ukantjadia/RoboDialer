from flask import Flask
import sys
import os
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to run script independently
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.user_model import User, db
from models.user_subscription_model import UserSubscription
from models.plan_model import Plan
from datetime import datetime, timedelta

def update_user_plan(username, email, new_tier):
    app = create_app()
    with app.app_context():
        try:
            # Find user by username and email
            user = User.query.filter_by(username=username, email=email).first()
            if not user:
                print(f"User '{username}' with email '{email}' not found!")
                return

            # Map tier to plan name
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
                'call_outreach': 'Pro Call Outreach',
                'free': 'Free'
            }
            mapped_plan_name = plan_name_mapping.get(new_tier.lower(), new_tier)
            plan = Plan.query.filter_by(plan_name=mapped_plan_name).first()
            if not plan:
                print(f"Plan '{mapped_plan_name}' not found in database. No changes made.")
                return

            # Update user tier
            user.tier = new_tier
            db.session.flush()

            # Update user subscription
            user_subscription = UserSubscription.query.filter_by(user_id=user.user_id).first()
            if not user_subscription:
                print(f"UserSubscription for user '{username}' not found! No changes made to subscription.")
                db.session.commit()
                return

            user_subscription.plan_id = plan.plan_id
            user_subscription.plan_name = plan.plan_name
            user_subscription.payment_frequency = plan.credit_reset_frequency if plan.credit_reset_frequency else 'monthly'
            user_subscription.credits_remaining = plan.initial_credits if plan.initial_credits is not None else 0
            user_subscription.tier_start_timestamp = datetime.utcnow()
            # Set expiration (example: 1 year for Gold, 30 days for Bronze/Silver/Free, else 30 days)
            tier_lower = new_tier.lower()
            if tier_lower == 'gold':
                user_subscription.plan_expiration_timestamp = datetime.utcnow() + timedelta(days=30)
            elif tier_lower in ['bronze', 'silver']:
                user_subscription.plan_expiration_timestamp = datetime.utcnow() + timedelta(days=30)
            elif tier_lower == 'free':
                user_subscription.plan_expiration_timestamp = datetime.utcnow() + timedelta(days=30)
            else:
                user_subscription.plan_expiration_timestamp = datetime.utcnow() + timedelta(days=30)
            user_subscription.username = user.username

            db.session.commit()
            print(f"User '{username}' updated successfully! New Tier: {new_tier}")
            print(f"  Username: {username}")
            print(f"  Email: {email}")
            print(f"  New Plan: {plan.plan_name}")
        except Exception as e:
            db.session.rollback()
            print(f"Error updating user '{username}': {str(e)}")

# def update_all():
#     """
#     Update a set of users with new tiers/plans.
#     You can adjust the users/tiers as needed.
#     """
#     users_to_update = [
#         # username, email, new_tier
#         # ('user', 'user@example.com', 'bronze'),
#         # ('student', 'student@example.com', 'silver'),
#         # ('user_123', 'user_123@example.com', 'free'),
#         # Add more users as needed
#     ]
#     for username, email, tier in users_to_update:
#         update_user_plan(username, email, tier)

# Directly call update_user_plan here. Edit these values as needed:
if __name__ == '__main__':
    # # Example usage:
    update_user_plan('lestersigauke', 'lestersigauke@gmail.com', 'bronze'),
    # update_user_plan('Kyungrok', 'krpark@g.ucla.edu', 'silver'),
    # update_user_plan('Angelo', 'angelo.sacco2002@gmail.com', 'bronze'),


    # update_user_plan('developer', 'developer@example.com', 'gold')
    # update_user_plan('admin', 'admin@example.com', 'gold')
    # update_user_plan('user', 'user@example.com', 'bronze')
    # update_user_plan('student', 'student@example.com', 'silver')
    # update_user_plan('user_123', 'user_123@example.com', 'free')
    # Add or modify calls as needed