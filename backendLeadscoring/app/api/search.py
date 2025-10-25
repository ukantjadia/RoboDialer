from fastapi import APIRouter, HTTPException, Body, Query
from typing import List
from ..models.search import SearchParams, CompanyResponse
from ..services.ml_service import MLService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize ML Service
ml_service = MLService()

# Mock database
class MockDatabase:
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def __getitem__(self, key):
        return self
    
    def find(self, query=None):
        return MockCursor()
    
    def update_one(self, filter_query, update_query):
        return MockUpdateResult()
    
    def insert_one(self, document):
        return MockInsertResult()

class MockCursor:
    def to_list(self, length=None):
        return []

class MockUpdateResult:
    def __init__(self):
        self.modified_count = 1

class MockInsertResult:
    def __init__(self):
        self.inserted_id = "mock_id"

# Mock database instance
mock_db = MockDatabase()

# Import mock data from data.py
from ..data import mock_leads as mock_companies

@router.post("/search", response_model=List[CompanyResponse])
async def search_companies(params: SearchParams) -> List[CompanyResponse]:
    try:
        # Convert SearchParams to preferences format for ML service
        preferences = {
            'industry': params.industry,
            'location': params.location,
            'min_employees': params.minEmployees,
            'max_employees': params.maxEmployees,
            'min_revenue': params.minRevenue,
            'max_revenue': params.maxRevenue,
            'target_revenue': params.targetRevenue,
            'target_employees': params.targetEmployees,
            'keywords': params.keywords
        }
        
        # Use ML service to score and filter leads
        scored_results = await ml_service.recommend_leads(mock_companies, preferences, top_n=len(mock_companies))
        
        # Convert to CompanyResponse format
        results = []
        for scored_lead in scored_results:
            # Handle both formats: direct lead object or {'lead': lead, 'score': score}
            if isinstance(scored_lead, dict) and 'lead' in scored_lead:
                lead_data = scored_lead['lead'].copy()
                lead_data['score'] = scored_lead.get('score', 0)
            else:
                lead_data = scored_lead.copy()
                lead_data['score'] = lead_data.get('score', 0)
            
            # Ensure required fields are present
            if 'id' not in lead_data:
                lead_data['id'] = lead_data.get('_id', str(hash(lead_data.get('name', ''))))
            if 'name' not in lead_data:
                lead_data['name'] = lead_data.get('Company Name', 'Unknown')
            if 'industry' not in lead_data:
                lead_data['industry'] = lead_data.get('Industry', 'Unknown')
            
            results.append(CompanyResponse(**lead_data))
        
        return results
    except Exception as e:
        logger.error(f"Error searching companies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.options("/search")
async def options_search():
    return {"message": "OK"}

@router.post("/recommend")
async def recommend_leads(
    preferences: dict = Body(..., example={
        "industry": "Technology",
        "location": "San Francisco",
        "must_have_website": True,
        "min_employees": 0,
        "max_employees": 1000,
        "min_revenue": 1000000,
        "max_revenue": 100000000,
        "target_revenue": 50000000,
        "target_employees": 50,
        "keywords": "AI, automation, software",
        "negative_keywords": "legacy, outdated"
    }),
    top_n: int = 1
):
    try:
        logger.info(f"[API] Received preferences: {preferences}")
        
        # Use ML service for dynamic scoring
        scored_results = await ml_service.recommend_leads(mock_companies, preferences, top_n=top_n)
        
        # Format results with explanations
        recommendations = []
        for scored_lead in scored_results:
            lead_data = scored_lead.get('lead', {})
            lead_data['score'] = scored_lead.get('score', 0)
            lead_data['explanation'] = scored_lead.get('explanation', '')
            recommendations.append(lead_data)
        
        return recommendations
    except Exception as e:
        logger.error(f"Error recommending leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 