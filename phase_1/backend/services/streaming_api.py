from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import time
import json
import asyncio
from threading import Thread
import sys
import uvicorn
import os

# Import the background scraper module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the start_background_scraping function
from backend.services.background import start_background_scraping

app = FastAPI()

# Add CORS middleware to allow requests from your frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Specify your frontend URL in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

@app.get("/api/scrape-stream")
async def stream(industry: str, location: str, request: Request):
    """Endpoint to stream scraper results for a given industry and location"""
    stop_flag = {"stop": False}
    
    def stop_scraper():
        stop_flag["stop"] = True
        
    get_results = start_background_scraping(industry, location, stop_flag)
    
    async def event_stream():
        yield "retry: 1000\n"
        yield "event: init\n"
        yield f"data: {json.dumps({'message': 'Scraper started'})}\n\n"

        last_data_count = 0
        try:
            while True:
                if await request.is_disconnected():
                    print("🔌 Client disconnected — stopping stream and scraper.")
                    stop_scraper()
                    break

                results = get_results()
                processed_data = results.get("processed_data", [])
                current_data_count = len(processed_data)

                if current_data_count > last_data_count:
                    new_items = processed_data
                    batch_data = {
                        "batch": last_data_count // 10 + 1,
                        "new_items": new_items,
                        "total_scraped": results.get("total_scraped", 0),
                        "elapsed_time": results.get("elapsed_time", 0),
                        "processed_count": current_data_count
                    }

                    yield f"event: batch\n"
                    yield f"data: {json.dumps(batch_data)}\n\n"
                    last_data_count = current_data_count

                if results.get("is_complete", False) or stop_flag["stop"]:
                    final_data = {
                        "message": "Scraping completed",
                        "total_scraped": results.get("total_scraped", 0),
                        "total_processed": len(processed_data),
                        "elapsed_time": results.get("elapsed_time", 0)
                    }

                    yield f"event: done\n"
                    yield f"data: {json.dumps(final_data)}\n\n"
                    break

                await asyncio.sleep(2)

        except asyncio.CancelledError:
            print("❌ Stream task cancelled.")
            stop_scraper()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
    
@app.get("/api/health")
async def health():
    return {"status": "ok"}

# if __name__ == "__main__":
#     uvicorn.run(app, host="127.0.0.1", port=5000)
