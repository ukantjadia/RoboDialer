from fastapi import APIRouter, HTTPException
from typing import List
from ...models.scoring_model import ScoringRequest, ScoringResponse, ScoringResult, Analysis, ScoreComponent
from ...services.ml_service import MLService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

ml_service = MLService()

@router.post("/score_leads", response_model=ScoringResponse)
async def score_companies(request: ScoringRequest):
    preferences = request.preferences
    companies = request.companies
    
    if not isinstance(companies, list) or not companies:
        raise HTTPException(status_code=400, detail="No companies provided.")

    try:
        # score_companies_list must return a list of dicts with company name and all breakdown fields
        scored_results = await ml_service.score_companies_batch(companies, preferences)
    except Exception as e:
        logger.error(f"Error scoring companies: {e}")
        raise HTTPException(status_code=500, detail="Failed to return AI score")
    
    return ScoringResponse(results=scored_results)