import requests
import json
import logging

logger = logging.getLogger(__name__)

def estimate_revenue_batch(data, api_key):
    """
    Estimates revenue for a batch of companies using DeepSeek API.

    Args:
        data (list of dict): List of company data dictionaries
        api_key (str): DeepSeek API token

    Returns:
        list: Revenue estimates in the format ["Estimated Revenue: 2m - high", ...]
    """
    logger.info(f"Estimating revenue for {len(data)} companies.")
    # Construct the prompt
    prompt = (
        """
        Estimate the annual revenue (in USD) for each company using the following available information: name, industry, address, BBB rating (if available), phone (if available), and website (if available).
        Use publicly known patterns, industry norms, business size indicators, and address context to guide your estimates. If data is insufficient or unclear, respond conservatively and lower the confidence level.
        Output format (strictly adhere):
        Estimated Revenue: <number><unit> - <confidence>
        Where:
        <number> is a numeric estimate (e.g., 850, 2.4)
        <unit> is one of: k (thousand), m (million), or b (billion)
        <confidence> is one of: high, medium, or low
        Examples:
        "Estimated Revenue: 850k - medium"
        "Estimated Revenue: 2.4m - low"
        Guardrails:
        Do not assume revenue based on company name alone - use supporting context.
        If BBB rating, phone, or website is missing, still attempt an estimate but note that confidence may decrease.
        Avoid generating values that seem implausible based on the industry and address type (e.g., small-town auto shop with billion-dollar revenue).
        """
    )

    for company in data:
        prompt += (
            f"Company: {company['Company']}\n"
            f"Industry: {company['Industry']}\n"
            f"Address: {', '.join(company['Address']) if isinstance(company['Address'], list) else company['Address']}\n"
            f"BBB Rating: {company['BBB Rating']}\n"
            f"Website: {company['Website']}\n\n"
        )
    logger.debug(f"DeepSeek prompt: {prompt}")

    # Call DeepSeek API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "system", "content": "Respond ONLY with revenue estimates in the specified format, one per company. No additional text."}
        ],
        "temperature": 0.3
    }

    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        logger.info(f"DeepSeek API response: {content}")
        return [line.strip() for line in content.split('\n') if line.strip()]

    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return [f"Error: {str(e)}" for _ in data]