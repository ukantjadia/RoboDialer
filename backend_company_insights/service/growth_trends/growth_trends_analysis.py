import os
import logging
import httpx
import json
import asyncio

logger = logging.getLogger("growth_trends")

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


async def analyze_growth_trends(company_data_json):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error(
            "[GROWTH TRENDS] DEEPSEEK_API_KEY not set in environment variables"
        )
        return {
            "company_name": "Unknown",
            "current_growth_stage": "Unknown",
            "growth_trend": "Unknown",
            "growth_trend_score": 50,
            "maturity_index": 0,
            "trend_insights": ["API key not set"],
            "growth_drivers": [],
            "growth_inhibitors": [],
            "scalability_assessment": {
                "level": "Unknown",
                "reasons": ["API key missing"],
            },
            "timeline_outlook": {"short_term": "Unknown", "medium_term": "Unknown"},
            "recommendation": "Unable to analyze",
            "data_confidence": {"level": "Low", "missing": ["API key not set"]},
        }

    # Extract company information from the JSON
    results = company_data_json.get("results", [])
    if not results:
        return {
            "company_name": "Unknown",
            "current_growth_stage": "Unknown",
            "growth_trend": "Unknown",
            "growth_trend_score": 50,
            "maturity_index": 0,
            "trend_insights": ["No company data provided"],
            "growth_drivers": [],
            "growth_inhibitors": [],
            "scalability_assessment": {
                "level": "Unknown",
                "reasons": ["No company data"],
            },
            "timeline_outlook": {"short_term": "Unknown", "medium_term": "Unknown"},
            "recommendation": "Unable to analyze",
            "data_confidence": {
                "level": "Low",
                "missing": ["No company data provided"],
            },
        }

    # Create the analysis prompt
    prompt_header = f"""
As a growth trends analyst, analyze the following company data to identify growth trends, patterns, and future growth trajectory.

CRITICAL: You MUST return ONLY a valid JSON object. DO NOT include any markdown code fences like ```

Input notes:
- You will receive a complex JSON structure containing:
  - results[].company: company name
  - results[].company_detail.company_data: company information including bio, LI_specialties, yearly_revenue_text, number_of_employees_text, founded, URL, etc.
  - results[].company_detail.company_outside_tech_data: array of technologies used
  - results[].company_detail.indeed_data: recent job postings
  - results[].analysis: existing investment analysis with total_score, investment_recommendation, growth_potential (score, explanation[]), risk (score, explanation[]), keywords (score, explanation[]), strengths[], concerns[]
- Use ONLY the provided data. Do not fabricate information. If critical data is missing, set values to null and list gaps in data_confidence.missing.

Analysis Requirements:
Return a single JSON object with these exact keys:
- "company_name": String. Extract from results[].company.
- "current_growth_stage": One of "Early", "Growth", "Mature", "Decline", "Turnaround".
- "growth_trend": One of "Accelerating", "Steady", "Slowing", "Stagnant", "Declining".
- "growth_trend_score": Integer 0-100. Calculate as: (growth_potential.score * 0.7) - (risk.score * 0.3), capped at 0-100 range.
- "maturity_index": Integer 0-100. Base on: company age from founded (if available), revenue scale from yearly_revenue_text, employee count from number_of_employees_text. Missing founded year reduces score by 20 points.
- "trend_insights": Array of 3-4 concise insights explaining growth trajectory using bio, tech stack diversity, hiring activity, and existing analysis.
- "growth_drivers": Array of 2-4 factors from bio, LI_specialties, tech adoption (company_outside_tech_data count), recent hiring (indeed_data), and analysis.strengths.
- "growth_inhibitors": Array of 2-4 constraints from analysis.concerns, risk explanations, tech stack limitations, or business model constraints.
- "scalability_assessment": Object with:
  - "level": "High", "Medium", or "Low" based on tech stack sophistication, platform vs service model, and hiring for growth roles.
  - "reasons": Array of 2-3 brief explanations tied to technology adoption, business model, and market approach.
- "timeline_outlook": Object with:
  - "short_term": "Stable", "Improvement with execution", or "At risk" based on recent hiring, investment recommendation, and immediate risks.
  - "medium_term": "Slow Growth", "Accelerating", or "Turnaround needed" based on market position and scalability factors.
- "recommendation": Map from investment_recommendation: "Strong"→"Strong Growth Potential", "Moderate"→"Moderate Growth Potential", "Weak"→"Limited Growth Potential".
- "data_confidence": Object with:
  - "level": "High" if all key fields present, "Moderate" if missing 1-2 key fields, "Low" if missing 3+ key fields.
  - "missing": Array listing absent critical data (e.g., "Founded year unknown", "Limited historical data", "Revenue growth trends unavailable").

Analysis Guidelines:
- Extract company_name from results[].company field.
- Use company_detail.company_data for basic company information (bio, specialties, revenue, employees, founded).
- Count company_outside_tech_data entries to assess technology adoption sophistication (>20 technologies suggests high tech adoption).
- Analyze indeed_data for hiring patterns - growth-focused roles like "Director of Marketing and Growth" indicate expansion phase.
- Integrate existing analysis scores: use growth_potential.score and risk.score for trend calculations, incorporate strengths/concerns into drivers/inhibitors.
- For maturity_index calculation:
  - Founded year: <5 years = 20pts, 5-10 years = 40pts, >10 years = 60pts, unknown = 0pts
  - Revenue scale: <$1M = 10pts, $1-10M = 20pts, $10-100M = 30pts, >$100M = 40pts
  - Employee count: <20 = 10pts, 20-100 = 20pts, 100-500 = 30pts, >500 = 40pts
- For scalability_assessment, consider:
  - High tech adoption (many technologies) + platform business = "High"
  - Service-based with limited tech or unclear model = "Low"
  - Mixed signals or moderate tech adoption = "Medium"
- Keep all array items under 18 words, avoid generic statements, focus on specific insights from the provided data.
- If founded year is null/missing, note this impacts maturity assessment accuracy.

IMPORTANT: Your response must be a valid JSON object starting with {{ and ending with }}. No other text.

Here is the company data to analyze:


"""

    # Convert the company data to a formatted string for the prompt
    company_data_str = json.dumps(company_data_json, indent=2)
    full_prompt = prompt_header + "\n\n" + company_data_str

    # Prepare the API call
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": full_prompt}],
        "max_tokens": 1024,
        "temperature": 0.2,
    }

    # Make the API call with retry logic
    max_retries = 3
    delay = 2

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(
                    DEEPSEEK_API_URL, headers=headers, json=payload
                )

                if resp.status_code == 429:
                    logger.warning(
                        f"[GROWTH TRENDS] Rate limited, attempt {attempt+1}/{max_retries}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue

                resp.raise_for_status()
                data = resp.json()

                if "choices" in data and data["choices"]:
                    response_text = data["choices"][0]["message"]["content"]
                    logger.info(f"[GROWTH TRENDS] Raw response: {response_text}")

                    try:
                        # Parse the JSON response
                        growth_analysis = json.loads(response_text)

                        # Ensure all required fields are present with defaults
                        return {
                            "company_name": growth_analysis.get(
                                "company_name", "Unknown"
                            ),
                            "current_growth_stage": growth_analysis.get(
                                "current_growth_stage", "Unknown"
                            ),
                            "growth_trend": growth_analysis.get(
                                "growth_trend", "Unknown"
                            ),
                            "growth_trend_score": growth_analysis.get(
                                "growth_trend_score", 50
                            ),
                            "trend_insights": growth_analysis.get("trend_insights", []),
                            "growth_drivers": growth_analysis.get("growth_drivers", []),
                            "growth_risks": growth_analysis.get("growth_risks", []),
                            "growth_opportunities": growth_analysis.get(
                                "growth_opportunities", []
                            ),
                            "trend_recommendation": growth_analysis.get(
                                "trend_recommendation", "Moderate Growth Potential"
                            ),
                            "growth_timeline": growth_analysis.get(
                                "growth_timeline", "Unknown"
                            ),
                        }

                    except json.JSONDecodeError as e:
                        logger.error(f"[GROWTH TRENDS] JSON parsing failed: {e}")
                        # Try to extract JSON using regex
                        import re

                        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                        if json_match:
                            try:
                                json_str = json_match.group(0)
                                growth_analysis = json.loads(json_str)
                                return {
                                    "company_name": growth_analysis.get("company_name", "Unknown"),
                                    "current_growth_stage": growth_analysis.get("current_growth_stage", "Unknown"),
                                    "growth_trend": growth_analysis.get("growth_trend", "Unknown"),
                                    "growth_trend_score": growth_analysis.get("growth_trend_score", 50),
                                    "maturity_index": growth_analysis.get("maturity_index", 0),
                                    "trend_insights": growth_analysis.get("trend_insights", []),
                                    "growth_drivers": growth_analysis.get("growth_drivers", []),
                                    "growth_inhibitors": growth_analysis.get("growth_inhibitors", []),
                                    "scalability_assessment": growth_analysis.get(
                                        "scalability_assessment",
                                        {"level": "Unknown", "reasons": []},
                                    ),
                                    "timeline_outlook": growth_analysis.get(
                                        "timeline_outlook",
                                        {"short_term": "Unknown", "medium_term": "Unknown"},
                                    ),
                                    "recommendation": growth_analysis.get("recommendation", "Moderate Growth Potential"),
                                    "data_confidence": growth_analysis.get(
                                        "data_confidence",
                                        {"level": "Unknown", "missing": []},
                                    ),
                                }
                            except:
                                pass

                        return {
                            "company_name": "Unknown",
                            "current_growth_stage": "Unknown",
                            "growth_trend": "Unknown",
                            "growth_trend_score": 50,
                            "maturity_index": 0,
                            "trend_insights": [f"JSON parsing failed: {e}"],
                            "growth_drivers": [],
                            "growth_inhibitors": [],
                            "scalability_assessment": {"level": "Unknown", "reasons": ["JSON parsing failed"]},
                            "timeline_outlook": {"short_term": "Unknown", "medium_term": "Unknown"},
                            "recommendation": "Unable to analyze",
                            "data_confidence": {"level": "Low", "missing": ["JSON parsing failed"]},
                        }

        except Exception as e:
            logger.error(f"[GROWTH TRENDS] API call failed: {e}")
            if attempt == max_retries - 1:
                return {
                    "company_name": "Unknown",
                    "current_growth_stage": "Unknown",
                    "growth_trend": "Unknown",
                    "growth_trend_score": 50,
                    "maturity_index": 0,
                    "trend_insights": [f"API call failed: {e}"],
                    "growth_drivers": [],
                    "growth_inhibitors": [],
                    "scalability_assessment": {"level": "Unknown", "reasons": ["API call failed"]},
                    "timeline_outlook": {"short_term": "Unknown", "medium_term": "Unknown"},
                    "recommendation": "Unable to analyze",
                    "data_confidence": {"level": "Low", "missing": ["API call failed"]},
                }

            await asyncio.sleep(delay)
            delay *= 2

    return {
        "company_name": "Unknown",
        "current_growth_stage": "Unknown", 
        "growth_trend": "Unknown",
        "growth_trend_score": 50,
        "maturity_index": 0,
        "trend_insights": ["Max retries exceeded"],
        "growth_drivers": [],
        "growth_inhibitors": [],
        "scalability_assessment": {"level": "Unknown", "reasons": ["Max retries exceeded"]},
        "timeline_outlook": {"short_term": "Unknown", "medium_term": "Unknown"},
        "recommendation": "Unable to analyze",
        "data_confidence": {"level": "Low", "missing": ["Max retries exceeded"]},
    }
