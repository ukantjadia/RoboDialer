from flask import Flask
import sys
import os

# Add parent directory to path to run script independently
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.lead_model import db
from sqlalchemy import text


def add_original_plan_id_field():
    app = create_app()
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(
                text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='user_subscriptions' 
                AND column_name='original_plan_id'
            """))

            if result.fetchone():
                print("✅ original_plan_id column already exists")
                return

            # Add the column
            db.session.execute(
                text("""
                ALTER TABLE user_subscriptions 
                ADD COLUMN original_plan_id INTEGER
            """))

            db.session.commit()
            print(
                "✅ Successfully added original_plan_id column to user_subscriptions table"
            )

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding original_plan_id column: {str(e)}")


if __name__ == '__main__':
    add_original_plan_id_field()
