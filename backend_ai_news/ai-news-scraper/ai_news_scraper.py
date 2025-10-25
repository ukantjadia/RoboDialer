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
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkcalendar import DateEntry
import threading

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
    def __init__(self, gemini_api_key: str, groq_api_key: str):
        self.gemini_api_key = gemini_api_key
        self.groq_api_key = groq_api_key
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        
    def analyze_with_gemini(self, content: str) -> Dict:
        """Analyze content using Gemini API"""
        headers = {
            'Content-Type': 'application/json'
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"""You are an AI news analyst. Analyze the given AI news content and provide:
1. A concise summary (2-3 sentences)
2. Key insights as bullet points (3-5 points)
3. Impact assessment on the AI industry

Format your response as JSON with keys: summary, insights, impact

Analyze this AI news content:

{content[:3000]}"""
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 1000
            }
        }
        
        try:
            response = requests.post(
                f"{self.gemini_url}?key={self.gemini_api_key}", 
                headers=headers, 
                json=payload, 
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if 'candidates' in result and len(result['candidates']) > 0:
                content = result['candidates'][0]['content']['parts'][0]['text']
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"summary": content, "insights": [content], "impact": "Analysis provided"}
            return {"summary": "Analysis unavailable", "insights": [], "impact": "Unknown"}
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {"summary": "Analysis failed", "insights": [], "impact": "Unknown"}
    
    def analyze_with_groq(self, content: str) -> Dict:
        """Analyze content using Groq API"""
        headers = {
            'Authorization': f'Bearer {self.groq_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "llama3-70b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": """You are an expert AI industry analyst. Analyze the given AI news and provide:
                    1. Executive summary (2-3 sentences)
                    2. Key technical insights (3-5 bullet points)
                    3. Market implications
                    
                    Respond in JSON format with keys: summary, insights, market_impact"""
                },
                {
                    "role": "user",
                    "content": f"Analyze this AI news:\n\n{content[:3000]}"
                }
            ],
            "temperature": 0.2,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(self.groq_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"summary": content, "insights": [content], "market_impact": "Analysis provided"}
            return {"summary": "Analysis unavailable", "insights": [], "market_impact": "Unknown"}
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return {"summary": "Analysis failed", "insights": [], "market_impact": "Unknown"}

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
                # Analyze with Gemini
                gemini_analysis = self.analyzer.analyze_with_gemini(article.content)
                
                # Analyze with Groq
                groq_analysis = self.analyzer.analyze_with_groq(article.content)
                
                # Combine insights
                combined_insights = []
                
                if gemini_analysis.get('insights'):
                    if isinstance(gemini_analysis['insights'], list):
                        combined_insights.extend(gemini_analysis['insights'])
                    else:
                        combined_insights.append(str(gemini_analysis['insights']))
                
                if groq_analysis.get('insights'):
                    if isinstance(groq_analysis['insights'], list):
                        combined_insights.extend(groq_analysis['insights'])
                    else:
                        combined_insights.append(str(groq_analysis['insights']))
                
                # Create comprehensive summary
                summary_parts = []
                if gemini_analysis.get('summary'):
                    summary_parts.append(gemini_analysis['summary'])
                if groq_analysis.get('summary'):
                    summary_parts.append(groq_analysis['summary'])
                
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

class ResultsWindow:
    def __init__(self, parent, articles: List[NewsArticle], target_date: datetime):
        self.window = tk.Toplevel(parent)
        self.window.title(f"AI News Results - {target_date.strftime('%Y-%m-%d')}")
        self.window.geometry("1000x700")
        self.window.configure(bg='#f0f0f0')
        
        # Main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text=f"🤖 AI News Digest - {target_date.strftime('%B %d, %Y')}", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        stats_label = ttk.Label(header_frame, text=f"📊 Total Articles: {len(articles)}", 
                               font=('Arial', 12))
        stats_label.grid(row=1, column=0, sticky=tk.W)
        
        # Scrollable text area
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.text_area = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=100, height=40,
                                                  font=('Consolas', 10))
        self.text_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        save_btn = ttk.Button(button_frame, text="💾 Save Results", 
                             command=lambda: self.save_results(articles, target_date))
        save_btn.grid(row=0, column=0, padx=(0, 10))
        
        close_btn = ttk.Button(button_frame, text="❌ Close", command=self.window.destroy)
        close_btn.grid(row=0, column=1)
        
        # Display results
        self.display_results(articles)
    
    def display_results(self, articles: List[NewsArticle]):
        """Display formatted results in the text area"""
        if not articles:
            self.text_area.insert(tk.END, "❌ No AI articles found for the selected date.\n")
            return
        
        for i, article in enumerate(articles, 1):
            # Article header
            self.text_area.insert(tk.END, f"\n{'='*80}\n")
            self.text_area.insert(tk.END, f"📰 ARTICLE {i}: {article.title}\n")
            self.text_area.insert(tk.END, f"{'='*80}\n")
            
            # Article details
            self.text_area.insert(tk.END, f"• 📅 Published: {article.published_date.strftime('%Y-%m-%d %H:%M')}\n")
            self.text_area.insert(tk.END, f"• 🔗 Source: {article.source}\n")
            self.text_area.insert(tk.END, f"• 🌐 URL: {article.url}\n\n")
            
            # Summary
            if article.summary:
                self.text_area.insert(tk.END, "📝 SUMMARY:\n")
                self.text_area.insert(tk.END, f"   {article.summary}\n\n")
            
            # Insights
            if article.insights:
                self.text_area.insert(tk.END, "🔍 KEY INSIGHTS:\n")
                for insight in article.insights:
                    if insight.strip():
                        self.text_area.insert(tk.END, f"   • {insight.strip()}\n")
                self.text_area.insert(tk.END, "\n")
            
            self.text_area.insert(tk.END, f"{'-'*80}\n")
        
        # Scroll to top
        self.text_area.see(tk.INSERT)
    
    def save_results(self, articles: List[NewsArticle], target_date: datetime):
        """Save results to file"""
        try:
            filename = f"ai_news_digest_{target_date.strftime('%Y%m%d')}.txt"
            content = self.text_area.get(1.0, tk.END)
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            messagebox.showinfo("Success", f"Results saved to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save results: {e}")

class AINewsScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 AI News Scraper")
        self.root.geometry("600x400")
        self.root.configure(bg='#f0f0f0')
        
        # Load environment variables
        load_dotenv()
        
        # Get API keys
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        
        # Initialize components
        self.analyzer = None
        self.scraper = None
        
        self.setup_ui()
        self.validate_api_keys()
    
    def setup_ui(self):
        """Setup the main UI"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🤖 AI News Scraper", 
                               font=('Arial', 20, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Date selection
        date_frame = ttk.LabelFrame(main_frame, text="📅 Select Date", padding="10")
        date_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(date_frame, text="Choose date to scrape AI news:").grid(row=0, column=0, sticky=tk.W)
        
        self.date_entry = DateEntry(date_frame, width=12, background='darkblue',
                                   foreground='white', borderwidth=2, 
                                   date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="📊 Progress", padding="10")
        progress_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.progress_var = tk.StringVar(value="Ready to scrape...")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        progress_frame.columnconfigure(0, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(0, 20))
        
        self.scrape_btn = ttk.Button(button_frame, text="🚀 Start Scraping", 
                                    command=self.start_scraping, style='Accent.TButton')
        self.scrape_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.exit_btn = ttk.Button(button_frame, text="❌ Exit", command=self.root.quit)
        self.exit_btn.grid(row=0, column=1)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                                font=('Arial', 10, 'italic'))
        status_label.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        # Configure column weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
    
    def validate_api_keys(self):
        """Validate API keys"""
        if not self.gemini_api_key or not self.groq_api_key:
            messagebox.showerror("Error", "API keys not found in environment variables!\n\n"
                               "Please add GEMINI_API_KEY and GROQ_API_KEY to your .env file")
            self.scrape_btn.config(state='disabled')
            self.status_var.set("❌ API keys missing")
        else:
            self.analyzer = AINewsAnalyzer(self.gemini_api_key, self.groq_api_key)
            self.scraper = AINewsScraper(self.analyzer)
            self.status_var.set("✅ Ready to scrape")
    
    def update_progress(self, current, total, message):
        """Update progress bar and message"""
        self.progress_var.set(f"{message} ({current}/{total})")
        self.progress_bar['value'] = (current / total) * 100
        self.root.update_idletasks()
    
    def start_scraping(self):
        """Start the scraping process in a separate thread"""
        if not self.analyzer or not self.scraper:
            messagebox.showerror("Error", "Please check API keys configuration")
            return
        
        selected_date = self.date_entry.get_date()
        target_date = datetime.combine(selected_date, datetime.min.time())
        
        # Disable button and show progress
        self.scrape_btn.config(state='disabled')
        self.progress_bar['value'] = 0
        self.status_var.set("🔄 Scraping in progress...")
        
        # Start scraping in thread
        thread = threading.Thread(target=self.scrape_worker, args=(target_date,))
        thread.daemon = True
        thread.start()
    
    def scrape_worker(self, target_date):
        """Worker thread for scraping"""
        try:
            # Step 1: Scrape articles
            self.progress_var.set("📡 Scraping AI news sources...")
            articles = self.scraper.scrape_all_sources(target_date, self.update_progress)
            
            if not articles:
                self.root.after(0, lambda: messagebox.showinfo("Info", 
                    f"No AI articles found for {target_date.strftime('%Y-%m-%d')}"))
                return
            
            # Step 2: Analyze articles
            self.progress_var.set("🧠 Analyzing articles with AI...")
            analyzed_articles = self.scraper.analyze_articles(articles, self.update_progress)
            
            # Step 3: Show results
            self.root.after(0, lambda: self.show_results(analyzed_articles, target_date))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Scraping failed: {e}"))
        finally:
            # Re-enable button
            self.root.after(0, lambda: self.scrape_btn.config(state='normal'))
            self.root.after(0, lambda: self.status_var.set("✅ Ready to scrape"))
            self.root.after(0, lambda: self.progress_var.set("Ready to scrape..."))
            self.root.after(0, lambda: setattr(self.progress_bar, 'value', 0))
    
    def show_results(self, articles, target_date):
        """Show results in a new window"""
        ResultsWindow(self.root, articles, target_date)

def main():
    """Main execution function"""
    root = tk.Tk()
    app = AINewsScraperGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()