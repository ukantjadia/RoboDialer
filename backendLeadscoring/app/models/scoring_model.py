from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ScoringRequest(BaseModel):
    preferences: Dict[str, Any]
    companies: List[Dict[str, Any]]

class ScoreComponent(BaseModel):
    score: float
    explanation: List[str]

class Analysis(BaseModel):
    total_score: float
    investment_recommendation: str
    growth_potential: ScoreComponent
    risk: ScoreComponent
    keywords: ScoreComponent
    strengths: List[str]
    concerns: List[str]

class ScoringResult(BaseModel):
    company: str  # For frontend mapping
    analysis: Analysis

class ScoringResponse(BaseModel):
    results: List[ScoringResult]