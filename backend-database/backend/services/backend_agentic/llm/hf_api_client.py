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

class HFInferenceClient:
    """
    Hugging Face Inference API client for text generation.
    It posts to https://api-inference.huggingface.co/models/{model} with the HF token.
    Returns APIResponse compatible with other LLM clients.
    """
    def __init__(self,
                 model: Optional[str] = None,
                 token: Optional[str] = None,
                 timeout: Optional[int] = None,
                 max_retries: Optional[int] = None):
        self.model = model or os.getenv("HF_API_MODEL", "tiiuae/falcon-7b-instruct")
        self.token = token or os.getenv("HF_API_TOKEN", "")
        self.timeout = int(timeout or os.getenv("HF_API_TIMEOUT", "12"))
        self.max_retries = int(max_retries or os.getenv("HF_API_RETRIES", "2"))
        self.base_url = f"https://api-inference.huggingface.co/models/{self.model}"
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def generate_response(self, prompt: str, system_message: Optional[str] = None) -> APIResponse:
        start = datetime.now()
        last_exc: Optional[Exception] = None
        # Construct a strict JSON-only instruction
        sys = (system_message or "").strip()
        instruction = (
            (sys + "\n" if sys else "") +
            "Return ONLY valid JSON. Do not include any prose or code fences."
        )
        full_prompt = f"{instruction}\n\n{prompt}" if instruction else prompt
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": 256,
                "temperature": 0.1,
                "return_full_text": False
            }
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        for attempt in range(self.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with (self.session or aiohttp.ClientSession()) as session:
                    async with session.post(self.base_url, json=payload, headers=headers, timeout=timeout) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # HF response can be a list of generated_texts or a dict; handle common shapes
                            content = ""
                            if isinstance(data, list) and data:
                                item = data[0]
                                content = item.get("generated_text", "") or json.dumps(item)
                            elif isinstance(data, dict):
                                content = data.get("generated_text", "") or json.dumps(data)
                            validation = self._validate_content(content)
                            exec_time = (datetime.now() - start).total_seconds()
                            return APIResponse(
                                content=content,
                                status="success",
                                usage={},
                                model=self.model,
                                validation_result=validation,
                                fallback_used=False,
                                timestamp=start,
                                execution_time=exec_time,
                            )
                        # Retry on transient statuses
                        if resp.status in (429, 500, 502, 503, 504):
                            last_exc = Exception(f"HF API HTTP {resp.status}: {await resp.text()}")
                            await asyncio.sleep(1 + attempt)
                            continue
                        text = await resp.text()
                        raise Exception(f"HF API error {resp.status}: {text}")
            except asyncio.TimeoutError as te:
                last_exc = te
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
            except Exception as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                break
        exec_time = (datetime.now() - start).total_seconds()
        logger.error(f"HF Inference API call failed: {last_exc}")
        return APIResponse(
            content=str(last_exc) if last_exc else "",
            status="error",
            usage={},
            model=self.model,
            validation_result={"is_valid": False, "is_json": False, "errors": [str(last_exc)] if last_exc else []},
            fallback_used=False,
            timestamp=start,
            execution_time=exec_time,
        )

    def _validate_content(self, content: str) -> Dict[str, Any]:
        content = (content or "").strip()
        # Try strict JSON parse
        try:
            json.loads(content)
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