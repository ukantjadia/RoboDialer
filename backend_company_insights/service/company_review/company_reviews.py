# company_reviews.py 

import asyncio
import requests
import json
import time
import os
import random
import textwrap
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from urllib.parse import quote_plus

# =============================================================================
# SECTION 1: HELPER FUNCTIONS
# =============================================================================
def is_similar_name(query_name, result_name):
    if not query_name or not result_name:
        return False
    q_lower = query_name.lower()
    r_lower = result_name.lower()
    if q_lower in r_lower or r_lower in q_lower:
        return True
    words1 = set(q_lower.split())
    words2 = set(r_lower.split())
    if len(words1) > 0 and len(words1 & words2) / len(words1) >= 0.7:
        return True
    return False

# =============================================================================
# SECTION 2: API AND SCRAPER FUNCTIONS (The 4 Steps)
# =============================================================================

# --- STEP 1: Google Maps Scraper ---
def is_relevant_business(business_name, company_name, address, location):
    business_words = set(business_name.lower().split())
    company_words = set(company_name.lower().split())
    if "results" in business_words or "search" in business_words:
        return False
    if company_words:
        overlap = len(business_words & company_words) / len(company_words)
        if overlap >= 0.7:
            return True
        if location and address:
            loc_parts = [part.strip().lower() for part in location.split(",")]
            address_lower = address.lower()
            if all(part in address_lower for part in loc_parts if part):
                return True
    return False

async def get_google_maps_review(browser, company_name, location=None):
    search_query = company_name if not location else f"{company_name} {location}"
    maps_url = "https://www.google.com/maps"

    page = await browser.new_page()
    try:
        await page.goto(maps_url, timeout=60000)
        await page.wait_for_selector("#searchboxinput", timeout=15000)
        await page.fill("#searchboxinput", search_query)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(5000)
        selectors = [ "a.hfpxzc", "div[role='article'] a", "a[href*='/place/']" ]
        for sel in selectors:
            try:
                if await page.query_selector(sel):
                    await page.click(sel)
                    await page.wait_for_timeout(5000)
                    break
            except Exception:
                pass

        try:
            business_name = await page.locator('h1.DUwDvf.lfPIob').text_content(timeout=5000)
            address = await page.locator('button[data-item-id=\"address\"]').text_content(timeout=5000)
            if not business_name or not is_relevant_business(business_name, company_name, address, location):
                return None, None, None
        except Exception:
            return None, None, None

        stars = None
        print(f"🔍 DEBUG: Attempting to extract overall business rating...")
        for rating_sel in ["div[aria-label*='stars']", "span[aria-label*='stars']"]:
            elem = await page.query_selector(rating_sel)
            if elem:
                aria_label = await elem.get_attribute('aria-label')
                print(f"🔍 DEBUG: Found rating element with aria-label: {aria_label}")
                if aria_label:
                    try:
                        stars = float(aria_label.split()[0])
                        print(f"✅ DEBUG: Successfully extracted rating: {stars}")
                        break
                    except Exception as e:
                        print(f"❌ DEBUG: Error parsing rating '{aria_label}': {e}")
                        pass
            else:
                print(f"🔍 DEBUG: No element found for selector: {rating_sel}")
        
        if stars is None:
            print(f"⚠️ DEBUG: Could not extract overall business rating, will try to calculate from individual reviews")

        reviews = []
        reviews_button_selectors = ["button[aria-label*='Reviews for']", "button:has-text('Reviews')"]
        for sel in reviews_button_selectors:
            reviews_button = page.locator(sel)
            if await reviews_button.count() > 0:
                await reviews_button.first.click()
                await page.wait_for_timeout(3000)
                break

        review_elements = await page.locator("div.jftiEf").all()
        for el in review_elements[:10]:
            try:
                # Click the "More" button if it exists to expand the review
                more_button = el.locator("button:has-text('More')")
                if await more_button.count() > 0:
                    try:
                        await more_button.click()
                        await page.wait_for_timeout(1200)
                    except Exception:
                        pass 

                rating_element = el.locator("span.kvMYJc")
                individual_rating = None
                if await rating_element.count() > 0:
                    aria_label = await rating_element.get_attribute('aria-label')
                    if aria_label: 
                        try:
                            individual_rating = float(aria_label.split()[0])
                            print(f"🔍 DEBUG: Individual review rating: {individual_rating}")
                        except Exception as e:
                            print(f"❌ DEBUG: Error parsing individual rating '{aria_label}': {e}")
                else:
                    print(f"🔍 DEBUG: No rating element found for this review")
                
                text = await el.locator("span.wiI7pd").text_content(timeout=1000)
                reviews.append({"rating": individual_rating, "text": text})
                print(f"🔍 DEBUG: Added review - rating: {individual_rating}, text length: {len(text) if text else 0}")
            except Exception: continue

        # If we couldn't get the overall rating but have individual reviews, calculate average
        if stars is None and reviews:
            try:
                valid_ratings = [r.get("rating") for r in reviews if r.get("rating") is not None]
                if valid_ratings:
                    stars = round(sum(valid_ratings) / len(valid_ratings), 1)
                    print(f"✅ DEBUG: Calculated average rating from {len(valid_ratings)} reviews: {stars}")
                else:
                    print(f"⚠️ DEBUG: No valid ratings found in individual reviews")
            except Exception as e:
                print(f"❌ DEBUG: Error calculating average rating: {e}")
        
        if stars is None and not reviews: return None, None, None
        print(f"🔍 DEBUG: Final result - stars: {stars}, reviews count: {len(reviews) if reviews else 0}")
        return stars, page.url, reviews

    except Exception as e:
        print(f"   [SCRAPER ERROR] An error occurred in Playwright: {e}")
        return None, None, None
    finally:
        await page.close()
        
# --- STEP 2: Local Business Data API ---
def get_local_business_data(api_key, company_name, location):
    if not location: return None, None, None
    
    # DEBUG: Log API key usage
    print(f"🔍 DEBUG: get_local_business_data called with API key: {'YES' if api_key else 'NO'}")
    if api_key:
        print(f"🔍 DEBUG: API key value: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else 'SHORT'}")
    else:
        print("🔍 DEBUG: API key is None or empty")
    
    api_host = "local-business-data.p.rapidapi.com"
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": api_host}
    try:
        search_url = f"https://{api_host}/search"
        search_params = {"query": f"{company_name} in {location}", "limit": 5}
        response = requests.get(search_url, headers=headers, params=search_params, timeout=20)
        if response.status_code != 200: return None, None, None
        data = response.json()
        business_id, google_maps_url, rating_from_search = None, None, None
        if data.get("status") == "OK" and data.get("data"):
            for business in data["data"]:
                if is_similar_name(company_name, business.get("name")):
                    business_id, google_maps_url, rating_from_search = business.get("business_id"), business.get("google_maps_url"), business.get("rating")
                    if not google_maps_url: google_maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(f'{company_name} {location}')}"
                    break
        if not business_id: return None, None, None
    except requests.exceptions.RequestException: return None, None, None
    time.sleep(1)
    try:
        reviews_url = f"https://{api_host}/business-reviews"
        review_params = {"business_id": business_id, "limit": 10}
        response = requests.get(reviews_url, headers=headers, params=review_params, timeout=20)
        if response.status_code != 200: return rating_from_search, google_maps_url, []
        review_data = response.json()
        if review_data.get("status") == "OK" and review_data.get("data"):
            reviews_list = review_data["data"]
            overall_rating = reviews_list[0].get("rating") if reviews_list else rating_from_search
            extracted_reviews = [{"text": r.get("review_text"), "rating": r.get("rating")} for r in reviews_list]
            return overall_rating, google_maps_url, extracted_reviews
    except requests.exceptions.RequestException: return rating_from_search, google_maps_url, []
    return rating_from_search, google_maps_url, []

# --- STEP 3: Yelp API ---
def get_yelp_data(api_key, company_name, location):
    if not location: return None, None, None
    
    # DEBUG: Log API key usage
    print(f"🔍 DEBUG: get_yelp_data called with API key: {'YES' if api_key else 'NO'}")
    if api_key:
        print(f"🔍 DEBUG: API key value: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else 'SHORT'}")
    else:
        print("🔍 DEBUG: API key is None or empty")
    
    api_host = "yelp-business-api.p.rapidapi.com"
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": api_host}
    try:
        search_url = f"https://{api_host}/search"
        search_params = {"search_term": company_name, "location": location, "limit": 5}
        response = requests.get(search_url, headers=headers, params=search_params, timeout=15)
        if response.status_code != 200: return None, None, None
        data = response.json()
        business_id, rating_from_search = None, None
        if data and data.get("business_search_result"):
            for business in data["business_search_result"]:
                if is_similar_name(company_name, business.get("name")):
                    business_id, rating_from_search = business.get("id"), business.get("rating")
                    break
        if not business_id: return None, None, None
    except requests.exceptions.RequestException: return None, None, None
    yelp_url = f"https://www.yelp.com/biz/{business_id}"
    time.sleep(1)
    try:
        reviews_url = f"https://{api_host}/reviews"
        review_params = {"business_id": business_id, "reviews_per_page": 10}
        response = requests.get(reviews_url, headers=headers, params=review_params, timeout=15)
        if response.status_code != 200: return rating_from_search, yelp_url, []
        review_data = response.json()
        overall_rating = review_data.get("rating")
        reviews_list = review_data.get("reviews", [])
        extracted_reviews = [{"text": r.get("text", {}).get("full"), "rating": r.get("rating")} for r in reviews_list]
        return overall_rating, yelp_url, extracted_reviews
    except requests.exceptions.RequestException: return rating_from_search, yelp_url, []
    return rating_from_search, yelp_url, []

# --- STEP 4: Website Sentiment Analysis ---
def get_website_sentiment_data(website):
    if not website: return None, None, None
    try:
        resp = requests.get(website, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        review_keywords = ["testimonial", "review", "what our clients say", "customer feedback", "client stories"]
        all_texts = []
        def extract_good_text(soup_obj):
            review_blocks = soup_obj.find_all(["blockquote", "div", "p"], class_=lambda c: c and ("review" in c or "testimonial" in c))
            if not review_blocks: review_blocks = soup_obj.find_all(["p", "li"])
            texts = [t.get_text(separator=" ", strip=True) for t in review_blocks]
            return [t for t in texts if 10 < len(t.split()) < 200]
        for keyword in review_keywords:
            section = soup.find(lambda tag: tag.name in ["section", "div"] and tag.get_text() and keyword in tag.get_text().lower())
            if section: all_texts.extend(extract_good_text(section))
        if not all_texts or len(" ".join(all_texts).split()) < 30: return None, None, None
        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(" ".join(all_texts))
        stars = round((scores["compound"] + 1) * 2.5, 1)
        extracted_reviews = [{"text": text} for text in all_texts[:10]]
        return stars, website, extracted_reviews
    except Exception: return None, None, None

# --- DeepSeek Summarization Function ---
def summarize_reviews_with_deepseek(api_key, reviews, is_website_source=False):
    review_texts = [review.get("text") for review in reviews if review.get("text")]
    if not review_texts: return None
    full_review_text = "\n\n".join(review_texts)
    
    if is_website_source:
        prompt = f"Mention this in starting 'This is an AI-estimated summary based on the company's website.' The following text is from the company's testimonials. Even if the text appears to be marketing material, extract the key points and themes mentioned. Create a neutral summary of what the company claims its strengths are based on this text. The summary should be around 100 words. Do not use introductory phrases like 'Based on the testimonials...'. Begin directly with the main feedback.\n\n{full_review_text}"
    else:
        prompt = f"Directly summarize the core sentiment, positive points, and negative points from the following customer feedback. The summary should be around 100 words. Do not use introductory phrases like 'Based on the reviews...' or 'Customers say...'. Begin directly with the main feedback.\n\n{full_review_text}"

    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that summarizes customer feedback."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200: return None
        
        raw_summary = response.json()['choices'][0]['message']['content']
        clean_summary = raw_summary.replace('\n', ' ').strip()
        return clean_summary

    except requests.exceptions.RequestException: return None

# =============================================================================
# SECTION 3: MAIN EXECUTION LOGIC
# =============================================================================

async def process_company_data(company, location, website):
    
    # IMPORTANT: Load API keys from environment variables for security
    rapid_api_key = os.getenv("RAPIDAPI_KEY")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    
    # DEBUG: Print API key loading information
    print(f"🔍 DEBUG: Current working directory: {os.getcwd()}")
    print(f"🔍 DEBUG: RAPIDAPI_KEY loaded: {'YES' if rapid_api_key else 'NO'}")
    if rapid_api_key:
        print(f"🔍 DEBUG: RAPIDAPI_KEY value: {rapid_api_key[:10]}...{rapid_api_key[-4:] if len(rapid_api_key) > 14 else 'SHORT'}")
    else:
        print("🔍 DEBUG: RAPIDAPI_KEY is None or empty")
    print(f"🔍 DEBUG: DEEPSEEK_API_KEY loaded: {'YES' if deepseek_api_key else 'NO'}")
    print(f"🔍 DEBUG: Environment variables: {[k for k in os.environ.keys() if 'API' in k.upper()]}")

    final_report = {
        "request_info": {
            "company_name": company,
            "location": location,
            "website": website
        },
        "rating_info": {
            "overall_rating": None,
            "source": None
        },
        "summary": {
            "text": None,
            "review_count": 0
        },
        "reviews": {
            "source": None,
            "list": []
        },
        "notes": None
    }

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            best_stars, rating_source_name, rating_source_url = None, None, None
            found_reviews, reviews_source_name, reviews_source_url = None, None, None

            has_text_reviews = lambda revs: revs and any(r.get("text") for r in revs)

            # Step 1: Google Maps Scraper with a 35-second timeout
            print(f"🔍 DEBUG: Step 1 - Starting Google Maps Scraper for company: {company}")
            try:
                stars, source, reviews = await asyncio.wait_for(
                    get_google_maps_review(browser, company, location), timeout=35.0
                )
                print(f"🔍 DEBUG: Google Maps result - stars: {stars}, source: {source}, reviews count: {len(reviews) if reviews else 0}")
                if reviews:
                    print(f"🔍 DEBUG: Google Maps reviews sample: {reviews[:2] if len(reviews) > 2 else reviews}")
                if has_text_reviews(reviews):
                    found_reviews, reviews_source_url, reviews_source_name = reviews, source, "Google Maps Scraper"
                    print(f"✅ DEBUG: Google Maps succeeded with {len(reviews)} reviews")
                else:
                    print(f"❌ DEBUG: Google Maps failed - no text reviews found")
                if stars is not None and best_stars is None:
                    best_stars, rating_source_url, rating_source_name = stars, source, "Google Maps Scraper"
                    print(f"✅ DEBUG: Google Maps provided rating: {stars}")
            except asyncio.TimeoutError:
                print(f"⏰ DEBUG: Google Maps scraper timed out after 35 seconds")
                pass
            
            # Step 2
            if not has_text_reviews(found_reviews):
                print(f"🔍 DEBUG: Step 2 - Calling Local Business API with rapid_api_key: {'YES' if rapid_api_key else 'NO'}")
                stars, source, reviews = get_local_business_data(rapid_api_key, company, location)
                print(f"🔍 DEBUG: Local Business API result - stars: {stars}, source: {source}, reviews count: {len(reviews) if reviews else 0}")
                if reviews:
                    print(f"🔍 DEBUG: Local Business API reviews sample: {reviews[:2] if len(reviews) > 2 else reviews}")
                if has_text_reviews(reviews):
                    found_reviews, reviews_source_url, reviews_source_name = reviews, source, "Local Business API"
                    print(f"✅ DEBUG: Local Business API succeeded with {len(reviews)} reviews")
                else:
                    print(f"❌ DEBUG: Local Business API failed - no text reviews found")
                if stars is not None and best_stars is None:
                    best_stars, rating_source_url, rating_source_name = stars, source, "Local Business API"
                    print(f"✅ DEBUG: Local Business API provided rating: {stars}")

            # Step 3
            if not has_text_reviews(found_reviews):
                print(f"🔍 DEBUG: Step 3 - Calling Yelp API with rapid_api_key: {'YES' if rapid_api_key else 'NO'}")
                stars, source, reviews = get_yelp_data(rapid_api_key, company, location)
                print(f"🔍 DEBUG: Yelp API result - stars: {stars}, source: {source}, reviews count: {len(reviews) if reviews else 0}")
                if reviews:
                    print(f"🔍 DEBUG: Yelp API reviews sample: {reviews[:2] if len(reviews) > 2 else reviews}")
                if has_text_reviews(reviews):
                    found_reviews, reviews_source_url, reviews_source_name = reviews, source, "Yelp API"
                    print(f"✅ DEBUG: Yelp API succeeded with {len(reviews)} reviews")
                else:
                    print(f"❌ DEBUG: Yelp API failed - no text reviews found")
                if stars is not None and best_stars is None:
                    best_stars, rating_source_url, rating_source_name = stars, source, "Yelp API"
                    print(f"✅ DEBUG: Yelp API provided rating: {stars}")

            # Step 4
            if not has_text_reviews(found_reviews):
                print(f"🔍 DEBUG: Step 4 - Starting Website Analysis for website: {website}")
                stars, source, reviews = get_website_sentiment_data(website)
                print(f"🔍 DEBUG: Website Analysis result - stars: {stars}, source: {source}, reviews count: {len(reviews) if reviews else 0}")
                if reviews:
                    print(f"🔍 DEBUG: Website Analysis reviews sample: {reviews[:2] if len(reviews) > 2 else reviews}")
                if has_text_reviews(reviews):
                    found_reviews, reviews_source_url, reviews_source_name = reviews, source, "Website Analysis"
                    print(f"✅ DEBUG: Website Analysis succeeded with {len(reviews)} reviews")
                else:
                    print(f"❌ DEBUG: Website Analysis failed - no text reviews found")
                if stars is not None and best_stars is None:
                    best_stars, rating_source_url, rating_source_name = stars, source, "AI-estimated from Website"
                    print(f"✅ DEBUG: Website Analysis provided rating: {stars}")

            # --- Final Report Generation ---
            print(f"🔍 DEBUG: Final Report Generation - best_stars: {best_stars}, rating_source: {rating_source_name}")
            print(f"🔍 DEBUG: Final Report Generation - found_reviews: {len(found_reviews) if found_reviews else 0}, reviews_source: {reviews_source_name}")
            
            if best_stars is not None:
                final_report["rating_info"]["overall_rating"] = best_stars
                final_report["rating_info"]["source"] = rating_source_name
                print(f"✅ DEBUG: Final Report - Rating {best_stars} from {rating_source_name}")

                reviews_with_text = [r for r in found_reviews if r.get("text")] if found_reviews else []
                print(f"🔍 DEBUG: Final Report - Reviews with text: {len(reviews_with_text)}")

                if reviews_with_text:
                    print(f"🔍 DEBUG: Final Report - Generating summary with DeepSeek API")
                    is_website = (reviews_source_name == "Website Analysis")
                    summary_text = summarize_reviews_with_deepseek(deepseek_api_key, reviews_with_text, is_website_source=is_website)
                    
                    final_report["summary"]["text"] = summary_text
                    final_report["summary"]["review_count"] = len(reviews_with_text)
                    final_report["reviews"]["source"] = reviews_source_name
                    final_report["reviews"]["list"] = found_reviews
                    print(f"✅ DEBUG: Final Report - Summary generated successfully")
                else:
                    if not final_report["notes"]:
                        final_report["notes"] = "Rating found, but no text reviews were available for a summary."
                    print(f"⚠️ DEBUG: Final Report - Rating found but no text reviews available")
            else:
                if not final_report["notes"]:
                    final_report["notes"] = f"Could not determine a rating and review for {company} from any source."
                print(f"❌ DEBUG: Final Report - No rating or reviews found from any source")
            
            print(f"🔍 DEBUG: Final Report - Notes: {final_report['notes']}")
            print(f"🔍 DEBUG: Final Report - Summary: {final_report['summary']['text'][:100] if final_report['summary']['text'] else 'None'}...")
            print(f"🔍 DEBUG: Final Report - Reviews count: {len(final_report['reviews']['list'])}")

            await browser.close()
        
        return final_report

    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}
