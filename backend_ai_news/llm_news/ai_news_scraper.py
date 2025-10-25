#!/usr/bin/env python3
"""
Advanced AI News Scraper with Gemini & Groq Integration
GUI version with calendar date selection and formatted output window
"""

import requests
import json
import time
from datetime import datetime, timedelta
import feedparser
from bs4 import BeautifulSoup
import concurrent.futures
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse
import sys
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_news_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    title: str
    url: str
    source: str
    published_date: datetime
    content: str
    summary: str = ""
    insights: List[str] = None

class AINewsAnalyzer:
    def __init__(self, deepseek_api_key: str):
        self.deepseek_api_key = deepseek_api_key
        self.deepseek_url = "https://api.deepseek.com/v1/chat/completions"

    def analyze_with_deepseek(self, content: str) -> dict:
        """Analyze content using DeepSeek API"""
        headers = {
            'Authorization': f'Bearer {self.deepseek_api_key}',
            'Content-Type': 'application/json'
        }
        '''payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are an AI news analyst. Analyze the given AI news content and provide:\n1. A concise summary (2-3 sentences)\n2. Key insights as bullet points (3-5 points)\n3. Impact assessment on the AI industry\n\nFormat your response as JSON with keys: summary, insights, impact\n\nAnalyze this AI news content:"},
                {"role": "user", "content": content[:3000]}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }'''
        payload = {
    "model": "deepseek-chat",
    "messages": [
        {
            "role": "system", 
            "content": """You are an AI news analyst. Analyze the given AI news content and provide:
1. A concise summary (2-3 sentences)
2. Key insights as bullet points (2-3 points) - these should be strategic implications, not just summary points
3. Impact assessment on the AI industry

Format your response as JSON with keys: summary, insights, impact

Examples:

Example 1:
Summary: "OpenAI announced GPT-4 Turbo with improved reasoning capabilities and reduced costs. The model shows 40% better performance on coding tasks and supports 128K context length."
Insights: [
"Cost reduction could democratize access to advanced AI capabilities for smaller companies",
"Extended context length enables new use cases in document analysis and long-form content generation",
"Performance improvements in coding suggest potential disruption in software development workflows"
]

Example 2:
Summary: "Google's Gemini Pro achieved state-of-the-art results on multiple benchmarks, outperforming GPT-4 in mathematical reasoning. The model will be integrated into Google's product ecosystem."
Insights: [
"Mathematical reasoning breakthrough could accelerate AI adoption in scientific research and finance",
"Google's ecosystem integration strategy positions them to compete directly with OpenAI's market dominance",
"Benchmark improvements suggest we're approaching human-level performance in specialized domains"
]

Now analyze this AI news content:"""
        },
        {"role": "user", "content": content[:3000]}
    ],
    "temperature": 0.3,
    "max_tokens": 1000
}
        try:
            response = requests.post(self.deepseek_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                text = result['choices'][0]['message']['content']
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"summary": text, "insights": [text], "impact": "Analysis provided"}
            return {"summary": "Analysis unavailable", "insights": [], "impact": "Unknown"}
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return {"summary": "Analysis failed", "insights": [], "impact": "Unknown"}

class AINewsScraper:
    def __init__(self, analyzer: AINewsAnalyzer):
        self.analyzer = analyzer
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # AI News Sources
        self.news_sources = {
            'TechCrunch AI': 'https://techcrunch.com/feed/',
            'VentureBeat AI': 'https://venturebeat.com/feed/',
            'AI News': 'https://artificialintelligence-news.com/feed/',
            'The Verge AI': 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml',
            'MIT Technology Review': 'https://www.technologyreview.com/feed/',
            'OpenAI Blog': 'https://openai.com/blog/rss.xml',
            'Google AI Blog': 'https://ai.googleblog.com/feeds/posts/default',
            'Anthropic News': 'https://www.anthropic.com/news/rss.xml',
            'DeepMind Blog': 'https://deepmind.com/blog/rss.xml',
            'Hugging Face Blog': 'https://huggingface.co/blog/feed.xml'
        }
        
        # AI-related keywords for filtering
        self.ai_keywords = [
            'artificial intelligence', 'machine learning', 'deep learning', 'neural network',
            'AI model', 'GPT', 'transformer', 'LLM', 'large language model',
            'computer vision', 'natural language processing', 'NLP',
            'reinforcement learning', 'robotics', 'automation',
            'OpenAI', 'Anthropic', 'Google AI', 'DeepMind', 'Hugging Face',
            'ChatGPT', 'Claude', 'Gemini', 'Llama', 'Mistral'
        ]
    
    def is_ai_related(self, title: str, content: str) -> bool:
        """Check if article is AI-related"""
        text = f"{title} {content}".lower()
        return any(keyword.lower() in text for keyword in self.ai_keywords)
    
    def extract_article_content(self, url: str) -> str:
        """Extract full article content from URL"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try common content selectors
            content_selectors = [
                'article', '.post-content', '.entry-content', '.article-content',
                '.content', '.post-body', '.story-body', '.article-body',
                'main', '[role="main"]', '.main-content'
            ]
            
            content = ""
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(strip=True)
                    break
            
            if not content:
                content = soup.get_text(strip=True)
            
            # Clean up content
            content = re.sub(r'\s+', ' ', content)
            return content[:5000]  # Limit content length
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return ""
    
    def scrape_rss_feed(self, source_name: str, feed_url: str, target_date: datetime) -> List[NewsArticle]:
        """Scrape articles from RSS feed for a specific date"""
        articles = []
        
        try:
            logger.info(f"Scraping {source_name} for date {target_date.strftime('%Y-%m-%d')}...")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:20]:  # Check more articles for date filtering
                try:
                    # Parse publication date
                    pub_date = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])
                    
                    # Check if article is from the target date (same day)
                    if pub_date.date() != target_date.date():
                        continue
                    
                    # Extract content
                    content = entry.summary if hasattr(entry, 'summary') else ""
                    if len(content) < 200:  # If summary is too short, get full content
                        full_content = self.extract_article_content(entry.link)
                        if full_content:
                            content = full_content
                    
                    # Filter AI-related content
                    if self.is_ai_related(entry.title, content):
                        article = NewsArticle(
                            title=entry.title,
                            url=entry.link,
                            source=source_name,
                            published_date=pub_date,
                            content=content
                        )
                        articles.append(article)
                        
                except Exception as e:
                    logger.error(f"Error processing article from {source_name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping {source_name}: {e}")
        
        return articles
    
    def scrape_all_sources(self, target_date: datetime, progress_callback=None) -> List[NewsArticle]:
        """Scrape all news sources concurrently for a specific date"""
        all_articles = []
        completed_sources = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_source = {
                executor.submit(self.scrape_rss_feed, source, url, target_date): source
                for source, url in self.news_sources.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    completed_sources += 1
                    logger.info(f"Scraped {len(articles)} articles from {source}")
                    
                    if progress_callback:
                        progress_callback(completed_sources, len(self.news_sources), f"Scraped {source}")
                        
                except Exception as e:
                    logger.error(f"Error scraping {source}: {e}")
                    completed_sources += 1
                    if progress_callback:
                        progress_callback(completed_sources, len(self.news_sources), f"Error scraping {source}")
        
        # Remove duplicates and sort by date
        unique_articles = []
        seen_urls = set()
        
        for article in sorted(all_articles, key=lambda x: x.published_date, reverse=True):
            if article.url not in seen_urls:
                unique_articles.append(article)
                seen_urls.add(article.url)
        
        return unique_articles
    
    def analyze_articles(self, articles: List[NewsArticle], progress_callback=None) -> List[NewsArticle]:
        """Analyze articles using AI APIs"""
        analyzed_articles = []
        
        for i, article in enumerate(articles):
            logger.info(f"Analyzing article {i+1}/{len(articles)}: {article.title[:50]}...")
            
            if progress_callback:
                progress_callback(i+1, len(articles), f"Analyzing: {article.title[:30]}...")
            
            try:
                # Analyze with DeepSeek
                deepseek_analysis = self.analyzer.analyze_with_deepseek(article.content)
                
                # Combine insights
                combined_insights = []
                
                if deepseek_analysis.get('insights'):
                    if isinstance(deepseek_analysis['insights'], list):
                        combined_insights.extend(deepseek_analysis['insights'])
                    else:
                        combined_insights.append(str(deepseek_analysis['insights']))
                
                # Create comprehensive summary
                summary_parts = []
                if deepseek_analysis.get('summary'):
                    summary_parts.append(deepseek_analysis['summary'])
                
                article.summary = " | ".join(summary_parts) if summary_parts else "No summary available"
                article.insights = combined_insights[:5]  # Top 5 insights
                
                analyzed_articles.append(article)
                
                # Add delay to respect API rate limits
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error analyzing article {article.title}: {e}")
                article.summary = "Analysis failed"
                article.insights = []
                analyzed_articles.append(article)
        
        return analyzed_articles

# --- Utility function for programmatic use (no GUI) ---
def get_ai_news_insights(text: str) -> dict:
    """
    Analyze news text using DeepSeek, returning insights and summary.
    Loads API key from .env automatically.
    Returns a dict with keys: 'summary', 'insights', 'impact', 'raw'.
    """
    load_dotenv()
    deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
    if not deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY must be set in .env")
    analyzer = AINewsAnalyzer(deepseek_api_key)
    result = analyzer.analyze_with_deepseek(text)
    return {
        'summary': result.get('summary', ''),
        'insights': result.get('insights', []),
        'impact': result.get('impact', ''),
        'raw': result
    }

def main():
    """Main execution function"""
    # This function is now primarily for programmatic use, not GUI
    # For GUI, use AINewsScraperGUI
    load_dotenv()
    deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
    
    if not deepseek_api_key:
        print("API key not found in environment variables!")
        print("Please add DEEPSEEK_API_KEY to your .env file")
        return
    
    analyzer = AINewsAnalyzer(deepseek_api_key)
    scraper = AINewsScraper(analyzer)
    
    # Example usage for programmatic scraping
    selected_date = datetime.now()
    target_date = datetime.combine(selected_date, datetime.min.time())
    
    print(f"Scraping AI news for {target_date.strftime('%Y-%m-%d')}...")
    articles = scraper.scrape_all_sources(target_date)
    
    if not articles:
        print(f"No AI articles found for {target_date.strftime('%Y-%m-%d')}")
        return
    
    print(f"Analyzing {len(articles)} articles...")
    analyzed_articles = scraper.analyze_articles(articles)
    
    print("\n--- Analyzed Articles ---")
    for i, article in enumerate(analyzed_articles, 1):
        print(f"\n{'='*80}")
        print(f"📰 ARTICLE {i}: {article.title}")
        print(f"{'='*80}")
        print(f"• 📅 Published: {article.published_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"• 🔗 Source: {article.source}")
        print(f"• 🌐 URL: {article.url}")
        print(f"\n📝 SUMMARY:")
        print(f"   {article.summary}")
        print(f"\n🔍 KEY INSIGHTS:")
        for insight in article.insights:
            if insight.strip():
                print(f"   • {insight.strip()}")
        print(f"\n{'-'*80}")

if __name__ == "__main__":
    main()