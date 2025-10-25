import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx
import requests
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from backend.config.logger_config import setup_logger
setup_logger()
logger = logging.getLogger("FlareSolverr")

FLARESOLVERR_URL = "http://flaresolverr:8191/v1"
FLARESOLVERR_TIMEOUT = 90 

def get_solved_cookies(target_url: str) -> list[dict]:
    """
    Requests FlareSolverr to solve a Cloudflare challenge and return cookies.
    """
    payload = {
        "cmd": "request.get",
        "url": target_url,
        "maxTimeout": 60000, 
    }
    

    headers = {"Content-Type": "application/json"}
    logger.info(f"Requesting cookies from FlareSolverr for: {target_url}")
    try:
        response = requests.post(FLARESOLVERR_URL, json=payload, headers=headers, timeout=FLARESOLVERR_TIMEOUT) 
        response.raise_for_status() 
        solution = response.json()["solution"]
        cookies = solution.get("cookies", [])
        for cookie in cookies:
            if "expiry" in cookie:
                cookie["expires"] = cookie.pop("expiry")
        if cookies:
            logger.info(f"FlareSolverr returned {len(cookies)} cookies.")
        else:
            logger.warning(f"FlareSolverr returned no cookies.")
        return cookies
    except requests.exceptions.RequestException as e:
        logger.error(f"FlareSolverr request failed for {target_url}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error with FlareSolverr for {target_url}: {e}")
        return []

 # seconds

def post_solved_cookies(target_url: str, post_data: str) -> Optional[Dict[str, any]]:
    """
    Requests FlareSolverr to solve a Cloudflare challenge and return cookies.
    """
    payload = {
        "cmd": "request.post",
        "url": target_url,
        "maxTimeout": 50000,
        "postData": post_data
    }
    
    headers = {"Content-Type": "application/json"}
    logger.info(f"Requesting cookies from FlareSolverr for: {target_url}")
    try:
        response = requests.post(FLARESOLVERR_URL, json=payload, headers=headers, timeout=FLARESOLVERR_TIMEOUT) 
        response.raise_for_status() 
        solution = response.json()["solution"]
        cookies = solution.get("cookies", [])
        for cookie in cookies:
            if "expiry" in cookie:
                cookie["expires"] = cookie.pop("expiry")
        if cookies:
            logger.info(f"FlareSolverr returned {len(cookies)} cookies.")
        else:
            logger.warning(f"FlareSolverr returned no cookies.")
        return solution
    except requests.exceptions.RequestException as e:
        logger.error(f"FlareSolverr request failed for {target_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error with FlareSolverr for {target_url}: {e}")
        return None

async def create_session() -> Optional[str]:
    """Creates a new FlareSolverr session asynchronously."""
    payload = {"cmd": "sessions.create"}
    logger.info("Creating FlareSolverr session...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(FLARESOLVERR_URL, json=payload, timeout=FLARESOLVERR_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            session_id = data.get("session")
            if session_id:
                logger.info(f"FlareSolverr session created: {session_id}")
                return session_id
            logger.error(f"Failed to create FlareSolverr session: {data.get('message')}")
            return None
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Error creating FlareSolverr session: {e}")
        return None

async def destroy_session(session_id: str):
    """Destroys a FlareSolverr session asynchronously."""
    payload = {"cmd": "sessions.destroy", "session": session_id}
    logger.info(f"Destroying FlareSolverr session: {session_id}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(FLARESOLVERR_URL, json=payload, timeout=FLARESOLVERR_TIMEOUT)
            response.raise_for_status()
            logger.info("FlareSolverr session destroyed successfully.")
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Error destroying FlareSolverr session {session_id}: {e}")

async def get_solved_page(
    target_url: str,
    session_id: str = None,
    cookies: List[Dict[str, Any]]=None
) -> Optional[Dict[str, Any]]:
    """
    Uses an existing FlareSolverr session to get the HTML and cookies of a protected page.
    """
    payload = {
        "cmd": "request.get",
        "url": target_url,
        "maxTimeout": 60000,
    }

    if session_id:
        payload["session"] = session_id

    if cookies:
        payload["cookies"] = cookies

    logger.info(f"Requesting solved page via FlareSolverr for: {target_url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(FLARESOLVERR_URL, json=payload, timeout=FLARESOLVERR_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "ok" and data.get("solution"):
                solution = data["solution"]
                html = solution.get("response")
                
                if "Cloudflare" in (html or "") and "Just a moment..." in (html or ""):
                    logger.warning("FlareSolverr may have failed to bypass challenge.")
                    return None
                    
                logger.info(f"Successfully retrieved page content for {target_url}")
                return solution
            
            logger.error(f"FlareSolverr returned an error: {data.get('message')}")
            return None

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Error during FlareSolverr request for {target_url}: {e}")
        return None

async def post_solved_page(
    target_url: str,
    post_data: str = None,
    cookies: List[Dict[str, Any]] = None
) ->  Optional[Dict[str, Any]]:
    """
    Uses an existing FlareSolverr session to get the HTML and cookies of a protected page.
    """
    payload = {
        "cmd": "request.post",
        "url": target_url,
        "maxTimeout": 60000,
        "postData":post_data
    }

    if cookies:
        payload["cookies"] = cookies

    logger.info(f"Requesting solved page via FlareSolverr for: {target_url}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(FLARESOLVERR_URL, json=payload, timeout=FLARESOLVERR_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "ok" and data.get("solution"):
                solution = data["solution"]
                html = solution.get("response")
                
                # A simple check to see if Cloudflare was actually bypassed
                if "Cloudflare" in (html or "") and "Just a moment..." in (html or ""):
                    logger.warning("FlareSolverr may have failed to bypass challenge.")
                    return None
                    
                logger.info(f"Successfully retrieved page content for {target_url}")
                return solution
            
            logger.error(f"FlareSolverr returned an error: {data.get('message')}")
            return None

    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logger.error(f"Error during FlareSolverr request for {target_url}: {e}")
        return None