# service/llm_service.py
from llm_news.llm_news_scraper import get_news_with_summary
from llm_news.company_profile import build_full_profile

def process_news_request(data):
    # Example: expects {"company": "...", "time_option": "this_week", "max_items": 10}
    company = data.get('company')
    time_option = data.get('time_option', 'this_week')
    max_items = data.get('max_items', 10)
    return get_news_with_summary(company, time_option, max_items)

def get_company_profile(company):
    # Optionally, you could pass a website or other params
    # For now, just use the company name and a placeholder website
    website = f"https://{company.replace(' ', '').lower()}.com"
    return build_full_profile(company, website) 