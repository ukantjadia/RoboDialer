from pydantic import BaseModel
from typing import Optional

class SearchParams(BaseModel):
    companyName: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    minEmployees: Optional[int] = None
    maxEmployees: Optional[int] = None
    minRevenue: Optional[int] = None
    maxRevenue: Optional[int] = None
    targetRevenue: Optional[int] = None
    targetEmployees: Optional[int] = None
    keywords: Optional[str] = None

class CompanyResponse(BaseModel):
    id: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry: str
    revenue: Optional[str] = None
    product_service: Optional[str] = None
    business_type: Optional[str] = None
    employees: Optional[str] = None
    year_founded: Optional[str] = None
    owner_linkedin: Optional[str] = None
    score: Optional[float] = None 