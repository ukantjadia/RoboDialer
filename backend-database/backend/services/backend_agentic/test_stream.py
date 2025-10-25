# test_stream.py
import os
import requests
from flask import Flask, Response, request, stream_with_context
from dotenv import load_dotenv
import json

# Load API key from .env
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

app = Flask(__name__)

@app.route("/stream-verdict", methods=["POST"])
def stream_verdict():
    user_query = request.json.get("query", "What is Yext's revenue?")

    # Mock fact result (normally you'd query your DB/scraper)
    prompt = f"Answer this query clearly: {user_query}"

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",  # or deepseek-reasoner if that's your plan
        "messages": [{"role": "user", "content": prompt}],
        "stream": True  # ✅ enables streaming
    }

    def generate():
        try:
            with requests.post(url, headers=headers, json=payload, stream=True) as r:
                for line in r.iter_lines():
                    if line:
                        try:
                            decoded = line.decode("utf-8")
                            if decoded.startswith("data: "):
                                data_str = decoded[len("data: "):]
                                if data_str.strip() == "[DONE]":
                                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                                else:
                                    chunk = json.loads(data_str)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                                    if delta:
                                        yield f"data: {json.dumps({'type': 'delta', 'data': delta})}\n\n"
                        except Exception as e:
                            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream")

if __name__ == "__main__":
    app.run(debug=True, port=5001)
