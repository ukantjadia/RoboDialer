from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import uvicorn
import os

# This allows the app to find backend folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.api.routes import scraper, health_check
from backend.config.logger_config import setup_logger

setup_logger()

app = FastAPI()

# Add CORS middleware to allow requests from your frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Specify your frontend URL in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.include_router(scraper.router, prefix="/api", tags=["Scraper"])
app.include_router(health_check.router, prefix="/api", tags=["Heath Check"])

# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=5000)
