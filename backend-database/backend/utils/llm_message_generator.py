# Handles message generation

import logging
from config.config import Config
from groq import Groq
from openai import OpenAI, APIStatusError
import anthropic

logger = logging.getLogger(__name__)

class GenerateController:
    """
    Controller for generating messages using different LLM providers.
    """
    @classmethod
    def _call_groq(cls, prompt: str) -> str:
        client = Groq(api_key=Config.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=True,
        )
        text = ""
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                text += delta
        return text

    @classmethod
    def _call_claude(cls, prompt: str) -> str:
        client = anthropic.Client(api_key=Config.ANTHROPIC_API_KEY)
        full_prompt = f"{anthropic.HUMAN_PROMPT}{prompt}{anthropic.AI_PROMPT}"
        resp = client.completions.create(
            model="claude-2",
            prompt=full_prompt,
            max_tokens_to_sample=Config.CLAUDE_MAX_TOKENS,
            temperature=0.7
        )
        return resp.completion

    @classmethod
    def _call_deepseek(cls, prompt: str) -> str:
        client = OpenAI(
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.OPENAI_BASE_URL
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user",   "content": prompt},
            ],
            stream=False
        )
        return response.choices[0].message.content

    @classmethod
    def generate_with_model(cls, prompt: str, model_choice: str) -> str:
        key = model_choice.strip().lower()
        if key == "groq":
            return cls._call_groq(prompt)
        if key in ("claude", "anthropic"):
            return cls._call_claude(prompt)
        if key == "deepseek":
            return cls._call_deepseek(prompt)
        raise ValueError(f"Unsupported model_choice: {model_choice}")
