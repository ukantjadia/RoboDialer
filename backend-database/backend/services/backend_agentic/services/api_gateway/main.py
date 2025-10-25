# FastAPI app
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Dict, Any, Optional
import uuid
import asyncio

# Orchestrator components
from aggregator.aggregator import Aggregator
from services.orchestrator.router_client import RouterClient
from services.orchestrator.orchestrator import LangGraphOrchestrator
from llm.deepseek_client import DeepSeekClient

app = FastAPI(title="Agentic Backend API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for dispatch results (ephemeral)
dispatch_results: Dict[str, Dict[str, Any]] = {}

# Initialize core components once
aggregator = Aggregator()
router_client = RouterClient()
llm_client = DeepSeekClient()
orchestrator = LangGraphOrchestrator(router_client=router_client, llm_client=llm_client, aggregator=aggregator)

@app.post("/api/query")
async def query_endpoint(request: Dict[str, Any]):
    """
    Main query endpoint that accepts natural language queries
    """
    try:
        user_id = request.get("user_id", "anon")
        query = request.get("query")
        options = request.get("options", {})
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        result = await orchestrator.process_query(user_id=user_id, query=query, options=options)
        
        # Store by dispatch_id if present
        dispatch_id = result.get("dispatch_id") or f"d-{uuid.uuid4().hex[:8]}"
        result["dispatch_id"] = dispatch_id
        dispatch_results[dispatch_id] = result
        
        return result
        
    except Exception as e:
        logger.error(f"Error in query endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/result/{dispatch_id}")
async def get_result(dispatch_id: str):
    """
    Get the result of a dispatch by ID
    """
    if dispatch_id not in dispatch_results:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    return dispatch_results[dispatch_id]

@app.post("/tool/scrape")
async def test_scrape(request: Dict[str, Any]):
    """
    Test endpoint for web scraping tool
    """
    url = request.get("url")
    selectors = request.get("selectors", [])
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    # TODO: Implement actual scraping
    return {
        "text": f"Scraped content from {url}",
        "metadata": {
            "source": url,
            "fetched_at": "2025-01-01T00:00:00Z"
        }
    }

@app.post("/tool/facts_csv_query")
async def test_facts_query(request: Dict[str, Any]):
    """
    Test endpoint for facts CSV query tool
    """
    entity = request.get("entity")
    fields = request.get("fields", [])
    
    if not entity:
        raise HTTPException(status_code=400, detail="Entity is required")
    
    # TODO: Implement actual CSV lookup
    # Mock response based on the actual CSV structure
    return {
        "entity": entity,
        "Company Name": entity,
        "Industry": "Technology",
        "Revenue": "10M",
        "Employees": "50",
        "City": "San Francisco",
        "State": "CA"
    }

@app.post("/tool/query_vectors")
async def test_vector_query(request: Dict[str, Any]):
    """
    Test endpoint for vector query tool
    """
    query = request.get("query")
    top_k = request.get("top_k", 5)
    
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    # TODO: Implement actual vector search
    return {
        "documents": [],
        "metadatas": [],
        "distances": []
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "message": "Agentic Backend API is running"}

@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "message": "Agentic Backend API",
        "version": "1.0.0",
        "endpoints": {
            "query": "/api/query",
            "result": "/api/result/{dispatch_id}",
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 