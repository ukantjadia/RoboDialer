from typing import List
import re
import asyncio

from ..models.scoring_model import Analysis, ScoreComponent, ScoringResult
from .enhanced_scraping_service import EnhancedScrapingService
import logging
from .llm_utils import batch_llm_analyze_companies

logger = logging.getLogger("ml_service")

class MLService:
    def __init__(self):
        pass

    @staticmethod
    def parse_revenue(value):
        import re
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).replace('$', '').replace(',', '').strip().lower()
        if '<' in s and 'm' in s:
            try:
                match = re.search(r'([0-9]+(\.[0-9]+)?)', s)
                if match:
                    upper_bound = float(match.group(1)) * 1_000_000
                    return upper_bound * 0.6
            except:
                pass
        if '<' in s and 'b' in s:
            try:
                match = re.search(r'([0-9]+(\.[0-9]+)?)', s)
                if match:
                    upper_bound = float(match.group(1)) * 1_000_000_000
                    return upper_bound * 0.6
            except:
                pass
        if '>' in s and 'm' in s:
            try:
                match = re.search(r'([0-9]+(\.[0-9]+)?)', s)
                if match:
                    lower_bound = float(match.group(1)) * 1_000_000
                    return lower_bound * 1.5
            except:
                pass
        if 'million' in s:
            try:
                return float(s.replace('million', '').strip()) * 1_000_000
            except:
                return None
        if 'billion' in s:
            try:
                return float(s.replace('billion', '').strip()) * 1_000_000_000
            except:
                return None
        if 'thousand' in s:
            try:
                return float(s.replace('thousand', '').strip()) * 1_000
            except:
                return None
        if s.endswith('m'):
            try:
                return float(s[:-1]) * 1_000_000
            except:
                return None
        if s.endswith('b'):
            try:
                return float(s[:-1]) * 1_000_000_000
            except:
                return None
        if s.endswith('k'):
            try:
                return float(s[:-1]) * 1_000
            except:
                return None
        match = re.search(r'([0-9]+(\.[0-9]+)?)', s)
        if match:
            try:
                return float(match.group(1))
            except:
                return None
        try:
            return float(s)
        except:
            return None

    @staticmethod
    def parse_employees(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        s = str(value).replace(',', '').strip().lower()
        import re
        range_match = re.search(r'([0-9]+)\s*[-–—to]\s*([0-9]+)', s)
        if range_match:
            try:
                min_emp = int(range_match.group(1))
                max_emp = int(range_match.group(2))
                return int((min_emp + max_emp) / 2)
            except:
                pass
        plus_match = re.search(r'([0-9]+)\s*\+', s)
        if plus_match:
            try:
                base_emp = int(plus_match.group(1))
                return int(base_emp * 1.25)
            except:
                pass
        less_match = re.search(r'<\s*([0-9]+)', s)
        if less_match:
            try:
                upper = int(less_match.group(1))
                return int(upper * 0.6)
            except:
                pass
        more_match = re.search(r'>\s*([0-9]+)', s)
        if more_match:
            try:
                lower = int(more_match.group(1))
                return int(lower * 1.5)
            except:
                pass
        word_map = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
            'hundred': 100, 'thousand': 1000
        }
        for word, num in word_map.items():
            if word in s:
                return num
        match = re.search(r'([0-9]+)', s)
        if match:
            try:
                return int(match.group(1))
            except:
                return None
        return None

    def is_valid_email(self, email):
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email or ""))

    async def recommend_leads(self, leads, preferences, top_n=10):
        
        # Mock database
        class MockDB:
            def __getitem__(self, key):
                return self
            def find(self, query=None):
                return []
            def update_one(self, filter_query, update_query):
                return {"modified_count": 1}
            def insert_one(self, document):
                return {"inserted_id": "mock_id"}
        
        db = MockDB()
        
        def is_valid_lead(lead):
            email = lead.get('Email') or lead.get('email')
            website = lead.get('Website') or lead.get('website')
            linkedin = lead.get('LinkedIn URL') or lead.get('linkedin')
            return (
                (email and '@' in str(email)) or
                (website and str(website).startswith('http')) or
                (linkedin and 'linkedin.com' in str(linkedin))
            )

        # ENFORCE: All three values for revenue and employees must be provided
        missing_fields = []
        for field in ['min_revenue', 'max_revenue', 'target_revenue']:
            if preferences.get(field) is None:
                missing_fields.append(field)
        for field in ['min_employees', 'max_employees', 'target_employees']:
            if preferences.get(field) is None:
                missing_fields.append(field)
        if missing_fields:
            logger.error(f"[SCORING] Missing required fields: {', '.join(missing_fields)}. User must provide min, max, and target for both revenue and employees.")
            return []

        # --- HARD FILTERS FIRST ---
        filtered_leads = []
        
        for lead in leads:
            # Industry hard filter - check multiple possible field names
            user_industry = (
                preferences.get('industry') or preferences.get('target_industry') or ''
            ).strip().lower()
            lead_industry = (
                lead.get('industry') or 
                lead.get('Industry') or 
                lead.get('Industry ') or  # Note the trailing space
                ''
            ).strip().lower()
            
            if user_industry and lead_industry != user_industry:
                print(f"[ml_service] Filtered out lead '{lead.get('name', lead.get('Company Name', 'Unknown'))}' - Industry mismatch: '{lead_industry}' != '{user_industry}'")
                continue  # Skip this lead - industry doesn't match
            
            # Location hard filter - check multiple possible field names
            user_location = (
                preferences.get('location') or preferences.get('target_location') or ''
            ).strip().lower()
            lead_location = (
                lead.get('location') or 
                lead.get('Location') or 
                lead.get('State') or  # Check State field
                ''
            ).strip().lower()
            
            if user_location and lead_location != user_location:
                print(f"[ml_service] Filtered out lead '{lead.get('name', lead.get('Company Name', 'Unknown'))}' - Location mismatch: '{lead_location}' != '{user_location}'")
                continue  # Skip this lead - location doesn't match
            
            # Revenue hard filter
            min_rev = preferences.get('min_revenue')
            max_rev = preferences.get('max_revenue')
            lead_rev = lead.get('revenue') or lead.get('Revenue')
            lead_rev_parsed = self.parse_revenue(lead_rev)
            if min_rev is not None and max_rev is not None and lead_rev_parsed is not None:
                try:
                    min_rev_f = float(min_rev)
                    max_rev_f = float(max_rev)
                    if lead_rev_parsed < min_rev_f or lead_rev_parsed > max_rev_f:
                        print(f"[ml_service] Filtered out lead '{lead.get('name', lead.get('Company Name', 'Unknown'))}' - Revenue {lead_rev_parsed} not in range [{min_rev_f}, {max_rev_f}]")
                        continue
                except Exception:
                    pass
            # Employees hard filter
            min_emp = preferences.get('min_employees')
            max_emp = preferences.get('max_employees')
            lead_emp = lead.get('employees') or lead.get('Employees')
            lead_emp_parsed = self.parse_employees(lead_emp)
            if min_emp is not None and max_emp is not None and lead_emp_parsed is not None:
                try:
                    min_emp_f = float(min_emp)
                    max_emp_f = float(max_emp)
                    if lead_emp_parsed < min_emp_f or lead_emp_parsed > max_emp_f:
                        print(f"[ml_service] Filtered out lead '{lead.get('name', lead.get('Company Name', 'Unknown'))}' - Employees {lead_emp_parsed} not in range [{min_emp_f}, {max_emp_f}]")
                        continue
                except Exception:
                    pass
            # If we get here, the lead passed all hard filters
            print(f"[ml_service] Lead '{lead.get('name', lead.get('Company Name', 'Unknown'))}' passed hard filters - Industry: '{lead_industry}', Location: '{lead_location}'")
            filtered_leads.append(lead)
        
        print(f"[ml_service] Hard filters applied: {len(leads)} total leads -> {len(filtered_leads)} matching leads")
        
        # If no leads pass the hard filters, return empty list
        if not filtered_leads:
            print(f"[ml_service] No leads match the hard filters for industry='{preferences.get('industry') or preferences.get('target_industry')}' and location='{preferences.get('location') or preferences.get('target_location')}'")
            return []

        # --- DYNAMIC SCORING WEIGHTS BASED ON INDUSTRY ---
        def get_industry_weights(industry):
            """Get industry-specific scoring weights based on PE investment patterns"""
            industry_lower = industry.lower()
            
            # Education/EdTech weights (current focus)
            if any(term in industry_lower for term in ['education', 'edtech', 'learning', 'training']):
                return {
                    'revenue': 30,      # Revenue stability important
                    'employees': 25,    # Team size matters for scalability
                    'keywords': 25,     # Market fit crucial for education
                    'valid_contact': 10, # Contact quality
                    'growth_potential': 10  # Growth indicators
                }
            
            # Technology/SaaS weights
            elif any(term in industry_lower for term in ['technology', 'software', 'saas', 'ai', 'tech']):
                return {
                    'revenue': 30,      # High revenue focus
                    'employees': 20,    # Smaller teams can be more agile
                    'keywords': 20,     # Market positioning
                    'valid_contact': 10,
                    'growth_potential': 20  # High growth potential
                }
            
            # Healthcare/Biotech weights
            elif any(term in industry_lower for term in ['healthcare', 'medical', 'biotech', 'pharma']):
                return {
                    'revenue': 25,      # Regulatory compliance more important
                    'employees': 25,    # Team expertise critical
                    'keywords': 20,     # Market fit
                    'valid_contact': 10,
                    'growth_potential': 20  # High growth potential
                }
            
            # Manufacturing weights
            elif any(term in industry_lower for term in ['manufacturing', 'industrial', 'production']):
                return {
                    'revenue': 35,      # Revenue stability very important
                    'employees': 25,    # Operational scale matters
                    'keywords': 20,     # Market positioning
                    'valid_contact': 10,
                    'growth_potential': 10   # Lower growth potential
                }
            
            # Construction weights
            elif any(term in industry_lower for term in ['construction', 'building', 'contractor']):
                return {
                    'revenue': 30,      # Revenue stability important
                    'employees': 25,    # Team size matters
                    'keywords': 20,     # Market positioning
                    'valid_contact': 10,
                    'growth_potential': 15   # Moderate growth potential
                }
            
            # Default weights (balanced approach)
            else:
                return {
                    'revenue': 30,
                    'employees': 25,
                    'keywords': 20,
                    'valid_contact': 10,
                    'growth_potential': 15
                }
        
        # Get industry-specific weights
        user_industry = preferences.get('industry') or preferences.get('target_industry') or 'education'
        WEIGHTS = get_industry_weights(user_industry)
        
        # Industry-specific scoring criteria
        def get_industry_criteria(industry):
            """Get industry-specific scoring criteria"""
            industry_lower = industry.lower()
            
            if any(term in industry_lower for term in ['education', 'edtech', 'learning']):
                return {
                    'min_revenue_threshold': 500000,  # Minimum viable revenue
                    'max_revenue_threshold': 50000000,  # Maximum before too large
                    'optimal_employee_range': (10, 200),  # Optimal team size
                    'growth_indicators': ['online', 'digital', 'platform', 'software', 'app', 'mobile']
                }
            
            elif any(term in industry_lower for term in ['technology', 'software', 'saas']):
                return {
                    'min_revenue_threshold': 100000,
                    'max_revenue_threshold': 100000000,
                    'optimal_employee_range': (5, 150),
                    'growth_indicators': ['saas', 'subscription', 'recurring', 'platform', 'api', 'cloud']
                }
            
            else:
                return {
                    'min_revenue_threshold': 100000,
                    'max_revenue_threshold': 50000000,
                    'optimal_employee_range': (5, 500),
                    'growth_indicators': ['growth', 'expansion', 'scaling', 'new markets']
                }
        
        INDUSTRY_CRITERIA = get_industry_criteria(user_industry)

        # Industry-specific risk and market positioning scoring
        def calculate_industry_risk_score(lead, industry):
            """Calculate industry-specific risk score (lower is better)"""
            risk_score = 0
            industry_lower = industry.lower()
            
            # Revenue risk factors
            lead_rev = self.parse_revenue(lead.get('revenue') or lead.get('Revenue'))
            if lead_rev:
                if lead_rev < INDUSTRY_CRITERIA['min_revenue_threshold']:
                    risk_score += 20  # High risk: too small
                elif lead_rev > INDUSTRY_CRITERIA['max_revenue_threshold']:
                    risk_score += 15  # Medium risk: too large for PE investment
            
            # Employee risk factors
            lead_emp = lead.get('employees') or lead.get('Employees')
            lead_emp_parsed = self.parse_employees(lead_emp)
            
            if lead_emp_parsed:
                optimal_min, optimal_max = INDUSTRY_CRITERIA['optimal_employee_range']
                if lead_emp_parsed < optimal_min:
                    risk_score += 10  # Risk: too small team
                elif lead_emp_parsed > optimal_max * 2:
                    risk_score += 15  # Risk: too large team
            
            # Industry-specific risk factors
            if industry_lower in ['education', 'edtech', 'learning']:
                # Education-specific risks
                company_text = ""
                if lead.get('description'):
                    company_text += " " + str(lead.get('description'))
                if lead.get('name'):
                    company_text += " " + str(lead.get('name'))
                if lead.get('website_text'):
                    company_text += " " + str(lead.get('website_text'))
                if lead.get('Company Name'):
                    company_text += " " + str(lead.get('Company Name'))
                
                company_text = company_text.lower()
                
                if any(term in company_text for term in ['brick', 'mortar', 'physical', 'location']):
                    risk_score += 5  # Risk: physical location dependency
                if any(term in company_text for term in ['government', 'public', 'funding']):
                    risk_score += 10  # Risk: government dependency
                if any(term in company_text for term in ['consulting', 'services', 'agency']):
                    risk_score += 8  # Risk: service-based revenue
                if any(term in company_text for term in ['pet', 'dog', 'animal', 'veterinary']):
                    risk_score += 15  # Risk: not education-focused
            
            elif industry_lower in ['technology', 'software', 'saas']:
                # Tech-specific risks
                company_text = ""
                if lead.get('description'):
                    company_text += " " + str(lead.get('description'))
                if lead.get('name'):
                    company_text += " " + str(lead.get('name'))
                if lead.get('website_text'):
                    company_text += " " + str(lead.get('website_text'))
                if lead.get('Company Name'):
                    company_text += " " + str(lead.get('Company Name'))
                
                company_text = company_text.lower()
                
                if any(term in company_text for term in ['consulting', 'services', 'agency']):
                    risk_score += 8  # Risk: service-based revenue
                if any(term in company_text for term in ['hardware', 'equipment', 'manufacturing']):
                    risk_score += 5  # Risk: hardware dependency
            
            return min(risk_score, 100)  # Cap at 100
        
        def calculate_market_positioning_score(lead, industry):
            """Calculate market positioning score (higher is better)"""
            positioning_score = 0
            industry_lower = industry.lower()
            
            # Combine all available text for analysis
            company_text = ""
            if lead.get('description'):
                company_text += " " + str(lead.get('description'))
            if lead.get('name'):
                company_text += " " + str(lead.get('name'))
            if lead.get('website_text'):
                company_text += " " + str(lead.get('website_text'))
            if lead.get('Company Name'):
                company_text += " " + str(lead.get('Company Name'))
            
            company_text = company_text.lower()
            
            if industry_lower in ['education', 'edtech', 'learning']:
                # Education positioning factors
                if any(term in company_text for term in ['online', 'digital', 'platform']):
                    positioning_score += 15  # Strong: digital transformation
                if any(term in company_text for term in ['accredited', 'certified', 'licensed']):
                    positioning_score += 10  # Strong: regulatory compliance
                if any(term in company_text for term in ['k-12', 'higher education', 'corporate training']):
                    positioning_score += 8   # Strong: clear market segment
                if any(term in company_text for term in ['ai', 'machine learning', 'personalized']):
                    positioning_score += 12  # Strong: innovation
                if any(term in company_text for term in ['language', 'learning', 'education']):
                    positioning_score += 10  # Strong: core education focus
                if any(term in company_text for term in ['curriculum', 'course', 'program']):
                    positioning_score += 8   # Strong: structured learning
                if any(term in company_text for term in ['student', 'learner', 'teacher']):
                    positioning_score += 6   # Strong: educational audience
            
            elif industry_lower in ['technology', 'software', 'saas']:
                # Tech positioning factors
                if any(term in company_text for term in ['saas', 'subscription', 'recurring']):
                    positioning_score += 20  # Strong: recurring revenue model
                if any(term in company_text for term in ['api', 'integration', 'platform']):
                    positioning_score += 15  # Strong: platform capabilities
                if any(term in company_text for term in ['cloud', 'scalable', 'enterprise']):
                    positioning_score += 12  # Strong: enterprise focus
            
            return min(positioning_score, 100)  # Cap at 100

        async def score_lead(lead, db):
            score = 0
            # Revenue (target-in-range scoring)
            min_rev = preferences.get('min_revenue')
            max_rev = preferences.get('max_revenue')
            target_rev = preferences.get('target_revenue')
            lead_rev = lead.get('revenue') or lead.get('Revenue')
            lead_rev_parsed = self.parse_revenue(lead_rev)
            logger.info(f"[SCORING] Lead: {lead.get('name', lead.get('Company Name', 'Unknown'))} | Raw revenue: {lead_rev} | Parsed revenue: {lead_rev_parsed} | Min: {min_rev} | Max: {max_rev} | Target: {target_rev}")
            max_score = WEIGHTS['revenue']
            edge_score = 5
            rev_score = 0
            if lead_rev_parsed is not None and min_rev is not None and max_rev is not None and target_rev is not None:
                try:
                    min_rev = float(min_rev)
                    max_rev = float(max_rev)
                    target_rev = float(target_rev)
                    if lead_rev_parsed < min_rev or lead_rev_parsed > max_rev:
                        rev_score = 0
                    else:
                        range_span = max(abs(target_rev - min_rev), abs(max_rev - target_rev))
                        dist = abs(lead_rev_parsed - target_rev)
                        if range_span == 0:
                            rev_score = max_score
                        else:
                            rev_score = edge_score + (max_score - edge_score) * (1 - (dist / range_span))
                        rev_score = max(edge_score, rev_score)
                        if lead_rev_parsed == target_rev:
                            rev_score = max_score
                        elif lead_rev_parsed == min_rev or lead_rev_parsed == max_rev:
                            rev_score = edge_score
                        rev_score = int(round(rev_score))
                except Exception as e:
                    logger.error(f"[SCORING] Revenue scoring error: {e}")
            score += rev_score
            
            # Revenue scoring (no bonuses)
            if lead_rev_parsed is not None:
                # No bonuses - just the base revenue score
                pass
            
            # Employees (target-in-range scoring)
            min_emp = preferences.get('min_employees')
            max_emp = preferences.get('max_employees')
            target_emp = preferences.get('target_employees')
            lead_emp = lead.get('employees') or lead.get('Employees')
            lead_emp_parsed = self.parse_employees(lead_emp)
            emp_score = 0
            if lead_emp_parsed is not None and min_emp is not None and max_emp is not None and target_emp is not None:
                try:
                    min_emp = float(min_emp)
                    max_emp = float(max_emp)
                    target_emp = float(target_emp)
                    if lead_emp_parsed < min_emp or lead_emp_parsed > max_emp:
                        emp_score = 0
                    else:
                        range_span = max(abs(target_emp - min_emp), abs(max_emp - target_emp))
                        dist = abs(lead_emp_parsed - target_emp)
                        if range_span == 0:
                            emp_score = WEIGHTS['employees']
                        else:
                            emp_score = edge_score + (WEIGHTS['employees'] - edge_score) * (1 - (dist / range_span))
                        emp_score = max(edge_score, emp_score)
                        if lead_emp_parsed == target_emp:
                            emp_score = WEIGHTS['employees']
                        elif lead_emp_parsed == min_emp or lead_emp_parsed == max_emp:
                            emp_score = edge_score
                        emp_score = int(round(emp_score))
                except Exception as e:
                    logger.error(f"[SCORING] Employee scoring error: {e}")
            score += emp_score
            
            # Employee scoring (no bonuses)
            # No bonuses - just the base employee score
            
            # Growth Potential Scoring (NEW)
            growth_score = 0
            if 'growth_potential' in WEIGHTS:
                # Analyze company description and website text for growth indicators
                company_text = ""
                if lead.get('description'):
                    company_text += " " + str(lead.get('description'))
                if lead.get('website_text'):
                    company_text += " " + str(lead.get('website_text'))
                if lead.get('name'):
                    company_text += " " + str(lead.get('name'))
                
                company_text = company_text.lower()
                
                # Check for growth indicators
                growth_indicators = INDUSTRY_CRITERIA.get('growth_indicators', [])
                growth_matches = sum(1 for indicator in growth_indicators if indicator in company_text)
                
                # Score based on growth indicators found
                if growth_matches >= 3:
                    growth_score = WEIGHTS['growth_potential']
                elif growth_matches >= 2:
                    growth_score = int(WEIGHTS['growth_potential'] * 0.7)
                elif growth_matches >= 1:
                    growth_score = int(WEIGHTS['growth_potential'] * 0.4)
                
                # No growth bonuses - just the base growth score
                
                score += growth_score
            # Enhanced Keyword Scoring with Fresh Website Scraping (No Caching)
            user_keywords = preferences.get('keywords')
            user_negative_keywords = preferences.get('negative_keywords')
            keyword_score = 0
            website_url = lead.get('website') or lead.get('Website')
            company_name = lead.get('name') or lead.get('Name') or lead.get('Company Name') or ''
            city = lead.get('city') or lead.get('City') or None
            state = lead.get('state') or lead.get('State') or None
            
            # Always scrape fresh content (no caching)
            enhanced_scraper = EnhancedScrapingService(None)
            keywords_list = [k.strip() for k in user_keywords.split(',')] if isinstance(user_keywords, str) else [str(k).strip() for k in user_keywords] if user_keywords else []
            scraped_data = await enhanced_scraper.scrape_company(company_name, website_url, keywords_list, city, state)
            website_text = scraped_data.get('text_snippet', '')
            webtext_source = 'freshly scraped'
            # Keyword scoring will be handled in batch after scraping
            
            # Valid Contact
            valid_contact = is_valid_lead(lead)
            if valid_contact:
                score += WEIGHTS['valid_contact']
            
            # Generate comprehensive score explanation
            explanation_parts = []
            
            # Revenue explanation
            if lead_rev_parsed is not None:
                if rev_score > 0:
                    explanation_parts.append(f"Revenue: ${lead_rev_parsed:,.0f} (Score: {rev_score}/{WEIGHTS['revenue']})")
                    if lead_rev_parsed >= INDUSTRY_CRITERIA['min_revenue_threshold']:
                        explanation_parts.append(f"✓ Above {user_industry} minimum threshold")
                    if (INDUSTRY_CRITERIA['min_revenue_threshold'] <= lead_rev_parsed <= INDUSTRY_CRITERIA['max_revenue_threshold']):
                        explanation_parts.append(f"✓ Optimal revenue range for {user_industry}")
                else:
                    explanation_parts.append(f"Revenue: ${lead_rev_parsed:,.0f} (Outside target range)")
            else:
                explanation_parts.append("Revenue: Not available")
            
            # Employee explanation
            if lead_emp_parsed is not None:
                if emp_score > 0:
                    explanation_parts.append(f"Employees: {lead_emp_parsed} (Score: {emp_score}/{WEIGHTS['employees']})")
                    optimal_min, optimal_max = INDUSTRY_CRITERIA['optimal_employee_range']
                    if optimal_min <= lead_emp_parsed <= optimal_max:
                        explanation_parts.append(f"✓ Optimal team size for {user_industry}")
                else:
                    explanation_parts.append(f"Employees: {lead_emp_parsed} (Outside target range)")
            else:
                explanation_parts.append("Employees: Not available")
            
            # Growth potential explanation
            if 'growth_potential' in WEIGHTS and growth_score > 0:
                explanation_parts.append(f"Growth Potential: {growth_score}/{WEIGHTS['growth_potential']}")
                if growth_matches >= 2:
                    explanation_parts.append(f"✓ Strong {user_industry} growth indicators")
            
            # Contact quality explanation
            if valid_contact:
                explanation_parts.append(f"Contact Quality: {WEIGHTS['valid_contact']}/{WEIGHTS['valid_contact']}")
            else:
                explanation_parts.append("Contact Quality: Missing valid contact")
            
            # Industry-specific insights
            if user_industry.lower() in ['education', 'edtech', 'learning']:
                if any(term in company_text for term in ['online', 'digital', 'platform']):
                    explanation_parts.append("✓ Technology-enabled education")
                if any(term in company_text for term in ['accredited', 'certified', 'licensed']):
                    explanation_parts.append("✓ Accredited/certified programs")
            
            explanation = " | ".join(explanation_parts)
            
            # Calculate additional industry-specific scores
            risk_score = calculate_industry_risk_score(lead, user_industry)
            positioning_score = calculate_market_positioning_score(lead, user_industry)
            
            # Add risk and positioning to explanation
            explanation += f" | Risk: {risk_score}/100 | Positioning: {positioning_score}/100"
            
            # Store additional scores in lead data
            # Removed internal scoring data - no longer needed in response
            # lead['risk_score'] = risk_score
            # lead['positioning_score'] = positioning_score
            # lead['industry_weights'] = WEIGHTS
            # lead['industry_criteria'] = INDUSTRY_CRITERIA
            
            logger.info(f"[SCORING] Valid contact: {valid_contact} | Final score: {score} | Risk: {risk_score} | Positioning: {positioning_score} | Explanation: {explanation}")
            return {"lead": lead, "score": score, "explanation": explanation}



        # Score all leads in parallel with concurrency limit
        import asyncio
        semaphore = asyncio.Semaphore(2)
        async def sem_score_lead(lead, db):
            async with semaphore:
                return await score_lead(lead, db)
        scored_leads_raw = await asyncio.gather(*[sem_score_lead(lead, db) for lead in filtered_leads])
        # Defensive check: filter out any non-dict results and log them
        scored_leads = []
        for res in scored_leads_raw:
            if isinstance(res, dict):
                scored_leads.append(res)
            else:
                logger.error(f"[SCORING ERROR] score_lead returned non-dict: {res} (type: {type(res)})")
        # Sort by score descending
        scored_leads.sort(key=lambda x: x['score'], reverse=True)

        # Enhanced Keyword, Risk, and Growth Analysis with Smart Hybrid Approach
        user_keywords = preferences.get('keywords')
        user_negative_keywords = preferences.get('negative_keywords')
        keywords_list = [k.strip() for k in user_keywords.split(',')] if isinstance(user_keywords, str) else [str(k).strip() for k in user_keywords] if user_keywords else []
        negative_keywords_list = [k.strip() for k in user_negative_keywords.split(',')] if isinstance(user_negative_keywords, str) else [str(k).strip() for k in user_negative_keywords] if user_negative_keywords else []
        
        # Debug logging
        logger.info(f"[DEBUG] Preferences received: {preferences}")
        logger.info(f"[DEBUG] user_keywords: '{user_keywords}' (type: {type(user_keywords)})")
        logger.info(f"[DEBUG] user_negative_keywords: '{user_negative_keywords}' (type: {type(user_negative_keywords)})")
        logger.info(f"[DEBUG] keywords_list: {keywords_list}")
        logger.info(f"[DEBUG] negative_keywords_list: {negative_keywords_list}")
        
        # Get industry from either target_industry or industry field
        user_industry = preferences.get('target_industry') or preferences.get('industry') or 'general'
        
        # Smart Hybrid Analysis: Check for existing stable AI analysis
        leads_for_llm = []
        
        # Check if user wants to force refresh (for testing/debugging)
        force_refresh = preferences.get('force_refresh', False)
        if force_refresh:
            logger.info("[HYBRID ANALYSIS] Force refresh requested - running fresh analysis for all leads")
            leads_for_llm = scored_leads
            leads_with_existing_analysis = []
        else:
            # No caching - always run fresh AI analysis for all leads
            for res in scored_leads:
                lead = res['lead']
                leads_for_llm.append(res)
                logger.info(f"[FRESH ANALYSIS] Running fresh AI analysis for {lead.get('Company Name', 'Unknown')} - no caching enabled")
        
        logger.info(f"[FRESH ANALYSIS] {len(leads_for_llm)} leads will get fresh AI analysis (no caching)")
        
        # Run LLM analysis only for leads that need fresh analysis
        if leads_for_llm:
            logger.info(f"[ENHANCED ANALYSIS] Running batch_llm_analyze_companies for {len(leads_for_llm)} leads...")
            try:
                # Extract the actual lead data from the res objects
                actual_leads_for_llm = [res['lead'] for res in leads_for_llm]
                logger.info(f"[ENHANCED ANALYSIS] Extracted {len(actual_leads_for_llm)} actual leads for LLM analysis")
                
                # Debug: Check what data we're sending to LLM
                for i, lead in enumerate(actual_leads_for_llm):
                    company_name = lead.get('Company Name', 'Unknown')
                    website_text_length = len(lead.get('website_text', ''))
                    logger.info(f"[LLM DEBUG] Lead {i+1}: {company_name} | Website text length: {website_text_length}")
                    if website_text_length > 0:
                        logger.info(f"[LLM DEBUG] Sample website text: {lead.get('website_text', '')[:200]}...")
                
                llm_results = await batch_llm_analyze_companies(actual_leads_for_llm, user_industry, keywords_list, negative_keywords_list)
                logger.info(f"[ENHANCED ANALYSIS] batch_llm_analyze_companies returned results for {len(llm_results)} leads.")
                logger.info(f"[DEBUG] First LLM result: {llm_results[0] if llm_results else 'No results'}")
                
                for i, res in enumerate(leads_for_llm):
                    llm_result = llm_results[i] if i < len(llm_results) else {
                        "keyword_score": 0, 
                        "risk_score": 50, 
                        "growth_potential_score": 50,
                        "keyword_reason": "No LLM result",
                        "risk_reason": "No analysis available",
                        "growth_reason": "No analysis available",
                        "investment_recommendation": "Moderate",
                        "key_strengths": [],
                        "key_concerns": []
                    }
                    
                    # Calculate scores from AI analysis
                    raw_keyword_score = llm_result.get('keyword_score', 0)
                    # Use dynamic weights based on industry
                    dynamic_weights = get_industry_weights(user_industry)
                    # Adjust keyword score to fit within existing keyword weight (20% of total)
                    keyword_score = max(0, min(dynamic_weights['keywords'], int(round(raw_keyword_score * dynamic_weights['keywords'] / 100))))
                    
                    raw_growth_score = llm_result.get('growth_potential_score', 50)
                    # Adjust growth score to fit within growth potential weight (15% of total)
                    growth_score = max(0, min(dynamic_weights.get('growth_potential', 15), int(round(raw_growth_score * dynamic_weights.get('growth_potential', 15) / 100))))
                    
                    risk_score = llm_result.get('risk_score', 50)
                    
                    # Add scores to final result
                    res['score'] += keyword_score + growth_score
                    res['lead']['ai_analysis'] = llm_result
                    res['lead']['risk_score'] = risk_score
                    res['lead']['growth_potential_score'] = raw_growth_score
                    res['lead']['investment_recommendation'] = llm_result.get('investment_recommendation', 'Moderate')
                    
                    # AI analysis results are only used in memory
                    logger.info(f"[AI ANALYSIS] Fresh AI analysis completed for {res['lead'].get('Company Name', 'Unknown')} - results not stored")
                    
                    # Update explanation with AI insights
                    explanation_parts = [res['explanation']]
                    
                    # Add keyword analysis (only if keywords were provided)
                    if keywords_list:
                        if raw_keyword_score > 70:
                            explanation_parts.append(f"Keywords: {raw_keyword_score}/100 (Excellent match)")
                        elif raw_keyword_score > 40:
                            explanation_parts.append(f"Keywords: {raw_keyword_score}/100 (Good match)")
                        else:
                            explanation_parts.append(f"Keywords: {raw_keyword_score}/100 (Poor match)")
                    
                    # Add growth analysis
                    if raw_growth_score > 70:
                        explanation_parts.append(f"Growth: {raw_growth_score}/100 (High potential)")
                    elif raw_growth_score > 40:
                        explanation_parts.append(f"Growth: {raw_growth_score}/100 (Moderate potential)")
                    else:
                        explanation_parts.append(f"Growth: {raw_growth_score}/100 (Low potential)")
                    
                    # Add AI insights
                    if llm_result.get('key_strengths'):
                        explanation_parts.append(f"Strengths: {', '.join(llm_result['key_strengths'][:2])}")
                    
                    if llm_result.get('key_concerns'):
                        explanation_parts.append(f"Concerns: {', '.join(llm_result['key_concerns'][:2])}")
                    
                    # Add investment recommendation
                    if llm_result.get('investment_recommendation') == 'Strong':
                        explanation_parts.append("🎯 Strong Investment")
                    elif llm_result.get('investment_recommendation') == 'Moderate':
                        explanation_parts.append("📊 Moderate Investment")
                    else:
                        explanation_parts.append("⚠️ Weak Investment")
                    
                    res['explanation'] = " | ".join(explanation_parts)
                    
                    logger.info(f"[ENHANCED ANALYSIS] Lead: {res['lead'].get('name', res['lead'].get('Company Name', 'Unknown'))} | Keyword: {raw_keyword_score}/100 → {keyword_score} | Growth: {raw_growth_score}/100 → {growth_score} | Risk: {risk_score}/100 | Recommendation: {llm_result.get('investment_recommendation', 'Moderate')}")
            except Exception as e:
                logger.error(f"[ENHANCED ANALYSIS] Error in batch_llm_analyze_companies: {e}")
                # Continue without AI analysis if it fails
        else:
            logger.info(f"[FRESH ANALYSIS] All leads processed with fresh AI analysis (no caching)")
                
            logger.info(f"[HYBRID ANALYSIS] Lead: {lead.get('Company Name', 'Unknown')} | Using existing analysis + keyword score: {keyword_score}/100")
                
            logger.info(f"[HYBRID ANALYSIS] Lead: {lead.get('Company Name', 'Unknown')} | Using existing analysis only")

        # Prepare the result list, ensuring no ObjectId fields remain
        result = []
        for item in scored_leads:
            lead = item['lead'] if 'lead' in item else item
            score = item['score'] if 'score' in item else 0
            
            # Debug logging to see the structure
            logger.info(f"[DEBUG] Item keys: {list(item.keys())}")
            logger.info(f"[DEBUG] Lead keys: {list(lead.keys())}")
            logger.info(f"[DEBUG] AI analysis in lead: {'ai_analysis' in lead}")
            logger.info(f"[DEBUG] Risk score in lead: {'risk_score' in lead}")
            logger.info(f"[DEBUG] Growth score in lead: {'growth_potential_score' in lead}")
            
            lead_copy = lead.copy()
            
            # Remove ObjectId if present and convert any remaining ObjectIds
            if '_id' in lead_copy:
                lead_copy.pop('_id', None)
            
            # Remove any other ObjectId fields if present
            for k, v in list(lead_copy.items()):
                if str(type(v)).endswith("ObjectId'>"):
                    lead_copy[k] = str(v)
            
            # Ensure all AI analysis data is preserved in the final result
            lead_copy['score'] = score
            lead_copy['revenue'] = lead.get('revenue') or lead.get('Revenue')
            lead_copy['keywords'] = lead.get('keywords') or lead.get('Keywords')
            
            # Preserve AI analysis data
            if 'ai_analysis' in lead:
                lead_copy['ai_analysis'] = lead['ai_analysis']
            if 'risk_score' in lead:
                lead_copy['risk_score'] = lead['risk_score']
            if 'growth_potential_score' in lead:
                lead_copy['growth_potential_score'] = lead['growth_potential_score']
            if 'investment_recommendation' in lead:
                lead_copy['investment_recommendation'] = lead['investment_recommendation']
            
            # Add explanation if available
            if 'explanation' in item:
                lead_copy['explanation'] = item['explanation']
            
            # Remove internal scoring data that's no longer needed
            lead_copy.pop('industry_weights', None)
            lead_copy.pop('industry_criteria', None)
            lead_copy.pop('positioning_score', None)
            
            # Debug logging for final result
            logger.info(f"[DEBUG] Final lead_copy keys: {list(lead_copy.keys())}")
            logger.info(f"[DEBUG] Final AI analysis present: {'ai_analysis' in lead_copy}")
            logger.info(f"[DEBUG] Final risk score present: {'risk_score' in lead_copy}")
            logger.info(f"[DEBUG] Final growth score present: {'growth_potential_score' in lead_copy}")
            
            result.append(lead_copy)
        
        return result[:top_n]
    
    @staticmethod
    def get_industry_weights(industry: str) -> dict:
        """Get industry-specific scoring weights based on PE investment patterns."""
        industry_lower = industry.lower()

        industry_weights_map = {
            'education': {
                'revenue': 30,
                'employees': 25,
                'keywords': 25,
                'valid_contact': 10,
                'growth_potential': 10
            },
            'technology': {
                'revenue': 30,
                'employees': 20,
                'keywords': 20,
                'valid_contact': 10,
                'growth_potential': 20
            },
            'healthcare': {
                'revenue': 25,
                'employees': 25,
                'keywords': 20,
                'valid_contact': 10,
                'growth_potential': 20
            },
            'manufacturing': {
                'revenue': 35,
                'employees': 25,
                'keywords': 20,
                'valid_contact': 10,
                'growth_potential': 10
            },
            'construction': {
                'revenue': 30,
                'employees': 25,
                'keywords': 20,
                'valid_contact': 10,
                'growth_potential': 15
            }
        }

        # Define keywords to map categories to industry weights
        industry_keywords_map = {
            'education': ['education', 'edtech', 'learning', 'training'],
            'technology': ['technology', 'software', 'saas', 'ai', 'tech'],
            'healthcare': ['healthcare', 'medical', 'biotech', 'pharma'],
            'manufacturing': ['manufacturing', 'industrial', 'production'],
            'construction': ['construction', 'building', 'contractor']
        }

        for key, keywords in industry_keywords_map.items():
            if any(term in industry_lower for term in keywords):
                return industry_weights_map[key]

        # Default weights
        return {
            'revenue': 30,
            'employees': 25,
            'keywords': 20,
            'valid_contact': 10,
            'growth_potential': 15
        }
    async def score_companies_batch(self, companies: List[dict], preferences: dict) -> List[dict]:
        user_industry = preferences.get("industry", "")
        user_keywords = preferences.get("keywords", "")
        negative_keywords = preferences.get("negative_keywords", "")
        keywords_list = [k.strip() for k in user_keywords.split(",")] if user_keywords else []
        negative_keywords_list = [k.strip() for k in negative_keywords.split(",")] if negative_keywords else []

        from .enhanced_scraping_service import EnhancedScrapingService
        enhanced_scraper = EnhancedScrapingService(None)  # No DB collection

        # Concurrently scrape companies' websites
        async def fetch_scrape(company):
            company_name = company.get('company') or company.get('name') or ""
            website_url = company.get('website') or company.get('Website') or None
            city = company.get('city') or company.get('City') or None
            state = company.get('state') or company.get('State') or None
            scraped_data = await enhanced_scraper.scrape_company(company_name, website_url, keywords_list, city, state)
            company['website_text'] = scraped_data.get('text_snippet', '')

        await asyncio.gather(*(fetch_scrape(company) for company in companies))

        # LLM batch analysis
        llm_analysis = await batch_llm_analyze_companies(companies, user_industry, keywords_list, negative_keywords_list)

        # Weights based on industry
        WEIGHTS = MLService.get_industry_weights(user_industry)

        results = []
        for idx, company in enumerate(companies):
            company_name = company.get('company') or company.get('name') or f"Company_{idx+1}"
            analysis_result = llm_analysis[idx]

            # --- Revenue scoring ---
            min_rev = preferences.get('min_revenue')
            max_rev = preferences.get('max_revenue')
            target_rev = preferences.get('target_revenue')
            lead_rev = company.get('revenue') or company.get('Revenue')
            lead_rev_parsed = self.parse_revenue(lead_rev)
            max_rev_score = WEIGHTS.get('revenue', 0)
            edge_score = 5
            rev_score = 0
            if lead_rev_parsed is not None and min_rev is not None and max_rev is not None and target_rev is not None:
                try:
                    min_rev_f = float(min_rev)
                    max_rev_f = float(max_rev)
                    target_rev_f = float(target_rev)
                    if lead_rev_parsed < min_rev_f or lead_rev_parsed > max_rev_f:
                        rev_score = 0
                    else:
                        range_span = max(abs(target_rev_f - min_rev_f), abs(max_rev_f - target_rev_f))
                        dist = abs(lead_rev_parsed - target_rev_f)
                        if range_span == 0:
                            rev_score = max_rev_score
                        else:
                            rev_score = edge_score + (max_rev_score - edge_score) * (1 - (dist / range_span))
                        rev_score = max(edge_score, rev_score)
                        if lead_rev_parsed == target_rev_f:
                            rev_score = max_rev_score
                        elif lead_rev_parsed == min_rev_f or lead_rev_parsed == max_rev_f:
                            rev_score = edge_score
                        rev_score = int(round(rev_score))
                except Exception as e:
                    logger.error(f"[SCORING] Revenue scoring error: {e}")
            # --- Employee scoring ---
            min_emp = preferences.get('min_employees')
            max_emp = preferences.get('max_employees')
            target_emp = preferences.get('target_employees')
            lead_emp = company.get('employees') or company.get('Employees')
            lead_emp_parsed = self.parse_employees(lead_emp)
            max_emp_score = WEIGHTS.get('employees', 0)
            emp_score = 0
            if lead_emp_parsed is not None and min_emp is not None and max_emp is not None and target_emp is not None:
                try:
                    min_emp_f = float(min_emp)
                    max_emp_f = float(max_emp)
                    target_emp_f = float(target_emp)
                    if lead_emp_parsed < min_emp_f or lead_emp_parsed > max_emp_f:
                        emp_score = 0
                    else:
                        range_span = max(abs(target_emp_f - min_emp_f), abs(max_emp_f - target_emp_f))
                        dist = abs(lead_emp_parsed - target_emp_f)
                        if range_span == 0:
                            emp_score = max_emp_score
                        else:
                            emp_score = edge_score + (max_emp_score - edge_score) * (1 - (dist / range_span))
                        emp_score = max(edge_score, emp_score)
                        if lead_emp_parsed == target_emp_f:
                            emp_score = max_emp_score
                        elif lead_emp_parsed == min_emp_f or lead_emp_parsed == max_emp_f:
                            emp_score = edge_score
                        emp_score = int(round(emp_score))
                except Exception as e:
                    logger.error(f"[SCORING] Employee scoring error: {e}")

            # Combine raw LLM scores using industry-specific weights
            weighted_keywords = WEIGHTS.get('keywords', 0) * (analysis_result.get('keyword_score', 0) / 100)
            weighted_growth = WEIGHTS.get('growth_potential', 0) * (analysis_result.get('growth_potential_score', 0) / 100)
            weighted_revenue = rev_score  # Already out of 30
            weighted_employees = emp_score  # Already out of 25
            weighted_valid_contact = WEIGHTS.get('valid_contact', 0) * 0  # Still 0 unless you want to add contact scoring
            debug_sum = weighted_keywords + weighted_growth + weighted_revenue + weighted_employees + weighted_valid_contact
            logger.info(f"[SCORING COMPONENTS] {company_name} | weighted_keywords: {weighted_keywords} | weighted_growth: {weighted_growth} | weighted_revenue: {weighted_revenue} | weighted_employees: {weighted_employees} | weighted_valid_contact: {weighted_valid_contact} | SUM: {debug_sum}")
            total_score = debug_sum
            logger.info(f"[SCORING DEBUG] {company_name} | Revenue: {rev_score}/{WEIGHTS.get('revenue', 0)} | Employees: {emp_score}/{WEIGHTS.get('employees', 0)} | Keywords: {analysis_result.get('keyword_score', 0)}/{WEIGHTS.get('keywords', 0)} | Growth: {analysis_result.get('growth_potential_score', 0)}/{WEIGHTS.get('growth_potential', 0)} | Total: {total_score}/100")
            # Removed risk adjustment from total_score

            analysis = {
                "total_score": round(total_score, 2),
                "investment_recommendation": analysis_result.get('investment_recommendation', 'Moderate'),
                "growth_potential": {
                    "score": analysis_result.get('growth_potential_score', 0),
                    "explanation": analysis_result.get('growth_reason', '')
                },
                "risk": {
                    "score": analysis_result.get('risk_score', 0),
                    "explanation": analysis_result.get('risk_reason', '')
                },
                "keywords": {
                    "score": analysis_result.get('keyword_score', 0),
                    "explanation": analysis_result.get('keyword_reason', '')
                },
                "strengths": analysis_result.get('key_strengths', []),
                "concerns": analysis_result.get('key_concerns', []),
            }
            results.append({"company": company_name, "analysis": analysis})

        return results