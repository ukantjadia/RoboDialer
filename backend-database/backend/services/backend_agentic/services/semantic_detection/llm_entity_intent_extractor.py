import os
import json
import time
import requests
from typing import Dict, Any
from huggingface_hub import login
login(os.getenv("HF_API_TOKEN"))

API_URL = os.getenv("HF_ROUTER_URL", "https://router.huggingface.co/v1/chat/completions")
MODEL = os.getenv("HF_ROUTER_MODEL", "tiiuae/falcon-7b-instruct")
TIMEOUT = float(os.getenv("HF_ROUTER_TIMEOUT", "12"))
MAX_RETRIES = int(os.getenv("HF_ROUTER_MAX_RETRIES", "2"))


def _headers() -> Dict[str, str]:
	return {"Authorization": f"Bearer {os.environ.get('HF_API_TOKEN', '')}"}


SYSTEM_PROMPT = (
	"You extract user intent and entities for a lead-gen orchestration system.\n"
	"Return STRICT JSON only with keys: intent(one of [compare, analyze, search, summarize]), "
	"entities(array of strings), confidence(float 0..1), reasoning(array of short strings).\n"
	"Do not add any text outside JSON."
)


def _strip_code_fences(s: str) -> str:
	s = s.strip()
	if s.startswith("```"):
		# Try to extract the fenced block content
		parts = s.split("```")
		if len(parts) >= 3:
			return parts[1].strip()
	return s


def _parse_json_strict(s: str) -> Dict[str, Any]:
	s = _strip_code_fences(s)
	return json.loads(s)


def extract_intent_entities(user_query: str) -> Dict[str, Any]:
	"""
	Call the HF Router GPT-OSS model to extract intent + entities.
	Returns dict: { intent, entities, confidence, reasoning }
	Raises on failure.
	"""
	payload = {
		"model": MODEL,
		"messages": [
			{"role": "system", "content": SYSTEM_PROMPT},
			{"role": "user", "content": user_query},
		],
		"temperature": 0.0,
	}

	last_err = None
	for _ in range(MAX_RETRIES + 1):
		try:
			resp = requests.post(API_URL, headers=_headers(), json=payload, timeout=TIMEOUT)
			resp.raise_for_status()
			body = resp.json()
			msg = body["choices"][0]["message"]["content"]
			data = _parse_json_strict(msg)

			intent = str(data.get("intent", "search")).lower()
			if intent not in ["compare", "analyze", "search", "summarize"]:
				intent = "search"

			entities = data.get("entities") or []
			if not isinstance(entities, list):
				entities = []

			confidence_val = data.get("confidence", 0.6)
			try:
				confidence = float(confidence_val)
			except Exception:
				# sometimes models wrap as {score: x}
				confidence = float(confidence_val.get("score", 0.6)) if isinstance(confidence_val, dict) else 0.6

			reasoning = data.get("reasoning") or []
			if isinstance(reasoning, str):
				reasoning = [reasoning]

			return {
				"intent": intent,
				"entities": entities,
				"confidence": confidence,
				"reasoning": reasoning,
			}
		except Exception as e:
			last_err = e
			time.sleep(0.25)

	raise RuntimeError(f"HF router extraction failed: {last_err}") 