from fastapi import FastAPI

from .api.routes import scoring, health_check
from dotenv import load_dotenv
import logging
from fastapi.middleware.cors import CORSMiddleware 

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file at the backend directory
load_dotenv(override=True) # Ensure .env is loaded at app startup

app = FastAPI()

# Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:5173",
#         "http://localhost:5174",
#         "http://localhost:5175",
#         "http://127.0.0.1:5173",
#         "http://127.0.0.1:5174",
#         "http://127.0.0.1:5175",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Include API routers
# app.include_router(search.router, prefix="/api")
app.include_router(health_check.router, prefix="/api", tags=["Health"])
app.include_router(scoring.router, prefix="/api", tags=["Scoring"])

@app.get("/")
async def root():
    return {"message": "Welcome to the CRM Lead Enrichment API!"}
