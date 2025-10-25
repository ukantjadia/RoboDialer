#!/usr/bin/env python3
"""
Test script to create a sample agent for testing the RoboDialer
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.lead_model import db
from models.cold_call_agent_model import Agent
from datetime import datetime

def create_test_agent():
    """Create a sample agent for testing"""
    
    try:
        # Check if an agent already exists
        existing_agent = Agent.query.first()
        if existing_agent:
            print(f"Agent already exists: {existing_agent.name} (ID: {existing_agent.id})")
            return
        
        # Create a test agent
        test_agent = Agent(
            name="John Doe",
            email="john.doe@example.com",
            phone="+1-555-0199",
            status="active",
            is_available=True,
            total_calls=0,
            successful_calls=0,
            max_concurrent_calls=1,
            score_given=4.5
        )
        
        db.session.add(test_agent)
        db.session.commit()
        print(f"Created test agent: {test_agent.name} (ID: {test_agent.id})")
        
    except Exception as e:
        print(f"Error creating test agent: {e}")
        db.session.rollback()

if __name__ == "__main__":
    # Import the app to get the application context
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from app import create_app
    
    app = create_app()
    with app.app_context():
        create_test_agent()