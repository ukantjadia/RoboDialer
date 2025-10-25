import sys
import os
from sqlalchemy import text

# Add parent directory to path to run script independently
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.lead_model import db


def add_pause_subscription_fields():
    """Add pause subscription fields to user_subscriptions table"""
    app = create_app()
    with app.app_context():
        try:
            # Add new columns for pause subscription functionality
            sql_commands = [
                # Add pause status enum
                """ALTER TABLE user_subscriptions 
                ADD COLUMN IF NOT EXISTS pause_status VARCHAR(20) DEFAULT 'none' CHECK (pause_status IN ('none', 'pending', 'active', 'completed'))""",

                # Add pause start date
                """ALTER TABLE user_subscriptions 
                ADD COLUMN IF NOT EXISTS pause_start_date TIMESTAMP""",

                # Add pause duration in days
                """ALTER TABLE user_subscriptions 
                ADD COLUMN IF NOT EXISTS pause_duration_days INTEGER""",

                # Add original plan days remaining
                """ALTER TABLE user_subscriptions 
                ADD COLUMN IF NOT EXISTS original_plan_days_remaining INTEGER""",

                # Add storage subscription ID
                """ALTER TABLE user_subscriptions 
                ADD COLUMN IF NOT EXISTS storage_subscription_id VARCHAR(255)""",

                # Add resume schedule ID
                """ALTER TABLE user_subscriptions 
                ADD COLUMN IF NOT EXISTS resume_schedule_id VARCHAR(255)"""
            ]

            for sql in sql_commands:
                db.session.execute(text(sql))

            db.session.commit()
            print(
                "Successfully added pause subscription fields to user_subscriptions table"
            )

        except Exception as e:
            db.session.rollback()
            print(f"Error adding pause subscription fields: {str(e)}")


if __name__ == '__main__':
    add_pause_subscription_fields()
