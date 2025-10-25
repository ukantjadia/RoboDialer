import os
import json
import re
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("Please set DEEPSEEK_API_KEY in your .env file")

def llm_chat_deepseek(prompt: str) -> Optional[str]:
    """
    Sends a prompt to the DeepSeek model and returns the reply.
    """
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result and 'choices' in result and result['choices']:
            return result['choices'][0]['message']['content'].strip()
        else:
            print(f"⚠️ DeepSeek AI call failed: No valid response received.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ DeepSeek AI call failed ({e}).")
        return None
    except Exception as e:
        print(f"⚠️ DeepSeek AI call failed during processing response ({e}).")
        return None

def calculate_relevancy_score(title: str, summary: str, target_company: str) -> int:
    """
    Calculates a preliminary score based on measurable factors from the documentation.
    - Entity Mentions (20%) -> max 20 points
    - Financial/Strategic Impact (30%) -> max 30 points
    """
    score = 0
    full_text = (title + " " + summary).lower()
    lower_target = target_company.lower()

    # Factor 1: Entity Mentions (20% Weight)
    mention_count = full_text.count(lower_target)
    if mention_count > 4:
        score += 20
    elif mention_count > 2:
        score += 15
    elif mention_count > 0:
        score += 10

    # Factor 2: Financial/Strategic Impact (30% Weight)
    high_impact_keywords = ["acquire", "acquisition", "merger", "billion"]
    if any(keyword in full_text for keyword in high_impact_keywords):
        score += 30
    else:
        medium_impact_keywords = ["funding", "investment", "million", "revenue", "profit"]
        if any(keyword in full_text for keyword in medium_impact_keywords):
            score += 15
            
    return score

def generate_tags_for_summary(title: str, summary: str, target_company: str, scraped_content: str = None) -> Dict[str, object]:
    """
    Analyzes news using weighted factors and returns a dict of tags.
    Optionally uses scraped content for better analysis.
    """
    if not all([title, summary, target_company]):
        return {}

    # Use scraped content if available for better analysis
    analysis_text = summary
    if scraped_content and len(scraped_content) > len(summary):
        analysis_text = f"{summary}\n\nFull Article Content: {scraped_content[:1000]}"

    relevancy_score = calculate_relevancy_score(title, analysis_text, target_company)

    prompt = (
        "You are a financial news analyst. Your task is to analyze the provided text and determine the 'relevancy' tag based on a specific weighted model. Then, provide 'event_type' and 'topic' tags. Return a compact JSON object.\n\n"
        "The relevancy model is based on four factors:\n"
        "- Entity Mentions (20%)\n"
        "- Financial/Strategic Impact (30%)\n"
        "- Novelty (25%)\n"
        "- Industry Significance (25%)\n\n"
        "CONTEXT & INSTRUCTIONS:\n"
        "I have already pre-calculated the first two factors for you:\n"
        f"- The combined score for 'Entity Mentions' and 'Financial/Strategic Impact' is {relevancy_score} out of a possible 50.\n\n"
        "Your Task:\n"
        "1. Evaluate the remaining two factors, 'Novelty' and 'Industry Significance', based on your understanding of the news content.\n"
        "2. Combine your evaluation with the pre-calculated score to determine a final 'relevancy' of 'High', 'Medium', or 'Low'. A high pre-calculated score combined with high novelty or significance should result in a 'High' relevancy.\n"
        "3. Determine the 'event_type' (e.g., 'Acquisition') and 'topic' (e.g., 'Cybersecurity').\n\n"
        f"NEWS CONTENT TO ANALYZE:\nTitle: {title}\nSummary: {summary}\n"
        f"{'Full Content Available: Yes' if scraped_content else 'Full Content Available: No'}\n\n"
        "Return ONLY the JSON object.\n"
        "JSON:"
    )

    raw = llm_chat_deepseek(prompt)
    if not raw:
        return {}

    text = raw.strip().replace("```json", "").replace("```", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "parsing_failed", "response": raw}

if __name__ == "__main__":
    sample_title = "Sentinel Corp to Acquire AegisCloud in Landmark Deal"
    sample_summary = (
        "Cyber-security firm Sentinel Corp announced its definitive agreement to acquire cloud-native "
        "security startup AegisCloud for $500 million. Sentinel Corp CEO praised the deal. Industry analyst Jane Doe "
        "also praised it. The deal is expected to close by year-end, integrating AegisCloud’s technology into Sentinel Corp’s platform."
    )
    target = "Sentinel Corp"

    print(f"Analyzing for target: '{target}'\n")
    result = generate_tags_for_summary(title=sample_title, summary=sample_summary, target_company=target)
    print(json.dumps(result, indent=2))