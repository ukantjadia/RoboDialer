import os
import json
import re
import warnings
import http.client
import time
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

from bs4 import BeautifulSoup, GuessedAtParserWarning
warnings.filterwarnings("ignore", category=GuessedAtParserWarning)

import feedparser
import wikipedia
import wptools
import yfinance as yf
import requests
from textblob import TextBlob
from dotenv import load_dotenv

from newspaper import Article
from boilerpy3 import extractors
boiler_extractor = extractors.ArticleExtractor()

# ─── Configuration ──────────────────────────────────────────────────────────────
MAX_TOKENS = 1024

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("Please set DEEPSEEK_API_KEY in your .env file")

def llm_chat(prompt: str) -> Optional[str]:
    """
    Calls DeepSeek's chat completion API with the given prompt.
    """
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
            ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ DeepSeek call failed ({e}).")
        return None

def tag_sentiment(text: str) -> dict:
    blob = TextBlob(text)
    return {"polarity": blob.sentiment.polarity,
            "subjectivity": blob.sentiment.subjectivity}

def get_homepage_info(website: str) -> dict:
    try:
        r = requests.get(website, timeout=10)
        r.raise_for_status()
    except:
        return {}
    soup = BeautifulSoup(r.text, "lxml")
    meta = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta["content"].strip() if meta and meta.get("content") else None
    first_h1  = soup.find("h1").get_text().strip() if soup.find("h1") else None
    first_p   = soup.find("p").get_text().strip() if soup.find("p") else None

    headers = []
    for lvl in range(1,7):
        for tag in soup.find_all(f"h{lvl}"):
            txt = tag.get_text().strip()
            if txt:
                headers.append({"tag": f"h{lvl}", "text": txt})

    return {
        "meta_description":  meta_desc,
        "first_h1":          first_h1,
        "homepage_snippet":  first_p,
        "headers":           headers
    }

def get_wikipedia_description(company: str) -> Optional[str]:
    try:
        page = wikipedia.page(company, auto_suggest=False)
    except wikipedia.DisambiguationError as e:
        choice = next((opt for opt in e.options if company.lower() in opt.lower()),
                      e.options[0])
        try:
            page = wikipedia.page(choice, auto_suggest=False)
        except:
            return None
    except:
        return None
    para = page.content.split("\n\n",1)[0]
    return re.sub(r"\[\d+\]", "", para).strip()

def get_wikipedia_infobox(company: str) -> dict:
    try:
        wp = wptools.page(company, silent=True)
        wp.get_parse()
        return wp.data.get("infobox",{}) or {}
    except:
        return {}

def fetch_clean_text(url: str) -> str:
    try:
        art = Article(url)
        art.download(); art.parse()
        return art.text or ""
    except:
        pass
    try:
        html = requests.get(url, timeout=10).text
        if "<html" not in html.lower():
            return ""
        return boiler_extractor.get_content(html)
    except:
        return ""

def llm_summarize_article(company: str, title: str, text: str) -> str:
    prompt = f"""
You are an expert news analyst for {company}.
Read the following article text and produce a 4–5 sentence summary,
focusing only on aspects relevant to {company}'s business, strategy, or products.

Title: {title}

Article text:
\"\"\"{text}\"\"\"
"""
    out = llm_chat(prompt)
    return out or ""

def get_bing_news_articles(company: str, query: str, max_items: int = 5) -> List[dict]:
    """Fetch news from Bing News Search via RapidAPI."""
    import requests
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        raise RuntimeError("Please set RAPIDAPI_KEY in your .env file")
    url = "https://bing-news-search1.p.rapidapi.com/news/search"
    headers = {
        "X-BingApis-SDK": "true",
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "bing-news-search1.p.rapidapi.com"
    }
    params = {
        "q": query,
        "count": str(max_items),
        "freshness": "Month",
        "textFormat": "Raw",
        "safeSearch": "Off",
        "mkt": "en-US"
    }
    try:
        print(f"[Bing News] Fetching news for query: {query}")
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("value", [])[:max_items]:
            print(f"[Bing News] Got: {item.get('name', '')}")
            results.append({
                "title": item.get("name", ""),
                "link": item.get("url", ""),
                "published": item.get("datePublished", ""),
                "summary": item.get("description", ""),
                "source": "Bing News"
            })
        return results
    except Exception as e:
        print(f"⚠️ Bing News API error: {e}")
        return []

def get_realtime_news_articles(company: str, query: str, max_items: int = 5) -> List[dict]:
    """Fetch news from Real-time News Data API via RapidAPI."""
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        raise RuntimeError("Please set RAPIDAPI_KEY in your .env file")
    url = "https://real-time-news-data.p.rapidapi.com/search"
    headers = {
        "x-rapidapi-host": "real-time-news-data.p.rapidapi.com",
        "x-rapidapi-key": rapidapi_key
    }
    params = {
        "query": query,
        "limit": str(max_items),
        "time_published": "anytime",
        "country": "US",
        "lang": "en"
    }
    try:
        print(f"[RealTime News] Fetching news for query: {query}")
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("data", [])[:max_items]:
            print(f"[RealTime News] Got: {item.get('title', '')}")
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "published": item.get("published_datetime_utc", ""),
                "summary": item.get("summary", ""),
                "source": "RealTime News"
            })
        return results
    except Exception as e:
        print(f"⚠️ RealTime News API error: {e}")
        return []

# Helper to merge and deduplicate news results by title

def merge_news_results(*news_lists, max_items=10):
    seen = set()
    merged = []
    for news_list in news_lists:
        for item in news_list:
            title = item.get("title", "").strip().lower()
            if title and title not in seen:
                seen.add(title)
                merged.append(item)
            if len(merged) >= max_items:
                return merged
    return merged

def get_news_api_rapid_articles(company: str, query: str, max_items: int = 5) -> List[dict]:
    """Fetch articles using News API RapidAPI with BeautifulSoup content extraction"""
    news_api_key = os.getenv("NEWS_API_KEY")
    if not news_api_key:
        print("⚠️ NEWS_API_KEY not found in environment variables")
        return []
    
    base_url = "news-api14.p.rapidapi.com"
    headers = {
        'x-rapidapi-key': news_api_key,
        'x-rapidapi-host': base_url
    }
    
    try:
        # Build query parameters
        params = {
            'query': query,
            'language': 'en',
            'limit': max_items
        }
        
        # Build query string
        query_string = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
        
        # Make request
        conn = http.client.HTTPSConnection(base_url)
        conn.request("GET", f"/v2/search/articles?{query_string}", headers=headers)
        
        response = conn.getresponse()
        data = response.read()
        
        if response.status != 200:
            print(f"⚠️ News API request failed with status {response.status}")
            return []
        
        response_data = json.loads(data.decode("utf-8"))
        articles_list = response_data.get("data", [])
        
        results = []
        for article in articles_list:
            try:
                print(f"[News API RapidAPI] Got: {article.get('title', '')}")
                
                # Extract full content using BeautifulSoup
                url = article.get("url", "")
                text = ""
                if url:
                    text = extract_article_content_bs4(url)
                    time.sleep(1)  # Be respectful to servers
                
                # If BeautifulSoup extraction failed, try newspaper3k
                if not text:
                    text = fetch_clean_text(url)
                
                summary = llm_summarize_article(company, article.get("title", ""), text) if text else ""
                
                results.append({
                    "title": article.get("title", ""),
                    "link": url,
                    "published": article.get("date", ""),
                    "summary": summary,
                    "source": "News API RapidAPI",
                    "author": article.get("authors", [""])[0] if article.get("authors") else "",
                    "description": article.get("excerpt", ""),
                    "keywords": article.get("keywords", []),
                    "scraped_content": text
                })
                
            except Exception as e:
                print(f"⚠️ Error processing News API article: {str(e)}")
                continue
        
        return results
        
    except Exception as e:
        print(f"⚠️ News API RapidAPI error: {e}")
        return []

def extract_article_content_bs4(url: str) -> str:
    """Extract article content from URL using BeautifulSoup"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Try to find main content areas
        content_selectors = [
            'article',
            '[role="main"]',
            '.content',
            '.article-content',
            '.post-content',
            '.entry-content',
            'main',
            '.main-content'
        ]
        
        content = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = " ".join([elem.get_text(strip=True) for elem in elements])
                if len(content) > 100:  # Ensure we have substantial content
                    break
        
        # If no specific content area found, get body text
        if not content or len(content) < 100:
            content = soup.get_text(strip=True)
        
        # Clean up the content
        content = " ".join(content.split())  # Remove extra whitespace
        
        return content[:3000]  # Limit content length for processing
        
    except Exception as e:
        print(f"⚠️ Error extracting content from {url}: {str(e)}")
        return ""

def get_google_news_articles(company: str,
                             query: str,
                             max_items: int = 5) -> List[dict]:
    rss_url = (
        "https://news.google.com/rss/search?"
        f"q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    )
    print(f"[Google News] Fetching news for query: {query}")
    feed = feedparser.parse(rss_url)
    results = []
    for entry in feed.entries[:max_items]:
        print(f"[Google News] Got: {entry.title}")
        text    = fetch_clean_text(entry.link)
        summary = llm_summarize_article(company, entry.title, text) if text else ""
        results.append({
            "title":     entry.title,
            "link":      entry.link,
            "published": entry.get("published"),
            "summary":   summary,
            "source":    "Google News"
        })
    # Also fetch News API RapidAPI, Bing News and RealTime News and merge
    try:
        news_api_results = get_news_api_rapid_articles(company, query, max_items)
        bing_results = get_bing_news_articles(company, query, max_items)
        realtime_results = get_realtime_news_articles(company, query, max_items)
        results = merge_news_results(results, news_api_results, bing_results, realtime_results, max_items=max_items)
    except Exception as e:
        print(f"⚠️ News API/Bing/RealTime News integration error: {e}")
    return results

def filter_recent_articles(arts: List[dict], days: int = 30) -> List[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for a in arts:
        try:
            dt = parsedate_to_datetime(a["published"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                out.append(a)
        except:
            continue
    return out

def extract_keywords(company: str, context: str,
                     max_keywords: int = 5) -> List[str]:
    prompt = f"""
Extract up to {max_keywords} key phrases (2–4 words each)
describing {company}'s core business:
\"\"\"{context}\"\"\"
Return ONLY a JSON array of strings.
"""
    raw = llm_chat(prompt)
    try:
        return json.loads(re.sub(r"^```[a-z]*|```$", "", raw, flags=re.I))
    except:
        return []

def get_stock_info(infobox: dict) -> dict:
    ticker = None
    for key in ("ticker","traded_as","stock_symbol"):
        val = infobox.get(key)
        if isinstance(val,str):
            m = re.search(r"[A-Za-z.]+$", val)
            if m:
                ticker = m.group(0); break
    if not ticker:
        return {}
    try:
        info = yf.Ticker(ticker).info
        return {
            "current_price":  info.get("regularMarketPrice"),
            "market_cap":     info.get("marketCap"),
            "pe_ratio":       info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
            "beta":           info.get("beta"),
        }
    except:
        return {}

def build_full_profile(company: str,
                       website: str,
                       max_news: int = 5) -> dict:
    """Run the full company_profile pipeline headlessly."""
    homepage     = get_homepage_info(website)
    wiki_summary = get_wikipedia_description(company)
    wiki_info    = get_wikipedia_infobox(company)
    context      = "\n\n".join(filter(None,
                        [homepage.get("homepage_snippet"), wiki_summary]))
    keywords     = extract_keywords(company, context)[:2]
    query        = company if not keywords else (
                   f"{company} AND ({keywords[0]} OR {keywords[1]})")
    raw_news     = get_google_news_articles(company, query, max_items=max_news)
    recent_news  = filter_recent_articles(raw_news)
    stock        = get_stock_info(wiki_info)

    profile = {
        "homepage":    homepage,
        "wikipedia":   {"summary": wiki_summary,
                        "infobox": wiki_info},
        "recent_news": recent_news
    }
    if stock:
        profile["stock_info"] = stock

    return profile
