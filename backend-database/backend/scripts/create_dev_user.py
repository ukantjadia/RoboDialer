from flask import Flask
import sys
import os

# Add parent directory to path to run script independently
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.user_model import User, db
from models.user_subscription_model import UserSubscription
from models.plan_model import Plan
from datetime import datetime, timedelta

def create_user_with_subscription(username, email, password, role, tier):
    app = create_app()
    with app.app_context():
        try:
            # Check if user already exists
            user = User.query.filter_by(username=username).first()
            if user:
                print(f"User '{username}' already exists!")
                return

            # Create user
            user = User(
                username=username,
                email=email,
                role=role,
                tier=tier,
                is_email_verified=True
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # To get user_id

            # Use the same mapping as in your subscription_controller.py
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
            mapped_plan_name = plan_name_mapping.get(tier.lower(), tier)
            plan = Plan.query.filter_by(plan_name=mapped_plan_name).first()
            if not plan:
                print(f"Plan '{mapped_plan_name}' not found in database. User will be created without subscription.")
                db.session.commit()
                return

            # Set up subscription
            tier_start = datetime.utcnow()
            if tier.lower() == 'gold':
                # Example: 1 year for Gold
                tier_expiration = tier_start + timedelta(days=365)
            else:
                # Example: 30 days for Free
                tier_expiration = tier_start + timedelta(days=30)

            user_subscription = UserSubscription(
                user_id=user.user_id,
                plan_id=plan.plan_id,
                plan_name=plan.plan_name,
                payment_frequency=plan.credit_reset_frequency if plan.credit_reset_frequency else 'monthly',
                credits_remaining=plan.initial_credits if plan.initial_credits is not None else 0,
                tier_start_timestamp=tier_start,
                plan_expiration_timestamp=tier_expiration,
                username=user.username
            )
            db.session.add(user_subscription)
            db.session.commit()
            print(f"User '{username}' created successfully! Role: {role}, Tier: {tier}")
            print(f"  Username: {username}")
            print(f"  Password: {password}")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user '{username}': {str(e)}")

def create_all():
    """
    Create a set of users with different roles and tiers.
    You can adjust the users/roles/tiers as needed.
    """
    users_to_create = [
        # username, email, password, role, tier
        ('developer', 'developer@example.com', 'developer123', 'developer', 'gold'),
        ('admin', 'admin@example.com', 'admin123', 'admin', 'gold'),
        ('user', 'user@example.com', 'user123', 'user', 'free'),
        ('student', 'student@example.com', 'student123', 'student', 'free'),
        ('user_123', 'user_123@example.com', 'student123', 'student', 'free'),
        # Add more users as needed
    ]
    for username, email, password, role, tier in users_to_create:
        create_user_with_subscription(username, email, password, role, tier)

if __name__ == '__main__':
    create_all()