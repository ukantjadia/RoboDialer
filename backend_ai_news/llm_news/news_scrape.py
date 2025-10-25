import json
import os
import requests
from newspaper import Article, Config
from boilerpy3 import extractors
boiler_extractor = extractors.ArticleExtractor()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("Please set DEEPSEEK_API_KEY in your .env file")

def extract_article_text(url):
    """Extract article text using multiple methods"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    try:
        # First try newspaper3k
        config = Config()
        config.browser_user_agent = headers['User-Agent']
        config.request_timeout = 10
        
        article = Article(url, config=config)
        article.download()
        article.parse()
        if article.text:
            return article.text
    except Exception as e:
        print(f"[Error] Newspaper3k failed for {url}: {e}")
    
    try:
        # Fallback to boilerpy3
        html = requests.get(url, timeout=10).text
        if "<html" not in html.lower():
            return ""
        return boiler_extractor.get_content(html)
    except Exception as e:
        print(f"[Error] Boilerpy3 failed for {url}: {e}")
    
    return ""

def extract_article_text_with_scraped_content(entry):
    """Extract article text, prioritizing scraped content if available"""
    # Check if we have scraped content from News API RapidAPI
    if entry.get('scraped_content'):
        return entry.get('scraped_content')
    
    # Fallback to URL extraction
    url = entry.get('url') or entry.get('link', '')
    if url:
        return extract_article_text(url)
    
    return ""

def summarize_articles(news_entries, max_article_length=3000):
    all_articles = []

    for entry in news_entries:
        # Use scraped content if available, otherwise extract from URL
        article_text = extract_article_text_with_scraped_content(entry)
        if article_text:
            trimmed = article_text.strip()[:max_article_length]
            all_articles.append(f"Article Title: {entry.get('title', '')}\n\n{trimmed}")

    if not all_articles:
        return "No article content could be extracted for summarization."

    combined_input = "\n\n---\n\n".join(all_articles)

    prompt = f"""
You are a business research assistant. Read the following **full articles** related to a company's recent news.

Write a rich, detailed paragraph that summarizes all major events across the articles. Capture:
- All key partnerships or announcements
- Product/platform launches or expansions
- Strategic directions and industry movements

⚠️ Do not begin with phrases like "Here is a summary" or "This article is about".

Include multiple points if necessary, but stay within one paragraph.

News Articles:
{combined_input}
"""

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 1500
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Error] DeepSeek summarization failed: {e}")
        return "[Error] DeepSeek summarization failed."

def update_news_summary_for_company_key(company_key: str, all_data: dict) -> dict:
    """
    Updates news_summary for the given company key in the company_data dict.
    """
    if company_key not in all_data:
        print(f"[❌ Error] Company key '{company_key}' not found.")
        return all_data

    news_entries = all_data[company_key].get("news", [])
    if not news_entries:
        print(f"[ℹ️] No news entries found for '{company_key}'. Skipping news summary.")
        return all_data

    summary = summarize_articles(news_entries)
    all_data[company_key]["news_summary"] = summary
    print(f"[✅ Success] News summary added for '{company_key}'.")
    return all_data
