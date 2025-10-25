# Note: This OSSLLMClient is currently unused when DeepSeek is configured as the default LLM.
# It remains for future OpenAI-compatible endpoints but is not wired by default.
import os
import aiohttp
import asyncio
import logging
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

@dataclass
class APIResponse:
    content: str
    status: str
    usage: Dict[str, int]
    model: str
    validation_result: Dict[str, Any]
    fallback_used: bool
    timestamp: datetime
    execution_time: float

class OSSLLMClient:
    """
    OpenAI-compatible OSS LLM client (e.g., vLLM/TGI) for chat completions.
    Exposes generate_response(user_prompt, system_message=None) and returns APIResponse.
    """
    def __init__(self,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 api_key: Optional[str] = None,
                 timeout: Optional[int] = None,
                 max_retries: Optional[int] = None):
        self.base_url = base_url or os.getenv("OSS_LLM_BASE_URL", "http://localhost:8000")
        self.model = model or os.getenv("OSS_LLM_MODEL", "EleutherAI/gpt-neox-20b")
        self.api_key = api_key or os.getenv("OSS_LLM_API_KEY", "")
        self.timeout = int(timeout or os.getenv("OSS_LLM_TIMEOUT", "30"))
        self.max_retries = int(max_retries or os.getenv("OSS_LLM_RETRIES", "3"))
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def generate_response(self, prompt: str, system_message: Optional[str] = None):
        start = datetime.now()
        last_exc: Optional[Exception] = None
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 256,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with (self.session or aiohttp.ClientSession()) as session:
                async with session.post(url, json=payload, headers=headers, timeout=timeout) as resp:
                    data = await resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    exec_time = (datetime.now() - start).total_seconds()
                    return APIResponse(content=content, status="success", usage=data.get("usage", {}), model=data.get("model", self.model), validation_result={"is_valid": True, "is_json": False}, fallback_used=False, timestamp=start, execution_time=exec_time)
        except Exception as e:
            exec_time = (datetime.now() - start).total_seconds()
            return APIResponse(content=str(e), status="error", usage={}, model=self.model, validation_result={"is_valid": False, "is_json": False}, fallback_used=False, timestamp=start, execution_time=exec_time)

    def _validate_content(self, content: str) -> Dict[str, Any]:
        content = (content or "").strip()
        # Try strict JSON parse
        try:
            parsed = json.loads(content)
            return {"is_valid": True, "is_json": True, "errors": []}
        except Exception:
            # Attempt to find a JSON object in content
            try:
                import re
                m = re.search(r"\{[\s\S]*\}$", content)
                if m:
                    json.loads(m.group(0))
                    return {"is_valid": True, "is_json": True, "errors": []}
            except Exception:
                pass
        return {"is_valid": False, "is_json": False, "errors": ["Invalid or non-JSON content"]} 