import os
import json
import http.client
from pprint import pprint
import feedparser
import time
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, Set
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import concurrent.futures
import threading
from boilerpy3 import extractors
boiler_extractor = extractors.ArticleExtractor()
from urllib.parse import quote
from .company_profile import (
    get_google_news_articles,llm_summarize_article,
    fetch_clean_text
)
from .generate_tags import generate_tags_for_summary
from .news_scrape import update_news_summary_for_company_key
import requests
from .ai_news_scraper import get_ai_news_insights
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Maximum number of news articles to return in the final result
# MAX_NEWS = 6 # Overall limit removed
MAX_NEWS_API = 4
MAX_REUTERS = 2
MAX_RSS_EACH = 2


def limit_summary_lines(summary: str, max_lines: int = 5) -> str:
    """Limit summary to specified number of lines"""
    if not summary:
        return summary
    
    lines = summary.strip().split('\n')
    if len(lines) <= max_lines:
        return summary
    
    # Take first max_lines and add ellipsis if truncated
    limited_lines = lines[:max_lines]
    return '\n'.join(limited_lines) + '...'


def display_article_realtime(article: Dict, index: int):
    """Display a single article as it's processed"""
    print(f"\n{'='*60}")
    print(f"📰 Article {index}")
    print(f"{'='*60}")
    print(f"📌 Title: {article.get('title', 'N/A')}")
    print(f"🔗 Link: {article.get('link', 'N/A')}")
    print(f"📅 Published: {article.get('published', 'N/A')}")
    print(f"\n📝 Summary:")
    print(article.get('summary', 'No summary available'))
    
    tags = article.get('tags', {})
    if tags:
        print(f"\n🏷️  Tags: {json.dumps(tags)}")
    print(f"{'='*60}\n")

def is_title_similar(new_title: str, seen_titles: Set[str]) -> bool:
    """Check if a new title is similar to any of the seen titles."""
    new_title_lower = new_title.lower().strip()
    if not new_title_lower:
        return True # Treat empty titles as duplicates

    s1 = set(new_title_lower.split())
    if not s1:
        return True

    for seen_title in seen_titles:
        s2 = set(seen_title.split())
        try:
            similarity = len(s1.intersection(s2)) / len(s1.union(s2))
            if similarity > 0.8:
                return True
        except ZeroDivisionError:
            continue
    return False

def get_recent_news_with_time_options(company: str, time_option: str = "this_week", max_items: int = 10) -> List[Dict]:
    """
    Scrapes recent news articles with user-defined time options.
    Optimized for reduced API calls and better performance with real-time deduplication.
    
    Args:
        company (str): Company name to search for
        time_option (str): Time range option - "today", "this_week", "this_month", "this_year", "5_years"
        max_items (int): Maximum number of articles to return
    
    Returns:
        List[Dict]: List of news articles with metadata
    """
    # Define time ranges
    now = datetime.now(timezone.utc)
    time_ranges = {
        "today": now - timedelta(days=1),
        "this_week": now - timedelta(weeks=1),
        "this_month": now - timedelta(days=30),
        "this_year": now - timedelta(days=365),
        "5_years": now - timedelta(days=365 * 5)
    }
    
    if time_option not in time_ranges:
        raise ValueError(f"Invalid time option. Choose from: {list(time_ranges.keys())}")
    
    cutoff_date = time_ranges[time_option]
    print(f"🔍 Searching for {company} news from {cutoff_date.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    
    all_articles = []
    seen_urls = set()
    seen_titles = set()
    
    # Use only the most reliable source to reduce API calls
    # Priority: News API RapidAPI > Google News > RapidAPI Real-time
    try:
        print(f"[News API RapidAPI] Fetching news for query: {company}")
        # Fetch more articles to have a buffer for deduplication
        news_api_articles = get_news_api_rapid_articles(company, max_items=MAX_NEWS_API * 2)
        
        if news_api_articles:
            # Process articles efficiently
            articles_added = process_articles_efficiently(company, news_api_articles, all_articles, seen_urls, seen_titles, limit=MAX_NEWS_API)
            print(f"✅ Found {articles_added} valid News API RapidAPI articles")
            
            # If we have enough articles, skip other sources
            if len(all_articles) >= max_items:
                print(f"✅ Sufficient articles found ({len(all_articles)}), skipping additional sources")
            else:
                # Only fetch from Google News if we need more articles
                remaining_items = max_items - len(all_articles)
                try:
                    print(f"[RSS Sources] Fetching additional {remaining_items} articles")
                    rss_articles = get_rss_articles_concurrent(company, max_items=remaining_items)
                    filtered_rss = filter_articles_by_date(rss_articles, cutoff_date)
                    
                    rss_added = process_rss_articles_efficiently(company, filtered_rss, all_articles, seen_urls, seen_titles, max_items=6)
                    print(f"✅ Found {rss_added} additional RSS articles")
                except Exception as e:
                    print(f"⚠️ RSS Sources error: {e}")
        else:
            # Fallback to RSS Sources if News API fails
            print(f"[RSS Sources] News API failed, falling back to RSS sources")
            rss_articles = get_rss_articles_concurrent(company, max_items=max_items)
            filtered_rss = filter_articles_by_date(rss_articles, cutoff_date)
            
            rss_added = process_rss_articles_efficiently(company, filtered_rss, all_articles, seen_urls, seen_titles, max_items=6)
            print(f"✅ Found {rss_added} RSS articles")
            
    except Exception as e:
        print(f"⚠️ News API RapidAPI error: {e}")
        # Final fallback to RSS Sources
        try:
            print(f"[RSS Sources] Final fallback")
            rss_articles = get_rss_articles_concurrent(company, max_items=max_items)
            filtered_rss = filter_articles_by_date(rss_articles, cutoff_date)
            
            rss_added = process_rss_articles_efficiently(company, filtered_rss, all_articles, seen_urls, seen_titles, max_items=6)
            print(f"✅ Found {rss_added} RSS articles")
        except Exception as e:
            print(f"⚠️ RSS Sources error: {e}")
    
    # Final processing sequence: 1. Deduplicate (already done), 2. Sort
    # Sort by relevancy: High > Medium > Low > Other
    relevancy_order = {"High": 0, "Medium": 1, "Low": 2}
    all_articles.sort(key=lambda article: relevancy_order.get(article.get("tags", {}).get("relevancy"), 3))
    
    # The final list is no longer trimmed by an overall max
    final_articles = all_articles
    
    print(f"📰 Total unique articles found: {len(all_articles)}, returning top {len(final_articles)}")
    return final_articles

def process_articles_efficiently(company: str, articles: List[Dict], valid_articles: List[Dict], seen_urls: Set[str], seen_titles: Set[str], limit: int) -> int:
    """
    Process articles efficiently with reduced API calls and better error handling.
    Appends unique articles to valid_articles list.
    """
    initial_count = len(valid_articles)
    
    for idx, article in enumerate(articles):
        if len(valid_articles) - initial_count >= limit:
            break

        try:
            # Deduplication Check
            link = article.get("link", "").strip()
            title = article.get("title", "")
            if (link and link in seen_urls) or is_title_similar(title, seen_titles):
                continue
            
            print(f"Processing article {idx+1}: {article.get('title', '')[:50]}...")
            
            # Use scraped content if available, otherwise try to fetch
            text = article.get("scraped_content", "")
            if not text:
                text = fetch_clean_text(article.get("link", ""))
            
            # Generate summary efficiently (but don't skip if it fails)
            summary = None
            if text:
                summary = llm_summarize_article(company, article.get("title", ""), text)
                
                # Check if summary is valid
                if summary and summary.strip():
                    summary_lower = summary.strip().lower()
                    # Skip article if summary begins with apologetic responses
                    if (summary_lower.startswith("i'm sorry") or 
                        summary_lower.startswith("i apologize") or
                        summary_lower.startswith("sorry")):
                        summary = None  # Don't skip, just don't use the summary
                    else:
                        summary = limit_summary_lines(summary, max_lines=5)
            
            article["summary"] = summary
            
            # Generate tags efficiently (skip if not critical)
            try:
                scraped_content = article.get("scraped_content", "")
                article["tags"] = generate_tags_for_summary(
                    title=article.get('title', ''), 
                    summary=summary, 
                    target_company=company,
                    scraped_content=scraped_content
                ) if summary else {}
            except Exception as e:
                article["tags"] = {}
            
            # Generate AI insights efficiently (skip if not critical)
            try:
                ai_insights = get_ai_news_insights(text) if text else {"error": "No content available"}
                article["ai_insights"] = ai_insights
            except Exception as e:
                article["ai_insights"] = {"error": str(e)}
            
            article["match_score"] = compute_match_score(company, article.get("title", ""))
            
            # Add to lists
            valid_articles.append(article)
            if link: seen_urls.add(link)
            seen_titles.add(title.lower().strip())

            # Display progress
            display_article_realtime(article, len(valid_articles))
            
        except Exception as e:
            print(f"⚠️ Error processing article {idx+1}: {e}")
            
            # Include failed article with basic information
            failed_article = {
                "title": article.get("title", ""),
                "link": article.get("link", ""),
                "published": article.get("published", ""),
                "source": article.get("source", ""),
                "summary": None,
                "tags": {},
                "ai_insights": {"error": "Failed to process article"},
                "match_score": compute_match_score(company, article.get("title", "")),
                "scraped_content": "",
                "processing_failed": True
            }
            # Add failed articles to ensure we don't re-process them, but don't count towards limit
            valid_articles.append(failed_article)
            
            # Display progress for failed article
            display_article_realtime(failed_article, len(valid_articles))
            continue
    
    return len(valid_articles) - initial_count

def get_recent_news_with_time_options_tracked(company: str, time_option: str, max_items: int, session_id: str, progress_dict: dict) -> List[Dict]:
    """
    Optimized version of get_recent_news_with_time_options that updates progress
    with reduced API calls and better streaming.
    """
    # Define time ranges
    now = datetime.now(timezone.utc)
    time_ranges = {
        "today": now - timedelta(days=1),
        "this_week": now - timedelta(weeks=1),
        "this_month": now - timedelta(days=30),
        "this_year": now - timedelta(days=365),
        "5_years": now - timedelta(days=365 * 5)
    }
    
    if time_option not in time_ranges:
        raise ValueError(f"Invalid time option. Choose from: {list(time_ranges.keys())}")
    
    cutoff_date = time_ranges[time_option]
    print(f"🔍 Searching for {company} news from {cutoff_date.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    
    all_articles = []
    seen_urls = set()
    seen_titles = set()
    
    # Use optimized approach with reduced API calls
    try:
        progress_dict[session_id]['message'] = f'Fetching news articles for {company}...'
        print(f"[News API RapidAPI] Fetching news for query: {company}")
        news_api_articles = get_news_api_rapid_articles(company, max_items=MAX_NEWS_API * 2)
        
        if news_api_articles:
            # Update total count
            progress_dict[session_id]['total'] = len(news_api_articles)
            
            # Process articles efficiently with progress tracking
            valid_articles_count = process_articles_tracked(company, news_api_articles, all_articles, seen_urls, seen_titles, session_id, progress_dict, limit=MAX_NEWS_API)
            print(f"✅ Found {valid_articles_count} valid News API RapidAPI articles")
            
            # If we have enough articles, skip other sources
            if len(all_articles) >= max_items:
                print(f"✅ Sufficient articles found ({len(all_articles)}), skipping additional sources")
            else:
                # Only fetch from RSS if we need more articles
                remaining_items = max_items - len(all_articles)
                try:
                    progress_dict[session_id]['message'] = f'Fetching additional articles from RSS sources...'
                    print(f"[RSS Sources] Fetching additional {remaining_items} articles")
                    rss_articles = get_rss_articles_concurrent(company, max_items=remaining_items)
                    filtered_rss = filter_articles_by_date(rss_articles, cutoff_date)
                    
                    # Update total count
                    current_total = progress_dict[session_id]['total']
                    progress_dict[session_id]['total'] = current_total + len(filtered_rss)
                    
                    rss_added = process_rss_articles_tracked(company, filtered_rss, all_articles, seen_urls, seen_titles, session_id, progress_dict, start_index=current_total, max_items=6)
                    print(f"✅ Found {rss_added} additional RSS articles")
                except Exception as e:
                    print(f"⚠️ RSS Sources error: {e}")
        else:
            # Fallback to RSS Sources if News API fails
            progress_dict[session_id]['message'] = f'News API failed, falling back to RSS sources...'
            print(f"[RSS Sources] News API failed, falling back to RSS sources")
            rss_articles = get_rss_articles_concurrent(company, max_items=max_items)
            filtered_rss = filter_articles_by_date(rss_articles, cutoff_date)
            
            progress_dict[session_id]['total'] = len(filtered_rss)
            rss_added = process_rss_articles_tracked(company, filtered_rss, all_articles, seen_urls, seen_titles, session_id, progress_dict, max_items=6)
            print(f"✅ Found {rss_added} RSS articles")
            
    except Exception as e:
        print(f"⚠️ News API RapidAPI error: {e}")
        # Final fallback to RSS Sources
        try:
            progress_dict[session_id]['message'] = f'Final fallback to RSS sources...'
            print(f"[RSS Sources] Final fallback")
            rss_articles = get_rss_articles_concurrent(company, max_items=max_items)
            filtered_rss = filter_articles_by_date(rss_articles, cutoff_date)
            
            progress_dict[session_id]['total'] = len(filtered_rss)
            rss_added = process_rss_articles_tracked(company, filtered_rss, all_articles, seen_urls, seen_titles, session_id, progress_dict, max_items=6)
            print(f"✅ Found {rss_added} RSS articles")
        except Exception as e:
            print(f"⚠️ RSS Sources error: {e}")
    
    # Final processing sequence: 1. Deduplicate (already done), 2. Sort
    # Sort by relevancy: High > Medium > Low > Other
    relevancy_order = {"High": 0, "Medium": 1, "Low": 2}
    all_articles.sort(key=lambda article: relevancy_order.get(article.get("tags", {}).get("relevancy"), 3))

    # The final list is no longer trimmed by an overall max
    final_articles = all_articles

    print(f"📰 Total unique articles found: {len(all_articles)}, returning top {len(final_articles)}")
    return final_articles

def get_recent_news_with_time_options_streaming(company: str, time_option: str, max_items: int, session_id: str, progress_dict: dict, send_progress_update) -> List[Dict]:
    """
    Streaming version of get_recent_news_with_time_options that sends SSE events.
    """
    # Define time ranges
    now = datetime.now(timezone.utc)
    time_ranges = {
        "today": now - timedelta(days=1),
        "this_week": now - timedelta(weeks=1),
        "this_month": now - timedelta(days=30),
        "this_year": now - timedelta(days=365),
        "5_years": now - timedelta(days=365 * 5)
    }
    
    if time_option not in time_ranges:
        raise ValueError(f"Invalid time option. Choose from: {list(time_ranges.keys())}")
    
    cutoff_date = time_ranges[time_option]
    print(f"🔍 Searching for {company} news from {cutoff_date.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")
    
    all_articles = []
    seen_urls = set()
    seen_titles = set()
    
    # Use optimized approach with SSE streaming
    try:
        send_progress_update({
            'message': f'Fetching news articles for {company}...'
        })
        print(f"[News API RapidAPI] Fetching news for query: {company}")
        news_api_articles = get_news_api_rapid_articles(company, max_items=MAX_NEWS_API * 2)
        
        if news_api_articles:
            # Update total count
            send_progress_update({
                'total': len(news_api_articles)
            })
            
            # Process articles efficiently with SSE streaming
            valid_articles_count = process_articles_streaming(company, news_api_articles, all_articles, seen_urls, seen_titles, session_id, progress_dict, send_progress_update, limit=MAX_NEWS_API)
            print(f"✅ Found {valid_articles_count} valid News API RapidAPI articles")
            
            # If we have enough articles, skip other sources
            if len(all_articles) >= max_items:
                print(f"✅ Sufficient articles found ({len(all_articles)}), skipping additional sources")
            else:
                # Only fetch from RSS if we need more articles
                remaining_items = max_items - len(all_articles)
                try:
                    send_progress_update({
                        'message': f'Fetching additional articles from RSS sources...'
                    })
                    print(f"[RSS Sources] Fetching additional {remaining_items} articles")
                    rss_articles = get_rss_articles_concurrent(company, max_items=remaining_items)
                    filtered_rss = filter_articles_by_date(rss_articles, cutoff_date)
                    
                    # Update total count
                    current_total = progress_dict[session_id]['total']
                    new_total = current_total + len(filtered_rss)
                    send_progress_update({
                        'total': new_total
                    })
                    
                    rss_added = process_articles_streaming(company, filtered_rss, all_articles, seen_urls, seen_titles, session_id, progress_dict, send_progress_update, start_index=current_total, limit=6)
                    print(f"✅ Found {rss_added} additional RSS articles")
                except Exception as e:
                    print(f"⚠️ RSS Sources error: {e}")
        else:
            # Fallback to RSS if News API fails
            send_progress_update({
                'message': f'News API failed, falling back to RSS sources...'
            })
            print(f"[RSS Sources] News API failed, falling back to RSS sources")
            rss_articles = get_rss_articles_concurrent(company, max_items=max_items)
            filtered_rss = filter_articles_by_date(rss_articles, cutoff_date)
            
            send_progress_update({
                'total': len(filtered_rss)
            })
            rss_added = process_articles_streaming(company, filtered_rss, all_articles, seen_urls, seen_titles, session_id, progress_dict, send_progress_update, limit=6)
            print(f"✅ Found {rss_added} RSS articles")
            
    except Exception as e:
        print(f"⚠️ News API RapidAPI error: {e}")
        # Final fallback to RSS Sources
        try:
            send_progress_update({
                'message': f'Final fallback to RSS sources...'
            })
            print(f"[RSS Sources] Final fallback")
            rss_articles = get_rss_articles_concurrent(company, max_items=max_items)
            filtered_rss = filter_articles_by_date(rss_articles, cutoff_date)
            
            send_progress_update({
                'total': len(filtered_rss)
            })
            rss_added = process_articles_streaming(company, filtered_rss, all_articles, seen_urls, seen_titles, session_id, progress_dict, send_progress_update, limit=6)
            print(f"✅ Found {rss_added} RSS articles")
        except Exception as e:
            print(f"⚠️ RSS Sources error: {e}")
    
    # Final processing sequence: 1. Deduplicate (already done), 2. Sort
    # Sort by relevancy: High > Medium > Low > Other
    relevancy_order = {"High": 0, "Medium": 1, "Low": 2}
    all_articles.sort(key=lambda article: relevancy_order.get(article.get("tags", {}).get("relevancy"), 3))

    # The final list is no longer trimmed by an overall max
    final_articles = all_articles
    
    print(f"📰 Total unique articles found: {len(all_articles)}, returning top {len(final_articles)}")
    return final_articles

def process_articles_tracked(company: str, articles: List[Dict], valid_articles: List[Dict], 
                           seen_urls: Set[str], seen_titles: Set[str], session_id: str, 
                           progress_dict: dict, start_index: int = 0, limit: int = 10) -> int:
    """
    Process articles efficiently with progress tracking.
    """
    initial_count = len(valid_articles)
    
    for idx, article in enumerate(articles):
        if len(valid_articles) - initial_count >= limit:
            break

        try:
            # Deduplication Check
            link = article.get("link", "").strip()
            title = article.get("title", "")
            if (link and link in seen_urls) or is_title_similar(title, seen_titles):
                continue

            # Update progress for each article
            current_index = start_index + idx + 1
            progress_dict[session_id]['processed'] = current_index
            progress_dict[session_id]['message'] = f'Processing article {current_index}/{progress_dict[session_id]["total"]}: {article.get("title", "")[:50]}...'
            
            print(f"Processing article {current_index}: {article.get('title', '')[:50]}...")
            
            # Use scraped content if available, otherwise try to fetch
            text = article.get("scraped_content", "")
            if not text:
                text = fetch_clean_text(article.get("link", ""))
            
            # Generate summary efficiently (but don't skip if it fails)
            summary = None
            if text:
                summary = llm_summarize_article(company, article.get("title", ""), text)
                
                # Check if summary is valid
                if summary and summary.strip():
                    summary_lower = summary.strip().lower()
                    # Skip article if summary begins with apologetic responses
                    if (summary_lower.startswith("i'm sorry") or 
                        summary_lower.startswith("i apologize") or
                        summary_lower.startswith("sorry")):
                        summary = None  # Don't skip, just don't use the summary
                    else:
                        summary = limit_summary_lines(summary, max_lines=5)
            
            article["summary"] = summary
            
            # Generate tags efficiently (skip if not critical)
            try:
                progress_dict[session_id]['message'] = f'Generating tags for article {current_index}...'
                scraped_content = article.get("scraped_content", "")
                article["tags"] = generate_tags_for_summary(
                    title=article.get('title', ''), 
                    summary=summary, 
                    target_company=company,
                    scraped_content=scraped_content
                ) if summary else {}
            except Exception as e:
                article["tags"] = {}
            
            # Generate AI insights efficiently (skip if not critical)
            try:
                progress_dict[session_id]['message'] = f'Generating insights for article {current_index}...'
                ai_insights = get_ai_news_insights(text) if text else {"error": "No content available"}
                article["ai_insights"] = ai_insights
            except Exception as e:
                article["ai_insights"] = {"error": str(e)}
            
            article["match_score"] = compute_match_score(company, article.get("title", ""))
            
            # Add to lists
            valid_articles.append(article)
            if link: seen_urls.add(link)
            seen_titles.add(title.lower().strip())
            
            # Add to progress with more detailed info
            progress_dict[session_id]['articles'].append({
                'title': article.get('title', ''),
                'index': len(valid_articles),
                'status': 'completed'
            })
            
            # Update message for successful processing
            progress_dict[session_id]['message'] = f'Completed article {current_index}/{progress_dict[session_id]["total"]} ({len(valid_articles)} valid so far)'
            
            # Send individual article completion event for real-time display
            if '_event_queue' in progress_dict[session_id]:
                try:
                    event_queue = progress_dict[session_id]['_event_queue']
                    event_data = {
                        'event': 'article_complete',
                        'data': json.dumps({
                            'article': article,
                            'index': len(valid_articles),
                            'total': progress_dict[session_id]['total']
                        })
                    }
                    event_queue.append(f"data: {json.dumps(event_data)}\n\n")
                except Exception as e:
                    print(f"⚠️ Error sending article completion event: {e}")
            
        except Exception as e:
            print(f"⚠️ Error processing article {current_index}: {e}")
            progress_dict[session_id]['message'] = f'Error processing article {current_index}: {str(e)[:50]}...'
            
            # Include failed article with basic information
            failed_article = {
                "title": article.get("title", ""),
                "link": article.get("link", ""),
                "published": article.get("published", ""),
                "source": article.get("source", ""),
                "summary": None,
                "tags": {},
                "ai_insights": {"error": "Failed to process article"},
                "match_score": compute_match_score(company, article.get("title", "")),
                "scraped_content": "",
                "processing_failed": True
            }
            valid_articles.append(failed_article)
            
            # Add to progress with failed status
            progress_dict[session_id]['articles'].append({
                'title': article.get('title', ''),
                'index': len(valid_articles),
                'status': 'failed'
            })
            
            # Update message for failed processing
            progress_dict[session_id]['message'] = f'Failed to process article {current_index}/{progress_dict[session_id]["total"]} ({len(valid_articles)} processed so far)'
            continue
    
    return len(valid_articles) - initial_count

def process_articles_streaming(company: str, articles: List[Dict], valid_articles: List[Dict], 
                             seen_urls: Set[str], seen_titles: Set[str], session_id: str, 
                             progress_dict: dict, send_progress_update, start_index: int = 0, limit: int = 10) -> int:
    """
    Process articles efficiently with SSE streaming updates.
    """
    initial_count = len(valid_articles)
    
    for idx, article in enumerate(articles):
        if len(valid_articles) - initial_count >= limit:
            break
        
        try:
            # Deduplication Check
            link = article.get("link", "").strip()
            title = article.get("title", "")
            if (link and link in seen_urls) or is_title_similar(title, seen_titles):
                continue

            # Update progress for each article
            current_index = start_index + idx + 1
            progress_update = {
                'processed': current_index,
                'message': f'Processing article {current_index}/{progress_dict[session_id]["total"]}: {article.get("title", "")[:50]}...'
            }
            send_progress_update(progress_update)
            
            print(f"Processing article {current_index}: {article.get('title', '')[:50]}...")
            
            # Use scraped content if available, otherwise try to fetch
            text = article.get("scraped_content", "")
            if not text:
                text = fetch_clean_text(article.get("link", ""))
            
            # Generate summary efficiently (but don't skip if it fails)
            summary = None
            if text:
                summary = llm_summarize_article(company, article.get("title", ""), text)
                
                # Check if summary is valid
                if summary and summary.strip():
                    summary_lower = summary.strip().lower()
                    # Skip article if summary begins with apologetic responses
                    if (summary_lower.startswith("i'm sorry") or 
                        summary_lower.startswith("i apologize") or
                        summary_lower.startswith("sorry")):
                        summary = None  # Don't skip, just don't use the summary
                    else:
                        summary = limit_summary_lines(summary, max_lines=5)
            
            article["summary"] = summary
            
            # Generate tags efficiently (skip if not critical)
            try:
                scraped_content = article.get("scraped_content", "")
                article["tags"] = generate_tags_for_summary(
                    title=article.get('title', ''), 
                    summary=summary, 
                    target_company=company,
                    scraped_content=scraped_content
                ) if summary else {}
            except Exception as e:
                article["tags"] = {}
            
            # Generate AI insights efficiently (skip if not critical)
            try:
                ai_insights = get_ai_news_insights(text) if text else {"error": "No content available"}
                article["ai_insights"] = ai_insights
            except Exception as e:
                article["ai_insights"] = {"error": str(e)}
            
            article["match_score"] = compute_match_score(company, article.get("title", ""))
            
            # Add to lists
            valid_articles.append(article)
            if link: seen_urls.add(link)
            seen_titles.add(title.lower().strip())
            
            # Add to progress and send update
            progress_dict[session_id]['articles'].append({
                'title': article.get('title', ''),
                'index': len(valid_articles)
            })
            
            # Send article update
            send_progress_update({
                'articles': progress_dict[session_id]['articles']
            })
            
        except Exception as e:
            print(f"⚠️ Error processing article {current_index}: {e}")
            
            # Include failed article with basic information
            failed_article = {
                "title": article.get("title", ""),
                "link": article.get("link", ""),
                "published": article.get("published", ""),
                "source": article.get("source", ""),
                "summary": None,
                "tags": {},
                "ai_insights": {"error": "Failed to process article"},
                "match_score": compute_match_score(company, article.get("title", "")),
                "scraped_content": "",
                "processing_failed": True
            }
            valid_articles.append(failed_article)
            
            # Add to progress with failed status
            progress_dict[session_id]['articles'].append({
                'title': article.get('title', ''),
                'index': len(valid_articles),
                'status': 'failed'
            })
            
            # Send article update for failed article
            send_progress_update({
                'articles': progress_dict[session_id]['articles']
            })
            continue
    
    return len(valid_articles) - initial_count


# --- NEW AND ADJUSTED HELPER FUNCTIONS FOR REUTERS FINANCE API ---
def get_reuters_finance_articles(company: str, time_option: str) -> List[Dict]:
    """
    Fetches articles for a specific company from the Reuters Business and Financial News API.
    This version is adjusted to use the time_option parameter.
    """
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        print("Error: RAPIDAPI_KEY not set.")
        return []

    host = "reuters-business-and-financial-news.p.rapidapi.com"
    
    # Define time ranges, same as the main function
    now = datetime.now(timezone.utc)
    time_ranges = {
        "today": now - timedelta(days=1),
        "this_week": now - timedelta(weeks=1),
        "this_month": now - timedelta(days=30),
        "this_year": now - timedelta(days=365),
        "5_years": now - timedelta(days=365 * 5)
    }
    
    if time_option not in time_ranges:
        raise ValueError(f"Invalid time option. Choose from: {list(time_ranges.keys())}")
    
    # Set fromDate and toDate based on the selected time_option
    to_date = now
    from_date = time_ranges[time_option]
    
    to_date_str = to_date.strftime('%Y-%m-%d')
    from_date_str = from_date.strftime('%Y-%m-%d')
    
    # Construct the request URL based on the API documentation
    url = f"https://{host}/get-articles-by-keyword-name-date-range/{from_date_str}/{to_date_str}/{company}/1/{MAX_REUTERS}"
    
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": host
    }

    try:
        print(f"[Reuters Finance] Fetching news for query: {company} in range: {time_option}")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        api_data = response.json()
        articles = api_data.get("articles", [])

        normalized_results = []
        for item in articles:
            full_url = "https://www.reuters.com" + item.get("urlSupplier", "")
            normalized_results.append({
                "title": item.get("articlesName"),
                "link": full_url,
                "published": item.get("publishedAt", {}).get("date"),
                "summary": item.get("articlesShortDescription"),
                "source": "Reuters Finance"
            })
        return normalized_results

    except Exception as e:
        print(f"⚠️ Reuters Finance API error: {e}")
        return []

def process_finance_articles(company: str, articles: List[Dict], valid_articles: List[Dict], seen_urls: Set[str], seen_titles: Set[str]) -> int:
    """
    Processes a list of financial articles, adds unique ones to the list, and sorts by relevancy.
    """
    if not articles:
        return 0

    print("\nProcessing financial news articles...")
    initial_count = len(valid_articles)
    
    for idx, article in enumerate(articles):
        if len(valid_articles) - initial_count >= MAX_REUTERS:
            break

        try:
            # Deduplication Check
            link = article.get("link", "").strip()
            title = article.get("title", "")
            if (link and link in seen_urls) or is_title_similar(title, seen_titles):
                continue

            print(f"Processing finance article {idx+1}/{len(articles)}: {article.get('title', '')[:50]}...")
            # text = fetch_clean_text(article.get("link", ""))
            text = article.get("summary")
            summary = llm_summarize_article(company, article.get("title", ""), text) if text else article.get("summary")
            article["summary"] = limit_summary_lines(summary) if summary else "No summary available."
            
            article["tags"] = generate_tags_for_summary(
                title=article.get('title', ''), 
                summary=summary, 
                target_company=company,
                scraped_content=text
            ) if summary else {}
            
            article["ai_insights"] = get_ai_news_insights(text) if text else {"error": "No content available"}
            article["match_score"] = compute_match_score(company, article.get("title", ""))
            
            valid_articles.append(article)
            if link: seen_urls.add(link)
            seen_titles.add(title.lower().strip())

        except Exception as e:
            print(f"⚠️ Error processing finance article {article.get('title', '')[:50]}...: {e}")
            continue
    
    return len(valid_articles) - initial_count

# --- END OF NEW HELPER FUNCTIONS ---

# --- NEW get_news_with_summary FUNCTION WITH FINANCIAL NEWS INTEGRATION ---
def get_news_with_summary(company: str, time_option: str, max_items: int = 10) -> dict:
    """
    Get news articles with AI-generated executive summary.
    This version fetches general news and dedicated financial news separately,
    then combines and deduplicates them in real-time.
    
    Returns:
        dict: Complete company data with news and summary.
    """
    # 1. Get the general news articles using the existing logic
    print("--- Fetching General News ---")
    final_articles = get_recent_news_with_time_options(company, time_option, max_items)
    
    # The `get_recent_news_with_time_options` now returns a deduplicated list
    # We can create the seen sets from its result to pass to the finance processor
    seen_urls = {article.get('link', '').strip() for article in final_articles if article.get('link')}
    seen_titles = {article.get('title', '').lower().strip() for article in final_articles if article.get('title')}

    # 2. Get financial news articles and process them to select the top unique ones
    print("\n--- Fetching Financial News ---")
    finance_articles_raw = get_reuters_finance_articles(company, time_option)
    process_finance_articles(company, finance_articles_raw, final_articles, seen_urls, seen_titles)

    # 3. Sort the final combined list
    print("\n--- Sorting All News ---")
    relevancy_order = {"High": 0, "Medium": 1, "Low": 2}
    final_articles.sort(key=lambda article: relevancy_order.get(article.get("tags", {}).get("relevancy"), 3))
    
    company_key = company.lower().replace(" ", "-")
    company_data = {
        company_key: {
            "company_name": company,
            "news": final_articles,
            "total_articles": len(final_articles)
        }
    }
    
    # 4. Generate the final executive summary
    if final_articles:
        print("\n🤖 Generating final executive summary...")
        updated_data = update_news_summary_for_company_key(company_key, company_data)
        return updated_data[company_key]
    
    return company_data[company_key]


def get_news_with_summary_tracked(company: str, time_option: str, max_items: int, session_id: str, progress_dict: dict) -> dict:
    """Modified version of get_news_with_summary that tracks progress"""
    
    progress_dict[session_id]['status'] = 'searching'
    progress_dict[session_id]['message'] = f'Searching for {company} news...'
    
    articles = get_recent_news_with_time_options_tracked(company, time_option, max_items, session_id, progress_dict)
    
    seen_urls = {article.get('link', '').strip() for article in articles if article.get('link')}
    seen_titles = {article.get('title', '').lower().strip() for article in articles if article.get('title')}

    progress_dict[session_id]['message'] = 'Fetching financial news...'
    finance_articles_raw = get_reuters_finance_articles(company, time_option)
    process_finance_articles(company, finance_articles_raw, articles, seen_urls, seen_titles)
    
    progress_dict[session_id]['message'] = 'Sorting news...'
    final_articles = articles
    relevancy_order = {"High": 0, "Medium": 1, "Low": 2}
    final_articles.sort(key=lambda article: relevancy_order.get(article.get("tags", {}).get("relevancy"), 3))

    company_key = company.lower().replace(" ", "-")
    company_data = {
        company_key: {
            "company_name": company,
            "news": final_articles,
            "total_articles": len(final_articles)
        }
    }
    
    if final_articles:
        progress_dict[session_id]['status'] = 'summarizing'
        progress_dict[session_id]['message'] = 'Generating executive summary...'
        try:
            updated_data = update_news_summary_for_company_key(company_key, company_data)
            progress_dict[session_id]['status'] = 'complete'
            progress_dict[session_id]['message'] = 'Summary complete.'
            progress_dict[session_id]['complete'] = True
            progress_dict[session_id]['result'] = updated_data[company_key]
            return updated_data[company_key]
        except Exception as e:
            progress_dict[session_id]['status'] = 'error'
            progress_dict[session_id]['message'] = f"Summary error: {str(e)}"
            progress_dict[session_id]['complete'] = True
            progress_dict[session_id]['result'] = company_data[company_key]
            return company_data[company_key]
    else:
        progress_dict[session_id]['status'] = 'complete'
        progress_dict[session_id]['message'] = 'No articles found.'
        progress_dict[session_id]['complete'] = True
        progress_dict[session_id]['result'] = company_data[company_key]
        return company_data[company_key]

def get_news_with_summary_streaming(company: str, time_option: str, max_items: int, session_id: str, progress_dict: dict, send_sse_event=None) -> dict:
    """
    Streaming version of get_news_with_summary that sends SSE events
    """
    def send_progress_update(data):
        if send_sse_event:
            send_sse_event('progress', data)
        progress_dict[session_id].update(data)
    
    send_progress_update({
        'status': 'searching',
        'message': f'Searching for {company} news...',
        'processed': 0,
        'total': 0,
        'articles': []
    })
    
    articles = get_recent_news_with_time_options_streaming(company, time_option, max_items, session_id, progress_dict, send_progress_update)
    
    seen_urls = {article.get('link', '').strip() for article in articles if article.get('link')}
    seen_titles = {article.get('title', '').lower().strip() for article in articles if article.get('title')}

    send_progress_update({'message': 'Fetching financial news...'})
    finance_articles_raw = get_reuters_finance_articles(company, time_option)
    process_finance_articles(company, finance_articles_raw, articles, seen_urls, seen_titles) # This needs a streaming version if we want to show its progress
    
    send_progress_update({'message': 'Sorting news...'})
    final_articles = articles
    relevancy_order = {"High": 0, "Medium": 1, "Low": 2}
    final_articles.sort(key=lambda article: relevancy_order.get(article.get("tags", {}).get("relevancy"), 3))

    company_key = company.lower().replace(" ", "-")
    company_data = {
        company_key: {
            "company_name": company,
            "news": final_articles,
            "total_articles": len(final_articles)
        }
    }
    
    if final_articles:
        send_progress_update({
            'status': 'summarizing',
            'message': 'Generating executive summary...'
        })
        
        try:
            updated_data = update_news_summary_for_company_key(company_key, company_data)
            result = updated_data[company_key]
            
            send_progress_update({
                'status': 'complete',
                'message': 'Summary complete.',
                'complete': True,
                'result': result
            })
            
            return result
        except Exception as e:
            error_msg = f"Summary error: {str(e)}"
            send_progress_update({
                'status': 'error',
                'message': error_msg,
                'complete': True,
                'result': company_data[company_key]
            })
            return company_data[company_key]
    else:
        send_progress_update({
            'status': 'complete',
            'message': 'No articles found.',
            'complete': True,
            'result': company_data[company_key]
        })
        return company_data[company_key]

def filter_articles_by_date(articles: List[Dict], cutoff_date: datetime) -> List[Dict]:
    """Filter articles by publication date"""
    filtered = []
    for article in articles:
        try:
            article_date = parse_article_date(article.get("published", ""))
            if article_date and article_date >= cutoff_date:
                filtered.append(article)
        except:
            continue
    return filtered

def parse_article_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats to datetime object"""
    if not date_str:
        return None
    
    try:
        # Try parsing RFC 2822 format (from RSS feeds)
        return parsedate_to_datetime(date_str)
    except:
        pass
    
    try:
        # Try ISO format
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        pass
    
    try:
        # Try common formats
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
    except:
        pass
    
    return None

def get_news_api_rapid_articles(company: str, max_items: int = 4) -> List[Dict]:
    """Fetch articles using News API RapidAPI with optimized content extraction"""
    news_api_key = os.getenv("NEWS_API_KEY")
    if not news_api_key:
        raise RuntimeError("Please set NEWS_API_KEY in your .env file")
    
    base_url = "news-api14.p.rapidapi.com"
    headers = {
        'x-rapidapi-key': news_api_key,
        'x-rapidapi-host': base_url
    }
    
    try:
        # Build query parameters - request more articles to account for filtering
        params = {
            'query': company,
            'language': 'en',
            'limit': min(max_items * 2, 50)  # Request more but cap at 50
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
        
        print(f"📰 Found {len(articles_list)} articles from News API RapidAPI")
        
        processed_articles = []
        content_extraction_count = 0
        
        for article in articles_list:
            try:
                # Extract basic article info
                article_info = {
                    "title": article.get("title", ""),
                    "link": article.get("url", ""),
                    "published": article.get("date", ""),
                    "source": article.get("publisher", {}).get("name", "") if article.get("publisher") else "",
                    "author": article.get("authors", [""])[0] if article.get("authors") else "",
                    "description": article.get("excerpt", ""),
                    "keywords": article.get("keywords", []),
                    "content_length": article.get("contentLength", 0),
                    "language": article.get("language", ""),
                    "paywall": article.get("paywall", False)
                }
                
                # Only extract content for articles that look promising
                # Skip paywall articles and those without proper URLs
                if (article_info["link"] and 
                    not article_info["paywall"] and 
                    content_extraction_count < max_items):
                    
                    # Skip problematic domains
                    skip_domains = ['wsj.com', 'ft.com', 'nytimes.com', 'bloomberg.com', 'reuters.com']
                    if any(domain in article_info["link"].lower() for domain in skip_domains):
                        article_info["scraped_content"] = ""
                        continue
                    
                    print(f"🔍 Extracting content for: {article_info['title'][:50]}...")
                    article_info["scraped_content"] = extract_article_content_bs4(article_info["link"])
                    content_extraction_count += 1
                    
                    # Optimized delay for better performance
                    if content_extraction_count > 0 and content_extraction_count % 5 == 0:  # Only delay every 5th request
                        time.sleep(0.3)  # Reduced delay
                else:
                    article_info["scraped_content"] = ""
                
                processed_articles.append(article_info)
                
                # Stop if we have enough articles with content
                if len([a for a in processed_articles if a.get("scraped_content")]) >= max_items:
                    break
                
            except Exception as e:
                print(f"⚠️ Error processing article: {str(e)}")
                continue
        
        # Filter to only articles with content
        articles_with_content = [a for a in processed_articles if a.get("scraped_content")]
        print(f"✅ Successfully extracted content for {len(articles_with_content)} articles")
        
        return articles_with_content[:max_items]
        
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

"""
def get_realtime_news_filtered(company: str, cutoff_date: datetime, max_items: int = 20) -> List[Dict]:
    \"\"\"Enhanced RapidAPI news with date filtering\"\"\"
    url = "https://real-time-news-data.p.rapidapi.com/search"
    qs = {"query": company, "limit": str(max_items * 2), "country": "US", "lang": "en"}
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        raise RuntimeError("Please set RAPIDAPI_KEY in your .env file")
    hdr = {
        "x-rapidapi-host": "real-time-news-data.p.rapidapi.com",
        "x-rapidapi-key": rapidapi_key
    }
    
    try:
        r = requests.get(url, headers=hdr, params=qs, timeout=15)
        r.raise_for_status()
        items = r.json().get("data", [])
    except Exception as e:
        print(f"⚠️ RapidAPI fetch error: {e}")
        return []
    
    filtered_articles = []
    for item in items:
        try:
            article_date = parse_article_date(item.get("published_datetime_utc", ""))
            if article_date and article_date >= cutoff_date:
                url = item.get("link") or item.get("source_url", "")
                article_text = fetch_clean_text(url) if url else ""
                
                # Generate summary (but don't skip if it fails)
                summary = None
                if article_text:
                    summary = llm_summarize_article(company, item.get("title", ""), article_text)
                    
                    # Check if summary is valid
                    if summary and summary.strip():
                        summary_lower = summary.strip().lower()
                        # Skip article if summary begins with apologetic responses
                        if (summary_lower.startswith("i'm sorry") or 
                            summary_lower.startswith("i apologize") or
                            summary_lower.startswith("sorry")):
                            summary = None  # Don't skip, just don't use the summary
                        else:
                            summary = limit_summary_lines(summary, max_lines=5)
                
                filtered_articles.append({
                    "title": item.get("title", ""),
                    "link": url,
                    "published": item.get("published_datetime_utc", ""),
                    "summary": summary,
                })
        except Exception as e:
            continue
    
    return filtered_articles[:max_items]
"""

def remove_duplicate_articles(articles: List[Dict]) -> List[Dict]:
    """Remove duplicate articles based on URL and then title similarity."""
    if not articles:
        return []
    
    unique_articles = []
    seen_urls = set()
    seen_titles = set()
    
    for article in articles:
        link = article.get("link", "").strip()
        title = article.get("title", "").lower().strip()

        # Skip articles that have no title
        if not title:
            continue
        
        # 1. Check for duplicate URLs (most reliable)
        if link and link in seen_urls:
            continue
        
        # 2. Check for highly similar titles
        is_duplicate = False
        for seen_title in seen_titles:
            # Calculate Jaccard similarity for titles
            s1 = set(title.split())
            s2 = set(seen_title.split())
            try:
                similarity = len(s1.intersection(s2)) / len(s1.union(s2))
                if similarity > 0.8:  # Increased threshold for better accuracy
                    is_duplicate = True
                    break
            except ZeroDivisionError:
                continue # Should not happen if titles are not empty
        
        if not is_duplicate:
            if link:
                seen_urls.add(link)
            seen_titles.add(title)
            unique_articles.append(article)
            
    return unique_articles

def compute_match_score(search_key: str, title: str) -> int:
    """Compute TF-IDF cosine similarity between the search key and the news title, return as percent (0-100)."""
    if not search_key or not title:
        return 0
    vect = TfidfVectorizer().fit([search_key, title])
    tfidf = vect.transform([search_key, title])
    score = cosine_similarity(tfidf[0], tfidf[1])[0][0]
    percent = int(round(score * 100))
    return percent

"""
def get_bing_news_articles(company: str, query: str, max_items: int = 5) -> List[dict]:
    \"\"\"Fetch news from Bing News Search via RapidAPI.\"\"\"
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
"""


def get_bbc_news_articles(company: str, max_items: int = 2) -> List[dict]:
    """Fetch news articles from BBC RSS feeds"""
    rss_urls = [
        "http://feeds.bbci.co.uk/news/business/rss.xml",
        "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "http://feeds.bbci.co.uk/news/world/rss.xml"
    ]
    
    results = []
    for rss_url in rss_urls:
        try:
            print(f"[BBC News] Fetching from: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries:
                if len(results) >= max_items:
                    break
                    
                # Check if company name is mentioned in title or description
                title_text = entry.title.lower()
                desc_text = entry.get("description", "").lower()
                company_lower = company.lower()
                
                if company_lower in title_text:
                    print(f"[BBC News] Found relevant article: {entry.title}")
                    results.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get("published"),
                        "source": "BBC News"
                    })
                    
        except Exception as e:
            print(f"⚠️ BBC News error for {rss_url}: {e}")
            continue
            
    return results

def get_guardian_news_articles(company: str, max_items: int = 2) -> List[dict]:
    """Fetch news articles from The Guardian RSS feeds"""
    rss_urls = [
        "https://www.theguardian.com/business/rss",
        "https://www.theguardian.com/technology/rss",
        "https://www.theguardian.com/uk/rss"
    ]
    
    results = []
    for rss_url in rss_urls:
        try:
            print(f"[The Guardian] Fetching from: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries:
                if len(results) >= max_items:
                    break
                    
                # Check if company name is mentioned in title or description
                title_text = entry.title.lower()
                desc_text = entry.get("description", "").lower()
                company_lower = company.lower()
                
                if company_lower in title_text:
                    print(f"[The Guardian] Found relevant article: {entry.title}")
                    results.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get("published"),
                        "source": "The Guardian"
                    })
                    
        except Exception as e:
            print(f"⚠️ The Guardian error for {rss_url}: {e}")
            continue
            
    return results

def get_bloomberg_news_articles(company: str, max_items: int = 2) -> List[dict]:
    """Fetch news articles from Bloomberg RSS feeds"""
    rss_urls = [
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.bloomberg.com/technology/news.rss"
    ]
    
    results = []
    for rss_url in rss_urls:
        try:
            print(f"[Bloomberg] Fetching from: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries:
                if len(results) >= max_items:
                    break
                    
                # Check if company name is mentioned in title or description
                title_text = entry.title.lower()
                desc_text = entry.get("description", "").lower()
                company_lower = company.lower()
                
                if company_lower in title_text:
                    print(f"[Bloomberg] Found relevant article: {entry.title}")
                    results.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.get("published"),
                        "source": "Bloomberg"
                    })
                    
        except Exception as e:
            print(f"⚠️ Bloomberg error for {rss_url}: {e}")
            continue
            
    return results

def get_rss_articles_concurrent(company: str, max_items: int = 6) -> List[dict]:
    """Fetch articles from multiple RSS sources concurrently"""
    print(f"[RSS Sources] Fetching articles from multiple RSS sources for: {company}")
    
    def fetch_and_filter_source(source_func, source_name):
        """Helper function to fetch articles from a single source"""
        try:
            print(f"[{source_name}] Starting fetch...")
            articles = source_func(company, max_items=MAX_RSS_EACH)
            print(f"[{source_name}] Found {len(articles)} relevant articles")
            return articles, source_name
        except Exception as e:
            print(f"⚠️ {source_name} error: {e}")
            return [], source_name
    
    # Use ThreadPoolExecutor to fetch articles concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all source fetching tasks
        future_to_source = {
            executor.submit(fetch_and_filter_source, get_bbc_news_articles, "BBC News"): "BBC News",
            executor.submit(fetch_and_filter_source, get_guardian_news_articles, "The Guardian"): "The Guardian", 
            executor.submit(fetch_and_filter_source, get_bloomberg_news_articles, "Bloomberg"): "Bloomberg"
        }
        
        # Collect results as they complete
        combined_articles = []
        for future in concurrent.futures.as_completed(future_to_source):
            source_name = future_to_source[future]
            try:
                articles, name = future.result(timeout=60)  # 60 second timeout per source
                combined_articles.extend(articles)
                print(f"[{name}] Completed fetching")
                    
            except concurrent.futures.TimeoutError:
                print(f"⚠️ {source_name} timed out")
            except Exception as e:
                print(f"⚠️ {source_name} failed: {e}")
    
    print(f"[RSS Sources] Total articles found: {len(combined_articles)}")
    return combined_articles

def process_rss_articles_efficiently(company: str, articles: List[Dict], valid_articles: List[Dict], seen_urls: Set[str], seen_titles: Set[str], max_items: int = 6) -> int:
    """
    Process RSS articles efficiently with their own limit (independent of other sources).
    """
    initial_count = len(valid_articles)
    
    for idx, article in enumerate(articles):
        # Check RSS limit (independent of other sources)
        if len(valid_articles) - initial_count >= max_items:
            print(f"✅ Reached RSS limit of {max_items} articles, stopping RSS processing")
            break
            
        try:
            # Deduplication Check
            link = article.get("link", "").strip()
            title = article.get("title", "")
            if (link and link in seen_urls) or is_title_similar(title, seen_titles):
                continue

            print(f"Processing RSS article {idx+1}: {article.get('title', '')[:50]}...")
            
            # Use scraped content if available, otherwise try to fetch
            text = article.get("scraped_content", "")
            if not text:
                text = fetch_clean_text(article.get("link", ""))
                # Store the extracted content for tag generation
                if text:
                    article["scraped_content"] = text
            
            # Generate summary efficiently (but don't skip if it fails)
            summary = None
            if text:
                summary = llm_summarize_article(company, article.get("title", ""), text)
                
                # Check if summary is valid
                if summary and summary.strip():
                    summary_lower = summary.strip().lower()
                    # Skip article if summary begins with apologetic responses
                    if (summary_lower.startswith("i'm sorry") or 
                        summary_lower.startswith("i apologize") or
                        summary_lower.startswith("sorry")):
                        summary = None  # Don't skip, just don't use the summary
                    else:
                        summary = limit_summary_lines(summary, max_lines=5)
            
            article["summary"] = summary
            
            # Generate tags efficiently (skip if not critical)
            try:
                scraped_content = article.get("scraped_content", "")
                # For RSS articles, use the summary if no scraped_content is available
                if not scraped_content and article.get("summary"):
                    scraped_content = article.get("summary")
                
                article["tags"] = generate_tags_for_summary(
                    title=article.get('title', ''), 
                    summary=summary, 
                    target_company=company,
                    scraped_content=scraped_content
                ) if summary else {}
            except Exception as e:
                print(f"⚠️ Error generating tags for RSS article: {e}")
                article["tags"] = {}
            
            # Generate AI insights efficiently (skip if not critical)
            try:
                ai_insights = get_ai_news_insights(text) if text else {"error": "No content available"}
                article["ai_insights"] = ai_insights
            except Exception as e:
                article["ai_insights"] = {"error": str(e)}
            
            article["match_score"] = compute_match_score(company, article.get("title", ""))
            
            # Add to lists
            valid_articles.append(article)
            if link: seen_urls.add(link)
            seen_titles.add(title.lower().strip())
            
            # Display progress
            display_article_realtime(article, len(valid_articles))
            
        except Exception as e:
            print(f"⚠️ Error processing RSS article {idx+1}: {e}")
            
            # Include failed RSS article with basic information
            failed_article = {
                "title": article.get("title", ""),
                "link": article.get("link", ""),
                "published": article.get("published", ""),
                "source": article.get("source", ""),
                "summary": None,
                "tags": {},
                "ai_insights": {"error": "Failed to process RSS article"},
                "match_score": compute_match_score(company, article.get("title", "")),
                "scraped_content": "",
                "processing_failed": True
            }
            valid_articles.append(failed_article)
            
            # Display progress for failed article
            display_article_realtime(failed_article, len(valid_articles))
            continue
    
    return len(valid_articles) - initial_count

def process_rss_articles_tracked(company: str, articles: List[Dict], valid_articles: List[Dict], seen_urls: Set[str], seen_titles: Set[str], session_id: str, progress_dict: dict, start_index: int = 0, max_items: int = 6) -> int:
    """
    Process RSS articles efficiently with progress tracking and their own limit.
    """
    initial_count = len(valid_articles)
    
    for idx, article in enumerate(articles):
        # Check RSS limit (independent of other sources)
        if len(valid_articles) - initial_count >= max_items:
            print(f"✅ Reached RSS limit of {max_items} articles, stopping RSS processing")
            break
            
        try:
            # Deduplication Check
            link = article.get("link", "").strip()
            title = article.get("title", "")
            if (link and link in seen_urls) or is_title_similar(title, seen_titles):
                continue
            
            # Update progress for each article
            current_index = start_index + idx + 1
            progress_dict[session_id]['processed'] = current_index
            progress_dict[session_id]['message'] = f'Processing RSS article {current_index}/{progress_dict[session_id]["total"]}: {article.get("title", "")[:50]}...'
            
            print(f"Processing RSS article {current_index}: {article.get('title', '')[:50]}...")
            
            # Use scraped content if available, otherwise try to fetch
            text = article.get("scraped_content", "")
            if not text:
                text = fetch_clean_text(article.get("link", ""))
                # Store the extracted content for tag generation
                if text:
                    article["scraped_content"] = text
            
            # Generate summary efficiently (but don't skip if it fails)
            summary = None
            if text:
                summary = llm_summarize_article(company, article.get("title", ""), text)
                
                # Check if summary is valid
                if summary and summary.strip():
                    summary_lower = summary.strip().lower()
                    # Skip article if summary begins with apologetic responses
                    if (summary_lower.startswith("i'm sorry") or 
                        summary_lower.startswith("i apologize") or
                        summary_lower.startswith("sorry")):
                        summary = None  # Don't skip, just don't use the summary
                    else:
                        summary = limit_summary_lines(summary, max_lines=5)
            
            article["summary"] = summary
            
            # Generate tags efficiently (skip if not critical)
            try:
                progress_dict[session_id]['message'] = f'Generating tags for RSS article {current_index}...'
                scraped_content = article.get("scraped_content", "")
                # For RSS articles, use the summary if no scraped_content is available
                if not scraped_content and article.get("summary"):
                    scraped_content = article.get("summary")
                
                article["tags"] = generate_tags_for_summary(
                    title=article.get('title', ''), 
                    summary=summary, 
                    target_company=company,
                    scraped_content=scraped_content
                ) if summary else {}
            except Exception as e:
                print(f"⚠️ Error generating tags for RSS article: {e}")
                article["tags"] = {}
            
            # Generate AI insights efficiently (skip if not critical)
            try:
                progress_dict[session_id]['message'] = f'Generating insights for RSS article {current_index}...'
                ai_insights = get_ai_news_insights(text) if text else {"error": "No content available"}
                article["ai_insights"] = ai_insights
            except Exception as e:
                article["ai_insights"] = {"error": str(e)}
            
            article["match_score"] = compute_match_score(company, article.get("title", ""))
            
            # Add to lists
            valid_articles.append(article)
            if link: seen_urls.add(link)
            seen_titles.add(title.lower().strip())
            
            # Add to progress with more detailed info
            progress_dict[session_id]['articles'].append({
                'title': article.get('title', ''),
                'index': len(valid_articles),
                'status': 'completed'
            })
            
            # Update message for successful processing
            progress_dict[session_id]['message'] = f'Completed RSS article {current_index}/{progress_dict[session_id]["total"]} ({len(valid_articles)} valid so far)'
            
            # Send individual article completion event for real-time display
            if '_event_queue' in progress_dict[session_id]:
                try:
                    event_queue = progress_dict[session_id]['_event_queue']
                    event_data = {
                        'event': 'article_complete',
                        'data': json.dumps({
                            'article': article,
                            'index': len(valid_articles),
                            'total': progress_dict[session_id]['total']
                        })
                    }
                    event_queue.append(f"data: {json.dumps(event_data)}\n\n")
                except Exception as e:
                    print(f"⚠️ Error sending RSS article completion event: {e}")
            
        except Exception as e:
            print(f"⚠️ Error processing RSS article {current_index}: {e}")
            progress_dict[session_id]['message'] = f'Error processing RSS article {current_index}: {str(e)[:50]}...'
            
            # Include failed RSS article with basic information
            failed_article = {
                "title": article.get("title", ""),
                "link": article.get("link", ""),
                "published": article.get("published", ""),
                "source": article.get("source", ""),
                "summary": None,
                "tags": {},
                "ai_insights": {"error": "Failed to process RSS article"},
                "match_score": compute_match_score(company, article.get("title", "")),
                "scraped_content": "",
                "processing_failed": True
            }
            valid_articles.append(failed_article)
            
            # Add to progress with failed status
            progress_dict[session_id]['articles'].append({
                'title': article.get('title', ''),
                'index': len(valid_articles),
                'status': 'failed'
            })
            
            # Update message for failed processing
            progress_dict[session_id]['message'] = f'Failed to process RSS article {current_index}/{progress_dict[session_id]["total"]} ({len(valid_articles)} processed so far)'
            continue
    
    return len(valid_articles) - initial_count
