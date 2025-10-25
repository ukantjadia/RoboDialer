
"""
Script to create a Pause plan in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.lead_model import db
from models.plan_model import Plan

def create_pause_plan():
    """Create a Pause plan in the database"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if Pause plan already exists
            existing_pause_plan = Plan.query.filter_by(plan_name='Pause').first()
            
            if existing_pause_plan:
                print("Pause plan already exists")
                return
            
            # Create the Pause plan
            pause_plan = Plan(
                plan_name='Pause',
                initial_credits=0,
                cost_per_lead=0.00,
                features_json='{"access": "limited", "type": "pause"}',
                credit_reset_frequency='monthly'
            )
            
            db.session.add(pause_plan)
            db.session.commit()
            
            print(f"Successfully created Pause plan with ID: {pause_plan.plan_id}")
            
        except Exception as e:
            print(f"Error creating Pause plan: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    create_pause_plan()
