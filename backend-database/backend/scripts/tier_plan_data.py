from flask import Flask
import sys
import os
from decimal import Decimal
import json

# Add parent directory to path to run script independently
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.plan_model import Plan
from models.lead_model import db  # Assuming db instance is accessible from lead_model
from sqlalchemy import text

plans_data = [
    {
        "plan_name":
        "Free",
        "description":
        "Basic access with limited leads and features",
        "monthly_price":
        Decimal('0.00'),
        "annual_price":
        Decimal('0.00'),
        "monthly_lead_quota":
        5,  # 60/year
        "annual_lead_quota":
        60,  # 5 * 12
        "cost_per_lead":
        Decimal('0.000'),
        "has_ai_features":
        False,
        "initial_credits":
        5,
        "credit_reset_frequency":
        "monthly",
        "features_json":
        json.dumps(
            ["Phase 1 Scraper Only", "No enrichment, no contact details"])
    },
    {
        "plan_name": "Bronze",
        "description": "Expanded access with more leads and basic features",
        "monthly_price": Decimal('19.00'),
        "annual_price": Decimal('199.00'),
        "monthly_lead_quota": 50,  # 600/year
        "annual_lead_quota": 600,  # 50 * 12
        "cost_per_lead": Decimal('0.333'),
        "has_ai_features": False,
        "initial_credits": 50,
        "credit_reset_frequency": "monthly",
        "features_json": json.dumps(["Basic Filters", "CSV Export"])
    },
    {
        "plan_name": "Bronze_Annual",
        "description":
        "Expanded access with more leads and basic features (Annual billing)",
        "monthly_price": Decimal('16.58'),  # 199/12
        "annual_price": Decimal('199.00'),
        "monthly_lead_quota": 50,  # 600/year
        "annual_lead_quota": 600,  # 50 * 12
        "cost_per_lead": Decimal('0.333'),
        "has_ai_features": False,
        "initial_credits": 600,  # Annual credits upfront
        "credit_reset_frequency": "annual",
        "features_json": json.dumps(["Basic Filters", "CSV Export"])
    },
    {
        "plan_name": "Silver",
        "description": "More leads and advanced contact features",
        "monthly_price": Decimal('49.00'),
        "annual_price": Decimal('499.00'),
        "monthly_lead_quota": 125,  # 1500/year
        "annual_lead_quota": 1500,  # 125 * 12
        "cost_per_lead": Decimal('0.333'),
        "has_ai_features": False,
        "initial_credits": 125,
        "credit_reset_frequency": "monthly",
        "features_json": json.dumps(["Phone Numbers", "Advanced Features"])
    },
    {
        "plan_name": "Gold",
        "description": "High volume leads and AI features",
        "monthly_price": Decimal('99.00'),
        "annual_price": Decimal('999.00'),
        "monthly_lead_quota": 292,  # 3500/year
        "annual_lead_quota": 3504,  # 292 * 12
        "cost_per_lead": Decimal('0.285'),
        "has_ai_features": True,
        "initial_credits": 292,
        "credit_reset_frequency": "monthly",
        "features_json": json.dumps(["Email Writing AI", "Priority Support"])
    },
    {
        "plan_name":
        "Platinum",
        "description":
        "Unlimited leads and custom workflows",
        "monthly_price":
        Decimal('199.00'),
        "annual_price":
        Decimal('1999.00'),
        "monthly_lead_quota":
        None,  # Unlimited
        "annual_lead_quota":
        None,  # Unlimited
        "cost_per_lead":
        None,  # Not applicable
        "has_ai_features":
        True,
        "initial_credits":
        None,  # Unlimited
        "credit_reset_frequency":
        "monthly",
        "features_json":
        json.dumps(
            ["Unlimited Credits", "Custom Workflows", "Priority Support"])
    },
    {
        "plan_name":
        "Enterprise",
        "description":
        "Custom pricing and features for large organizations",
        "monthly_price":
        None,  # Custom
        "annual_price":
        None,  # Custom
        "monthly_lead_quota":
        None,  # Custom
        "annual_lead_quota":
        None,  # Custom
        "cost_per_lead":
        None,  # Custom
        "has_ai_features":
        True,
        "initial_credits":
        None,  # Custom
        "credit_reset_frequency":
        "custom",
        "features_json":
        json.dumps(
            ["Custom Credits/Year", "Custom Workflows", "Tailored Features"])
    },
    {
        "plan_name": "Pause",
        "description": "Temporary pause with limited access",
        "monthly_price": Decimal('10.00'),
        "annual_price": Decimal('10.00'),
        "monthly_lead_quota": 0,
        "annual_lead_quota": 0,
        "cost_per_lead": None,
        "has_ai_features": False,
        "initial_credits": 0,
        "credit_reset_frequency": "monthly",
        "features_json": json.dumps(["Basic Filters Only", "No Credits", "Limited Access"])
    }
]


def seed_plans():
    """Updates existing plans and inserts new ones, without deleting or changing plan_id."""
    app = create_app()
    with app.app_context():
        print("Altering plans table to allow NULL for initial_credits...")
        try:
            db.session.execute(
                text(
                    'ALTER TABLE plans ALTER COLUMN initial_credits DROP NOT NULL;'
                ))
            db.session.execute(
                text(
                    'ALTER TABLE plans ALTER COLUMN initial_credits DROP NOT NULL;'
                ))
            db.session.execute(
                text(
                    'ALTER TABLE plans ALTER COLUMN monthly_price DROP NOT NULL;'
                ))
            db.session.commit()
        except Exception as e:
            print(
                f"Warning: Could not alter table (maybe already nullable): {e}"
            )
            db.session.rollback()
        print("Updating/inserting plans table...")
        for plan_data in plans_data:
            existing_plan = Plan.query.filter_by(
                plan_name=plan_data['plan_name']).first()
            if existing_plan:
                # Update all fields except plan_id
                for key, value in plan_data.items():
                    if key != 'plan_id':
                        setattr(existing_plan, key, value)
                print(f"Updated plan: {plan_data['plan_name']}")
            else:
                plan = Plan(**plan_data)
                db.session.add(plan)
                print(f"Added plan: {plan_data['plan_name']}")
        try:
            db.session.commit()
            print("Plans update/insert complete.")
        except Exception as e:
            db.session.rollback()
            print(f"Error saving plans: {str(e)}")


if __name__ == '__main__':
    seed_plans()
