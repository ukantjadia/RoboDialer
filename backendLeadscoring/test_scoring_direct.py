#!/usr/bin/env python3
"""
Direct test of the lead scoring system without server
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.data import mock_leads
from app.services.ml_service import MLService

async def test_scoring():
    print("🚀 TESTING YOUR LEAD SCORING SYSTEM")
    print("=" * 50)
    
    # Initialize ML service
    ml_service = MLService()
    
    # Test preferences
    preferences = {
        "industry": "Technology",
        "min_employees": 0,
        "max_employees": 1000,
        "min_revenue": 0,
        "max_revenue": 100000000,
        "target_revenue": 25000000,
        "target_employees": 50,
        "keywords": "AI, automation, software"
    }
    
    print(f"📊 Processing {len(mock_leads)} leads...")
    print(f"🎯 Preferences: {preferences}")
    print()
    
    try:
        # Score all leads
        scored_results = await ml_service.recommend_leads(mock_leads, preferences, top_n=10)
        
        print(f"✅ Successfully scored {len(scored_results)} leads!")
        print()
        
        # Display top results
        print("🏆 TOP 10 SCORED LEADS:")
        print("-" * 80)
        
        for i, result in enumerate(scored_results, 1):
            # Handle different result formats
            if isinstance(result, dict):
                if 'lead' in result:
                    lead = result['lead']
                    score = result.get('score', 0)
                    explanation = result.get('explanation', 'No explanation available')
                else:
                    # Direct lead data
                    lead = result
                    score = result.get('score', 0)
                    explanation = result.get('explanation', 'No explanation available')
            else:
                lead = result
                score = getattr(result, 'score', 0)
                explanation = getattr(result, 'explanation', 'No explanation available')
            
            print(f"{i:2d}. {lead['name']:<25} | Score: {score:5.1f} | Industry: {lead['industry']}")
            print(f"    Location: {lead['city']}, {lead['state']} | Revenue: {lead['revenue']} | Employees: {lead['employees']}")
            print(f"    Explanation: {explanation}")
            print()
        
        # Test different industries
        print("🔍 TESTING DIFFERENT INDUSTRIES:")
        print("-" * 40)
        
        industries = ["Technology", "Healthcare", "Finance", "Education"]
        
        for industry in industries:
            industry_prefs = preferences.copy()
            industry_prefs["industry"] = industry
            
            try:
                results = await ml_service.recommend_leads(mock_leads, industry_prefs, top_n=3)
                
                print(f"\n📈 {industry} Industry (Top 3):")
                for j, result in enumerate(results, 1):
                    # Handle different result formats
                    if isinstance(result, dict):
                        if 'lead' in result:
                            lead = result['lead']
                            score = result.get('score', 0)
                        else:
                            lead = result
                            score = result.get('score', 0)
                    else:
                        lead = result
                        score = getattr(result, 'score', 0)
                    
                    print(f"   {j}. {lead['name']} - Score: {score:.1f}")
            except Exception as e:
                print(f"   ❌ Error testing {industry}: {str(e)}")
        
        print("\n🎉 LEAD SCORING SYSTEM TEST COMPLETE!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scoring()) 