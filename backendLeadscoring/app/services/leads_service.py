from typing import List, Dict, Any, Optional
from .ml_service import MLService
import bson
from bson import ObjectId
import re
import logging

logger = logging.getLogger(__name__)

def convert_objectid_to_str(doc):
    if isinstance(doc, dict):
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                doc[k] = str(v)
            elif isinstance(v, dict):
                doc[k] = convert_objectid_to_str(v)
            elif isinstance(v, list):
                doc[k] = [convert_objectid_to_str(i) for i in v]
    elif isinstance(doc, list):
        doc = [convert_objectid_to_str(i) for i in doc]
    return doc

def normalize_lead_fields(lead):
    lead = dict(lead)
    lead.pop('_id', None)

    # Name (robust normalization)
    import re
    norm = {re.sub(r'\s+', '', k).lower(): v for k, v in lead.items()}
    # Always set 'name' to company name or fallback to a unique identifier
    if 'companyname' in norm and norm['companyname']:
        lead['name'] = norm['companyname'].strip()
    elif 'name' in norm and norm['name']:
        lead['name'] = norm['name'].strip()
    else:
        # Fallback: use First Name + Last Name + City + State if available
        fallback = []
        for key in ['firstname', 'lastname', 'city', 'state']:
            val = norm.get(key)
            if val:
                fallback.append(str(val).strip())
        lead['name'] = ' '.join(fallback) if fallback else 'Unknown'

    # Industry (exact key match with trailing space)
    industry = lead.get('Industry ')
    lead['industry'] = industry.strip() if industry else ''

    # Location (State, exact key match)
    state = lead.get('State')
    lead['location'] = state.strip() if state else ''

    # Employees (robust normalization)
    employees = lead.get('Employees') or norm.get('employees')
    if employees:
        try:
            lead['employees'] = int(employees)
        except Exception:
            lead['employees'] = str(employees).strip()
    else:
        lead['employees'] = ''

    # Preserve AI analysis data and other important fields
    # These fields should not be stripped out
    ai_fields = ['ai_analysis', 'risk_score', 'growth_potential_score', 'investment_recommendation', 'explanation', 'score']
    for field in ai_fields:
        if field in lead:
            # Ensure the field is preserved
            pass  # Already preserved by dict(lead)

    return lead

class LeadsService:
    def __init__(self):
        self.leads = []
        self.ml_service = MLService()
        self._is_initialized = False
        self._collection = 'companies'

    async def initialize(self, collection: str = 'companies'):
        """Initialize the service by loading leads from DB and training ML models"""
        if not self._is_initialized or self._collection != collection:
            try:
                from ..database import get_mongo_db
                db = await get_mongo_db()
                companies = await db[collection].find().to_list(length=None)
                self.leads = companies
                self._collection = collection
                if self.leads:
                    print(f"Loaded {len(self.leads)} leads from DB")
                else:
                    print(f"No leads found in database collection '{collection}'")
                self._is_initialized = True
            except Exception as e:
                print(f"Error loading leads from DB: {e}")
                self.leads = []
                self._is_initialized = False

    async def get_analytics(self) -> Dict[str, Any]:
        """Get analytics data"""
        if not self._is_initialized:
            await self.initialize()
        
        if not self.leads:
            return {
                "lead_distribution": {},
                "lead_projection": [],
                "top_leads": []
            }

        # Return basic analytics without ML processing
        return {
            "total_leads": len(self.leads),
            "lead_distribution": {},
            "lead_projection": [],
            "top_leads": self.leads[:10] if self.leads else []
        }

    async def add_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new lead"""
        if not self._is_initialized:
            await self.initialize()
        # Accept website_text, llm_summary, last_scraped if present
        # (No strict schema, but document for clarity)
        # lead['website_text'], lead['llm_summary'], lead['last_scraped'] can be present
        self.leads.append(lead)
        return lead

    async def delete_lead(self, lead_id: str) -> bool:
        """Delete a lead by ID"""
        if not self._is_initialized:
            await self.initialize()
        
        initial_length = len(self.leads)
        self.leads = [lead for lead in self.leads if lead.get("id") != lead_id]
        
        if len(self.leads) < initial_length:
            return True
        return False

    def get_leads(self, sort_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all leads"""
        return self.leads

    def get_lead_by_id(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific lead by ID"""
        for lead in self.leads:
            if lead.get('id') == lead_id:
                return lead
        return None

    def update_lead(self, lead_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a lead and retrain ML models"""
        for lead in self.leads:
            if lead.get('id') == lead_id:
                lead.update(updates)
                return lead
        return None

    def convert_objectids(self, obj):
        if isinstance(obj, list):
            return [self.convert_objectids(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self.convert_objectids(v) for k, v in obj.items()}
        elif isinstance(obj, bson.ObjectId):
            return str(obj)
        else:
            return obj

    async def recommend_leads_async(self, preferences: Dict[str, Any], top_n: int = 1, collection: str = 'companies') -> List[Dict[str, Any]]:
        await self.initialize(collection)
        recommendations = await self.ml_service.recommend_leads(self.leads, preferences, top_n)
        # Deeply convert all ObjectIds to strings
        recommendations = self.convert_objectids(recommendations)
        recommendations = recommendations[:top_n]
        
        # Debug logging to confirm AI analysis data is preserved
        if recommendations:
            first_rec = recommendations[0]
            logger.info(f"[LEADS SERVICE] First recommendation keys: {list(first_rec.keys())}")
            logger.info(f"[LEADS SERVICE] AI analysis present: {'ai_analysis' in first_rec}")
            logger.info(f"[LEADS SERVICE] Risk score present: {'risk_score' in first_rec}")
            logger.info(f"[LEADS SERVICE] Growth score present: {'growth_potential_score' in first_rec}")
            if 'ai_analysis' in first_rec:
                logger.info(f"[LEADS SERVICE] AI analysis data: {first_rec['ai_analysis']}")
        
        # Don't call normalize_lead_fields to preserve AI analysis data
        return recommendations 