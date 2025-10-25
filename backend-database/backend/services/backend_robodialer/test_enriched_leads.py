#!/usr/bin/env python3
"""
Test script to create sample enriched leads data for testing the RoboDialer
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.lead_model import db
from models.user_lead_drafts_model import UserLeadDraft
from models.user_model import User
from models import Lead
import uuid
from datetime import datetime

def create_test_data():
    """Create sample enriched leads for testing"""
    
    try:
        # Create a test user if none exists
        test_user = User.query.first()
        if not test_user:
            print("No users found in database. Creating test user...")
            test_user = User(
                username="testuser",
                email="test@example.com",
                is_active=True,
                created_at=datetime.now()
            )
            db.session.add(test_user)
            db.session.commit()
            print(f"Created test user: {test_user.user_id}")
        else:
            print(f"Using existing user: {test_user.user_id}")
        
        # Use a dummy lead_id since we're just testing the enriched leads functionality
        test_lead_id = "test_lead_001"
        
        # Create sample enriched lead drafts
        sample_drafts = [
            {
                "company": "Tech Innovators Inc",
                "companyPhone": "+1-555-0123",
                "contactPerson": "John Smith",
                "contact_name": "John Smith",
                "industry": "Software",
                "revenue": "$2M-5M",
                "employees": "25-50",
                "city": "San Francisco",
                "state": "CA",
                "website": "https://techinnovators.com"
            },
            {
                "company": "Digital Solutions LLC",
                "companyPhone": "+1-555-0456",
                "contactPerson": "Sarah Johnson",
                "contact_name": "Sarah Johnson",
                "industry": "Digital Marketing",
                "revenue": "$1M-2M",
                "employees": "10-25",
                "city": "Austin",
                "state": "TX",
                "website": "https://digitalsolutions.com"
            },
            {
                "company": "Cloud Services Pro",
                "companyPhone": "+1-555-0789",
                "contactPerson": "Mike Davis",
                "contact_name": "Mike Davis",
                "industry": "Cloud Computing",
                "revenue": "$5M-10M",
                "employees": "100-200",
                "city": "Seattle",
                "state": "WA",
                "website": "https://cloudservicespro.com"
            }
        ]
        
        created_count = 0
        for draft_data in sample_drafts:
            # Check if a draft with this company already exists
            existing = UserLeadDraft.query.filter(
                UserLeadDraft.draft_data['company'].astext == draft_data['company']
            ).first()
            
            if not existing:
                draft = UserLeadDraft(
                    user_id=test_user.user_id,
                    lead_id=test_lead_id,  # Use dummy lead_id
                    draft_data=draft_data,
                    status='pending',
                    phase='approved',
                    change_summary=f"Test enriched lead data for {draft_data['company']}"
                )
                db.session.add(draft)
                created_count += 1
                print(f"Created draft for: {draft_data['company']}")
            else:
                print(f"Draft already exists for: {draft_data['company']}")
        
        if created_count > 0:
            db.session.commit()
            print(f"\nSuccessfully created {created_count} enriched lead drafts!")
        else:
            print("\nNo new drafts created - all test data already exists.")
            
        # Verify the data
        total_drafts = UserLeadDraft.query.filter_by(is_deleted=False).count()
        print(f"Total enriched lead drafts in database: {total_drafts}")
        
    except Exception as e:
        print(f"Error creating test data: {e}")
        db.session.rollback()

if __name__ == "__main__":
    # Import the app to get the application context
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from app import create_app
    
    app = create_app()
    with app.app_context():
        create_test_data()