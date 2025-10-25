#!/usr/bin/env python3
"""
Database initialization script to create tables and sample data for RoboDialer
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.lead_model import db
from models.cold_call_agent_model import Agent
from models.cold_call_log_model import CallLog
from datetime import datetime

def init_database():
    """Initialize database tables and create sample data"""
    
    try:
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        print("Tables created successfully!")
        
        # Check if agents already exist
        existing_agents = Agent.query.count()
        if existing_agents > 0:
            print(f"Database already has {existing_agents} agents. Skipping agent creation.")
            return
        
        # Create sample agents
        sample_agents = [
            {
                "name": "Alex Johnson",
                "email": "alex.johnson@company.com",
                "phone": "+1-555-0101",
                "status": "active",
                "is_available": True,
                "total_calls": 45,
                "successful_calls": 38,
                "max_concurrent_calls": 2
            },
            {
                "name": "Sarah Chen",
                "email": "sarah.chen@company.com", 
                "phone": "+1-555-0102",
                "status": "active",
                "is_available": True,
                "total_calls": 52,
                "successful_calls": 41,
                "max_concurrent_calls": 1
            },
            {
                "name": "Mike Rodriguez",
                "email": "mike.rodriguez@company.com",
                "phone": "+1-555-0103", 
                "status": "on_break",
                "is_available": False,
                "total_calls": 38,
                "successful_calls": 29,
                "max_concurrent_calls": 1
            },
            {
                "name": "Emma Wilson",
                "email": "emma.wilson@company.com",
                "phone": "+1-555-0104",
                "status": "active", 
                "is_available": True,
                "total_calls": 63,
                "successful_calls": 55,
                "max_concurrent_calls": 3
            }
        ]
        
        created_count = 0
        for agent_data in sample_agents:
            # Check if agent with this email already exists
            existing = Agent.query.filter_by(email=agent_data['email']).first()
            
            if not existing:
                agent = Agent(
                    name=agent_data['name'],
                    email=agent_data['email'],
                    phone=agent_data['phone'],
                    status=agent_data['status'],
                    is_available=agent_data['is_available'],
                    total_calls=agent_data['total_calls'],
                    successful_calls=agent_data['successful_calls'],
                    max_concurrent_calls=agent_data['max_concurrent_calls'],
                    created_at=datetime.utcnow()
                )
                db.session.add(agent)
                created_count += 1
                print(f"Created agent: {agent_data['name']}")
            else:
                print(f"Agent already exists: {agent_data['name']}")
        
        if created_count > 0:
            db.session.commit()
            print(f"\nSuccessfully created {created_count} sample agents!")
        else:
            print("\nNo new agents created - all sample data already exists.")
            
        # Verify the data
        total_agents = Agent.query.count()
        print(f"Total agents in database: {total_agents}")
        
        # Show agent details
        agents = Agent.query.all()
        print("\nAgent List:")
        for agent in agents:
            print(f"  - {agent.name} ({agent.email}) - Status: {agent.status}")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    # Import the app to get the application context
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from app import create_app
    
    app = create_app()
    with app.app_context():
        init_database()