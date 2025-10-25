import asyncio
import json
import os
import sys
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

# Import the background scraper module
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))) 
from backend.main import start_background_scraping

router = APIRouter()

@router.get("/scrape-stream")
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

                if results.get("is_complete", False):
                    break

                await asyncio.sleep(2)

        except asyncio.CancelledError:
            print("❌ Stream task cancelled.")
            stop_scraper()
        finally:
            final_results = get_results()
            final_processed_data = final_results.get("processed_data", [])
            
            message = "Scraping completed"
            if stop_flag["stop"] and not final_results.get("is_complete", False):
                message = "Scraping cancelled"

            final_data = {
                "message": message,
                "total_scraped": final_results.get("total_scraped", 0),
                "total_processed": len(final_processed_data),
                "elapsed_time": final_results.get("elapsed_time", 0)
            }
            yield "event: done\n"
            yield f"data: {json.dumps(final_data)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
