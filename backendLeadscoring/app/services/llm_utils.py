import os
import logging
import rapidfuzz
import httpx
import json
import google.generativeai as genai
import asyncio

logger = logging.getLogger("ml_service")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "google/gemini-2.0-flash-exp:free"

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_MODEL = "deepseek-chat"

async def openrouter_chat(messages):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set.")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://your-app.com/",
        "X-Title": "Lead Scoring"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.2
    }
    max_retries = 5
    delay = 2
    for attempt in range(max_retries):
        await asyncio.sleep(1)  # Throttle to 1 request per second
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
                if resp.status_code == 429:
                    logger.warning(f"[LLM RETRY] 429 Too Many Requests, attempt {attempt+1}/{max_retries}, waiting {delay}s")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                resp.raise_for_status()
                data = resp.json()
                if 'choices' in data and data['choices']:
                    return data['choices'][0]['message']['content']
                else:
                    return {"keyword_score": 0, "reason": "No response from LLM", "positive_keyword_matches": [], "negative_keyword_matches": []}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                logger.warning(f"[LLM RETRY] 429 Too Many Requests (exception), attempt {attempt+1}/{max_retries}, waiting {delay}s")
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise
        except Exception as e:
            logger.error(f"[LLM ERROR] {e}")
            if attempt == max_retries - 1:
                return {"keyword_score": 0, "reason": str(e), "positive_keyword_matches": [], "negative_keyword_matches": []}
            await asyncio.sleep(delay)
            delay *= 2
    return {"keyword_score": 0, "reason": "[ERROR] Client error '429 Too Many Requests'", "positive_keyword_matches": [], "negative_keyword_matches": []}

async def deepseek_chat(messages):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set.")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",  # Replace with DeepSeek's exact model name
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.2,
    }
    max_retries = 5
    delay = 2
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
                
                if resp.status_code == 429:
                    logger.warning(f"[LLM RETRY] 429 Too Many Requests, attempt {attempt+1}/{max_retries}, waiting {delay}s")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                resp.raise_for_status()
                data = resp.json()
                
                if 'choices' in data and data['choices']:
                    return data['choices'][0]['message']['content']
                else:
                    return {"keyword_score": 0, "reason": "No response from LLM", "positive_keyword_matches": [], "negative_keyword_matches": []}
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                logger.warning(f"[LLM RETRY] 429 (exception), attempt {attempt+1}/{max_retries}, waiting {delay}s")
                await asyncio.sleep(delay)
                delay *= 2
                continue
        
        except Exception as e:
            logger.error(f"[LLM ERROR] {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(delay)
            delay *= 2
            
    return {"keyword_score": 0, "reason": "[ERROR] Client error '429 Too Many Requests'", "positive_keyword_matches": [], "negative_keyword_matches": []}

async def batch_llm_analyze_companies(leads_batch, user_industry, keywords_list, negative_keywords_list):
    """
    Enhanced analysis: Scores a batch of leads using a single Deepeek API call for keywords, risk, and growth potential.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("[ENHANCED BATCH LLM] DEEPSEEK_API_KEY not set in environment variables")
        return [{"keyword_score": 0, "risk_score": 50, "growth_potential_score": 50, "keyword_reason": "API key not set.", "risk_reason": "No analysis available", "growth_reason": "No analysis available", "investment_recommendation": "Moderate", "key_strengths": [], "key_concerns": []}] * len(leads_batch)

    # logger.info(f"[ENHANCED BATCH LLM] GEMINI_API_KEY found: {api_key[:10]}...")
    # genai.configure(api_key=api_key)
    # model = genai.GenerativeModel('gemini-1.5-flash')

    prompt_header = f"""
As a private equity investment analyst, analyze each company for comprehensive investment potential.

**User's Investment Criteria:**
- Target Industry: {user_industry}
- Positive Keywords: {', '.join(keywords_list)}
- Negative Keywords: {', '.join(negative_keywords_list)}

**CRITICAL: You MUST return ONLY a valid JSON array. DO NOT include any markdown code fences like ```json. No other text before or after the JSON.**

**Analysis Requirements:**
Return a single, valid JSON array of objects, one for each company. The response must start with [ and end with ].
Each JSON object must have these exact keys:
- "company_name": The exact name of the company from the input.
- "keyword_score": An integer score from 0 to 100 based on keyword relevance to the target industry.
- "risk_score": An integer score from 0 to 100 (0=low risk, 100=high risk) based on investment risk assessment.
- "growth_potential_score": An integer score from 0 to 100 based on growth potential and scalability.
- "keyword_reason": An array of 2-3 strings explaining the keyword score in precise points.
- "risk_reason": An array of 2-3 strings explaining the risk assessment in precise points.
- "growth_reason": An array of 2-3 strings explaining the growth potential in precise points.
- "investment_recommendation": One of "Strong", "Moderate", or "Weak".
- "key_strengths": An array of 2-3 key strengths for this company.
- "key_concerns": An array of 2-3 key concerns or risks for this company.

**Analysis Guidelines:**
- Keyword Score: Consider relevance to target industry and keyword matches
- Risk Score: Consider industry risks, business model, market position, dependencies
- Growth Score: Consider innovation, scalability, market expansion potential, technology adoption
- Investment Recommendation: Based on overall analysis of all factors

**IMPORTANT: Your response must be a valid JSON array starting with [ and ending with ]. No other text.**

Here is the list of companies to analyze:
"""

    company_prompts = []
    lead_names = []
    for i, lead in enumerate(leads_batch):
        company_name = str(lead.get('name') or lead.get('Company Name', f'Unknown Lead {i+1}'))
        lead_names.append(company_name)
        description = lead.get('description') or lead.get('Product/Service Category') or ''
        website_text = lead.get('website_text', '')[:3000]  # Reduced for combined analysis
        revenue = lead.get('revenue') or lead.get('Revenue') or 'Unknown'
        employees = lead.get('employees') or lead.get('Employees') or 'Unknown'
        location = lead.get('location') or lead.get('Location') or 'Unknown'
        
        company_prompts.append(f"""--- Company Start ---
Name: "{company_name}"
Description: "{description}"
Website Content: "{website_text}"
Revenue: {revenue}
Employees: {employees}
Location: {location}
--- Company End ---""")

    full_prompt = prompt_header + "\n\n" + "\n\n".join(company_prompts)
    messages = [{"role": "system", "content": full_prompt}]

    try:
        # response = await model.generate_content_async(
        #     full_prompt,
        #     generation_config={"temperature": 0.0}
        # )
        
        response = await deepseek_chat(messages)
        
        logger.info(f"[ENHANCED BATCH LLM] Raw LLM response: {response}")
        try:
            # Strip code fences and 'json' if present
            if isinstance(response, str):
                response_clean = response.strip()
                if response_clean.startswith('```'):
                    response_clean = response_clean.lstrip('`').lstrip('json').lstrip().rstrip('`').strip()
                response = response_clean
            # Try to parse the response as JSON
            llm_results = json.loads(response)
            
            # Handle different response formats
            if isinstance(llm_results, list):
                # Expected format - array of objects
                result_map = {item.get('company_name'): item for item in llm_results if isinstance(item, dict)}
            elif isinstance(llm_results, dict):
                # Single object response - wrap in array
                logger.warning("[ENHANCED BATCH LLM] LLM returned single object instead of array, wrapping in array")
                llm_results = [llm_results]
                result_map = {llm_results[0].get('company_name'): llm_results[0]} if llm_results[0].get('company_name') else {}
            else:
                raise ValueError(f"LLM response is neither list nor dict: {type(llm_results)}")
            
            final_ordered_results = []
            for name in lead_names:
                if name in result_map:
                    result = result_map[name]
                    # Ensure all required fields are present with defaults
                    final_ordered_results.append({
                        "keyword_score": result.get('keyword_score', 0),
                        "risk_score": result.get('risk_score', 50),
                        "growth_potential_score": result.get('growth_potential_score', 50),
                        "keyword_reason": result.get('keyword_reason', 'No keyword analysis provided'),
                        "risk_reason": result.get('risk_reason', 'No risk analysis provided'),
                        "growth_reason": result.get('growth_reason', 'No growth analysis provided'),
                        "investment_recommendation": result.get('investment_recommendation', 'Moderate'),
                        "key_strengths": result.get('key_strengths', []),
                        "key_concerns": result.get('key_concerns', [])
                    })
                else:
                    logger.warning(f"[ENHANCED BATCH LLM] LLM response did not include a result for company: {name}")
                    final_ordered_results.append({
                        "keyword_score": 0,
                        "risk_score": 50,
                        "growth_potential_score": 50,
                        "keyword_reason": "LLM response did not include this company",
                        "risk_reason": "No analysis available",
                        "growth_reason": "No analysis available",
                        "investment_recommendation": "Moderate",
                        "key_strengths": [],
                        "key_concerns": []
                    })
            return final_ordered_results
        except json.JSONDecodeError as e:
            logger.error(f"[ENHANCED BATCH LLM ERROR] JSON decode failed: {e} | Raw response: {response}")
            # Try to extract JSON from the response if it's wrapped in text
            try:
                # Look for JSON array in the response
                import re
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    llm_results = json.loads(json_str)
                    if isinstance(llm_results, list):
                        result_map = {item.get('company_name'): item for item in llm_results if isinstance(item, dict)}
                        final_ordered_results = []
                        for name in lead_names:
                            if name in result_map:
                                result = result_map[name]
                                final_ordered_results.append({
                                    "keyword_score": result.get('keyword_score', 0),
                                    "risk_score": result.get('risk_score', 50),
                                    "growth_potential_score": result.get('growth_potential_score', 50),
                                    "keyword_reason": result.get('keyword_reason', 'No keyword analysis provided'),
                                    "risk_reason": result.get('risk_reason', 'No risk analysis provided'),
                                    "growth_reason": result.get('growth_reason', 'No growth analysis provided'),
                                    "investment_recommendation": result.get('investment_recommendation', 'Moderate'),
                                    "key_strengths": result.get('key_strengths', []),
                                    "key_concerns": result.get('key_concerns', [])
                                })
                            else:
                                final_ordered_results.append({
                                    "keyword_score": 0,
                                    "risk_score": 50,
                                    "growth_potential_score": 50,
                                    "keyword_reason": "LLM response parsing recovered but company not found",
                                    "risk_reason": "Analysis failed",
                                    "growth_reason": "Analysis failed",
                                    "investment_recommendation": "Moderate",
                                    "key_strengths": [],
                                    "key_concerns": []
                                })
                        return final_ordered_results
            except Exception as recovery_error:
                logger.error(f"[ENHANCED BATCH LLM ERROR] JSON recovery also failed: {recovery_error}")
            
            return [{
                "keyword_score": 0,
                "risk_score": 50,
                "growth_potential_score": 50,
                "keyword_reason": f"LLM response parse error: {e}",
                "risk_reason": "Analysis failed",
                "growth_reason": "Analysis failed",
                "investment_recommendation": "Moderate",
                "key_strengths": [],
                "key_concerns": []
            } for _ in lead_names]
        except Exception as e:
            logger.error(f"[ENHANCED BATCH LLM ERROR] JSON parsing failed: {e} | Raw response: {response}")
            return [{
                "keyword_score": 0,
                "risk_score": 50,
                "growth_potential_score": 50,
                "keyword_reason": f"LLM response parse error: {e}",
                "risk_reason": "Analysis failed",
                "growth_reason": "Analysis failed",
                "investment_recommendation": "Moderate",
                "key_strengths": [],
                "key_concerns": []
            } for _ in lead_names]
    except Exception as e:
        logger.error(f"[ENHANCED BATCH LLM ERROR] Exception in batch_llm_analyze_companies: {e}")
        return [{
            "keyword_score": 0,
            "risk_score": 50,
            "growth_potential_score": 50,
            "keyword_reason": f"Exception: {e}",
            "risk_reason": "Analysis failed",
            "growth_reason": "Analysis failed",
            "investment_recommendation": "Moderate",
            "key_strengths": [],
            "key_concerns": []
        } for _ in lead_names]

# The old llm_judge_keywords is no longer needed with the new batching logic.

# Gemini API rate limits:
# - Free tier: 60 requests per minute (1 request per second)
# - Paid tier: higher limits (see https://ai.google.dev/pricing)
# - To check your usage, go to https://makersuite.google.com/app/apikey and view quota/usage info.

async def gemini_tiebreaker(leads: list, context: str = "") -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"explanation": "GEMINI_API_KEY not set.", "ranking": list(range(len(leads)))}
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        lead_descriptions = []
        for lead in leads:
            name = lead.get('name', 'Unknown')
            desc = f"{name}:\n"
            for k, v in lead.items():
                desc += f"  {k}: {v}\n"
            lead_descriptions.append(desc)
        prompt = (
            "You are an expert B2B sales analyst. Given the following leads, which are currently tied in our ML scoring system, provide a concise, user-friendly, and actionable explanation using ONLY bullet points. "
            "Do NOT repeat facts that are already visible in the table (such as employee count, revenue, or company location) unless you are drawing a unique insight or comparison. "
            "Focus on providing unique, strategic, or actionable insights that a business user would not immediately see from the table. "
            "Each bullet must provide a unique, non-overlapping insight. "
            "Do not use 'Lead X' or numbers—always use the company name. "
            "Do not include any paragraphs or prose—just bullet points. "
            "Mention company names in your explanation. Keep each bullet short and clear for a business user. "
            "\n\nIMPORTANT:\n"
            "When listing the ranking, copy and paste the company names exactly as shown above. Do not change, abbreviate, or omit any names. Include every company in your ranking, even if you have no strong preference for some.\n"
            "Double-check that your ranking includes every company name from the list above, with no omissions or changes.\n"
            "At the end, output the ranking as a single line, comma-separated, in this format:\n"
            "Ranking: Company Name 1, Company Name 2, Company Name 3, ...\n\n"
            "Example:\n"
            "- Acme Corp: Strong leadership team.\n"
            "- Beta LLC: Innovative product line.\n"
            "- Gamma Inc: Long market history.\n"
            "Ranking: Acme Corp, Beta LLC, Gamma Inc\n\n"
            f"{context}\n\n" + "\n".join(lead_descriptions) +
            "\n\nRespond in this format:\n- <insight 1>\n- <insight 2>\nRanking: <comma-separated company names in preferred order>\n"
        )
        response = model.generate_content(prompt)
        text = response.text
        explanation = ""
        ranking = list(range(len(leads)))
        if "Explanation:" in text:
            explanation = text.split("Explanation:",1)[1].split("Ranking:",1)[0].strip()
        else:
            lines = text.splitlines()
            bullet_lines = []
            for line in lines:
                if line.strip().startswith('-'):
                    bullet_lines.append(line.strip())
                if 'Ranking:' in line:
                    break
            explanation = '\n'.join(bullet_lines)
        if "Ranking:" in text:
            ranking_line = text.split("Ranking:",1)[1].strip().splitlines()[0]
            company_names = [lead.get('name', 'Unknown') for lead in leads]
            ranking = []
            used_indices = set()
            for name in ranking_line.split(","):
                name = name.strip()
                if name in company_names and company_names.index(name) not in used_indices:
                    idx = company_names.index(name)
                    ranking.append(idx)
                    used_indices.add(idx)
                else:
                    best_score = 0
                    best_idx = None
                    for i, cname in enumerate(company_names):
                        if i in used_indices:
                            continue
                        import rapidfuzz
                        score = rapidfuzz.fuzz.ratio(name.lower(), cname.lower())
                        if score > best_score:
                            best_score = score
                            best_idx = i
                    if best_score >= 90 and best_idx is not None:
                        ranking.append(best_idx)
                        used_indices.add(best_idx)
            if not ranking:
                try:
                    ranking = [int(x.strip())-1 for x in ranking_line.split(",") if x.strip().isdigit()]
                except Exception:
                    pass
        return {"explanation": explanation, "ranking": ranking if ranking else list(range(len(leads)))}
    except Exception as e:
        logger.error(f"[GEMINI TIEBREAKER ERROR] {e}")
        return {"explanation": f"Failed to generate explanation", "ranking": list(range(len(leads)))} 