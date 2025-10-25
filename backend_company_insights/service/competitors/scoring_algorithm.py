import math
from typing import Dict, Tuple
from datetime import datetime, timezone
import re

# ------------------------------------------------
# FEATURE EXTRACTION UTILS
# ------------------------------------------------


def parse_text_range(value_text: str) -> float:
    """Parse a text representation of a range (e.g., "$1M - $2M") into a numeric value."""

    if not value_text or value_text.lower().strip() in ["n/a", "unknown", "-"]:
        return 0.0

    text = (
        value_text.lower().replace("$", "").replace("usd", "").replace(",", "").strip()
    )

    if "-" in text:
        parts = [p.strip() for p in text.split("-") if p.strip()]
        if len(parts) == 2:

            def parse_part(part: str) -> float:
                num_match = re.search(r"(\d+(?:\.\d+)?)", part)
                num = float(num_match.group(1)) if num_match else 0.0
                if "billion" in part:
                    num *= 1_000_000_000
                elif "million" in part:
                    num *= 1_000_000
                elif "thousand" in part:
                    num *= 1_000
                return num

            low = parse_part(parts[0])
            high = parse_part(parts[1])
            if high > 0.0 and low > 0.0:
                return (low + high) / 2
            if low > 0.0:
                return low
            if high > 0.0:
                return high
        return 0.0

    num_match = re.search(r"(\d+(?:\.\d+)?)", text)
    num = float(num_match.group(1)) if num_match else 0.0
    if "billion" in text:
        num *= 1_000_000_000
    elif "million" in text:
        num *= 1_000_000
    elif "thousand" in text:
        num *= 1_000
    return num


def classify_company_size(revenue: float) -> str:
    """Classify company size based on revenue."""

    if revenue == 0:
        return "UNKNOWN"
    if revenue < 1_000_000:
        return "STARTUP"
    if revenue < 10_000_000:
        return "SMALL"
    if revenue < 100_000_000:
        return "MEDIUM"
    if revenue < 1_000_000_000:
        return "LARGE"
    return "ENTERPRISE"


def clean_and_extract_features(org: Dict) -> Dict:
    """Extract features from Growjo data structure"""

    if "company_data" in org:
        company_data = org["company_data"]
        tech_data = org.get("company_outside_tech_data", [])
    else:
        company_data = org
        tech_data = org.get("company_outside_tech_data", [])

    # Extract revenue and employee count
    revenue_text = company_data.get("yearly_revenue", "")
    revenue_numeric = parse_text_range(revenue_text)

    employee_text = company_data.get("number_of_employees", "")
    employee_numeric = int(parse_text_range(employee_text))

    # Extract technologies
    tech_names = set()
    for tech in tech_data:
        tech_name = tech.get("technology", "").strip()
        if tech_name:
            tech_names.add(tech_name.lower())

    # Extract industry labels from multiple sources
    industry_sources = [
        company_data.get("industries", ""),
        company_data.get("tags", ""),
        company_data.get("LI_specialties", ""),
        company_data.get("industry_path", ""),
        company_data.get("sic_description", ""),
    ]

    industry_labels = []
    for source in industry_sources:
        if source:
            labels = [s.strip().lower() for s in source.split(",") if s.strip()]
            industry_labels.extend(labels)

    # Remove duplicates and clean
    industry_labels = list(set(industry_labels))

    # Extract business keywords from tags
    business_keywords = []
    tags = company_data.get("tags", "")
    if tags:
        business_keywords = [kw.strip().lower() for kw in tags.split(",") if kw.strip()]

    return {
        "id": str(company_data.get("company_id", "")),
        "name": company_data.get("company_name", ""),
        "domain": company_data.get("URL", ""),
        "sic_codes": (
            [company_data.get("sic_code", "")] if company_data.get("sic_code") else []
        ),
        "industry_labels": industry_labels,
        "business_keywords": business_keywords,
        "revenue": revenue_numeric,
        "revenue_printed": company_data.get(
            "yearly_revenue_text", company_data.get("yearly_revenue", "")
        ),
        "estimated_employees": employee_numeric,
        "city": company_data.get("city", ""),
        "technologies": list(tech_names),
        "size_tier": classify_company_size(revenue_numeric),
    }


# ------------------------------------------------
# SIMILARITY UTILITIES
# ------------------------------------------------


def jaccard(a: set, b: set) -> float:
    """Calculate Jaccard similarity between two sets."""

    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def normalized_log_revenue_similarity(a: float, b: float) -> float:
    """Calculate normalized log revenue similarity between two values."""

    if a == 0 or b == 0:
        return 0.0
    log_a, log_b = math.log10(a), math.log10(b)
    dist = abs(log_a - log_b) / max(log_a, log_b)
    return 1.0 - min(dist, 1.0)


# ------------------------------------------------
# CORE METRICS & PIPELINE
# ------------------------------------------------


def industry_similarity(x: Dict, y: Dict) -> float:
    """Calculate industry similarity between two companies."""

    codes_x = set(x["sic_codes"])
    codes_y = set(y["sic_codes"])
    sim_codes = jaccard(codes_x, codes_y)

    labels_x = set(x.get("industry_labels", []))
    labels_y = set(y.get("industry_labels", []))
    sim_labels = jaccard(labels_x, labels_y)

    return 0.7 * sim_codes + 0.3 * sim_labels


def size_similarity(x: Dict, y: Dict) -> float:
    """Calculate size similarity between two companies."""

    return normalized_log_revenue_similarity(x["revenue"], y["revenue"])


def tech_similarity(x: Dict, y: Dict) -> float:
    """Calculate technology similarity between two companies."""

    t_x, t_y = set(x.get("technologies", [])), set(y.get("technologies", []))
    if not t_x and not t_y:
        return 0.5 * industry_similarity(x, y)
    return jaccard(t_x, t_y)


def geo_similarity(x: Dict, y: Dict) -> float:
    """Calculate geographic similarity between two companies."""

    city_x = (x.get("city", "") or "").strip().lower()
    city_y = (y.get("city", "") or "").strip().lower()

    if city_x and city_y and city_x == city_y:
        return 1.0
    return 0.0


def composite_similarity(target: Dict, cand: Dict) -> Tuple[float, Dict]:
    """Calculate composite similarity score between target and candidate companies."""

    scores = {
        "industry": industry_similarity(target, cand),
        "size": size_similarity(target, cand),
        "tech": tech_similarity(target, cand),
        "geo": geo_similarity(target, cand),
    }

    weight = {"industry": 0.40, "size": 0.25, "tech": 0.20, "geo": 0.15}
    comp = sum(scores[k] * weight[k] for k in scores)
    scores["composite"] = comp
    # print(f"COMP: {comp}, Scores: {scores}")
    return comp, scores


# ------------------------------------------------
# CLASSIFICATION
# ------------------------------------------------


def competitor_type(comp_score: float, industry_score: float) -> str:
    """Determine the type of competitor based on similarity scores."""

    if comp_score >= 0.70 and industry_score >= 0.80:
        return "direct"
    if comp_score >= 0.40:
        return "indirect"
    if comp_score >= 0.25:
        return "substitute"
    if comp_score >= 0.15:
        return "emerging"
    return "not_competitor"


def confidence_level(comp_score: float) -> str:
    """Determine the confidence level based on composite similarity score."""

    if comp_score >= 0.75:
        return "high"
    if comp_score >= 0.50:
        return "medium"
    if comp_score >= 0.25:
        return "low"
    return "very_low"


# ------------------------------------------------
# PIPELINE RUN LOGIC
# ------------------------------------------------


def run_competitor_pipeline(
    growjo_data, target_company_name: str, target_city: str, top_n: int
):
    if isinstance(growjo_data, dict) and "company_details" in growjo_data:
        orgs = [
            clean_and_extract_features(company)
            for company in growjo_data["company_details"]
        ]
    elif isinstance(growjo_data, list):
        orgs = [clean_and_extract_features(company) for company in growjo_data]
    elif "company_data" in growjo_data:
        orgs = [clean_and_extract_features(growjo_data)]
    elif "organizations" in growjo_data:
        orgs = [
            clean_and_extract_features(org)
            for org in growjo_data.get("organizations", [])
        ]
    else:
        orgs = [
            clean_and_extract_features(company)
            for company in growjo_data.values()
            if isinstance(company, dict)
        ]

    # Find target company by name AND city
    target = None
    target_name_lower = (target_company_name or "").lower().strip()
    target_city_lower = (target_city or "").lower().strip()

    for org in orgs:
        org_name_lower = (org["name"] or "").lower().strip()
        org_city_lower = (org["city"] or "").lower().strip()

        # Exact match on both name and city
        if org_name_lower == target_name_lower and org_city_lower == target_city_lower:
            target = org
            break

    # If exact match not found, try partial matching on name with exact city match
    if not target:
        for org in orgs:
            org_name_lower = (org["name"] or "").lower().strip()
            org_city_lower = (org["city"] or "").lower().strip()

            # Partial name match with exact city match
            if (
                target_name_lower in org_name_lower
                and org_city_lower == target_city_lower
            ):
                target = org
                break

    if not target:
        return {
            "error": f"Target company '{target_company_name}' in '{target_city}' not found"
        }

    # Get candidates (exclude target)
    candidates = [o for o in orgs if o["id"] != target["id"]]

    results = []
    for cand in candidates:
        comp, breakdown = composite_similarity(target, cand)

        entry = {
            "company_name": cand["name"],
            "city": cand["city"],
            "revenue": cand["revenue_printed"] or "N/A",
            "number_of_employees": cand["estimated_employees"] or "N/A",
            # "employee_growth": "N/A",  # Not available in Growjo
            # "total_funding": "N/A",  # Not available in Growjo
            # "valuation": cand["market_cap"] or "N/A", # Not available in Growjo
            "similarity_score": round(comp, 3),
        }

        results.append(entry)

    ranked = sorted(results, key=lambda x: x["similarity_score"], reverse=True)[:top_n]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
        "target_company": {"name": target["name"], "city": target["city"]},
        "competitors": ranked,
    }
