#!/usr/bin/env python3
"""
Test script to verify call log creation and database connection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models.lead_model import db
from models.cold_call_log_model import CallLog
from models.cold_call_agent_model import Agent
from datetime import datetime
import requests
import json

def test_database_connection():
    """Test basic database connectivity"""
    with app.app_context():
        try:
            # Test if we can query the database
            agent_count = Agent.query.count()
            call_log_count = CallLog.query.count()
            print(f"✅ Database connected successfully!")
            print(f"   - Agents in database: {agent_count}")
            print(f"   - Call logs in database: {call_log_count}")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

def test_call_log_creation():
    """Test creating a call log entry"""
    with app.app_context():
        try:
            # Find an existing agent
            agent = Agent.query.first()
            if not agent:
                print("❌ No agent found in database. Creating a test agent...")
                agent = Agent(
                    name="Test Agent",
                    email="test@example.com",
                    phone="+1234567890",
                    status="available"
                )
                db.session.add(agent)
                db.session.commit()
                print(f"✅ Created test agent with ID: {agent.id}")
            
            # Create a test call log
            test_call_log = CallLog(
                agent_id=agent.id,
                phone_number="+919141017165",
                direction="outgoing",
                status="failed",
                action_taken="call",
                contact_name="Test Contact",
                started_at=datetime.now(),
                ended_at=datetime.now(),
                duration=0,
                notes="Test failed call for debugging",
                follow_up_required=False,
                call_attempt_number=1
            )
            
            db.session.add(test_call_log)
            db.session.commit()
            
            print(f"✅ Test call log created successfully!")
            print(f"   - Call Log ID: {test_call_log.id}")
            print(f"   - Agent ID: {test_call_log.agent_id}")
            print(f"   - Phone: {test_call_log.phone_number}")
            print(f"   - Status: {test_call_log.status}")
            
            return test_call_log
            
        except Exception as e:
            print(f"❌ Failed to create call log: {e}")
            db.session.rollback()
            return None

def test_api_call_log_creation():
    """Test creating call log via API"""
    try:
        # Test data for failed call
        test_data = {
            "agent_id": 1,  # Assuming agent 1 exists
            "phone_number": "+919141017165",
            "direction": "outgoing",
            "status": "failed",
            "action_taken": "call",
            "contact_name": "API Test Contact",
            "started_at": datetime.now().isoformat(),
            "ended_at": datetime.now().isoformat(),
            "duration": 0,
            "notes": "API test failed call for debugging",
            "follow_up_required": False,
            "call_attempt_number": 1
        }
        
        response = requests.post(
            "http://localhost:8000/api/v1/call_logs",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ API call log creation successful!")
            print(f"   - Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"   - Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def main():
    print("🔍 Testing Call Log Creation...")
    print("=" * 50)
    
    # Test 1: Database connection
    if not test_database_connection():
        return
    
    print("\n" + "=" * 50)
    
    # Test 2: Direct database call log creation
    print("🧪 Testing direct database call log creation...")
    call_log = test_call_log_creation()
    
    print("\n" + "=" * 50)
    
    # Test 3: API call log creation
    print("🧪 Testing API call log creation...")
    test_api_call_log_creation()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")

if __name__ == "__main__":
    main()