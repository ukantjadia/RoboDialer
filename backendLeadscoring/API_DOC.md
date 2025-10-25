# 🎯 Lead Scoring API Documentation

## Overview

This API provides **dynamic, AI-powered lead scoring** for companies.  
It analyzes company data and user-defined preferences to return a detailed scoring breakdown, including:

- Growth potential  
- Risk assessment  
- Keyword relevance  
- Investment recommendations  

## 🔗 Endpoint

**POST** `/ai-score/score_leads`

## 📄 Description

Scores a batch of companies based on user preferences and returns detailed AI-powered analysis for each company.

## 📨 Request Body

**Content-Type:** `application/json`

```json
{
  "preferences": {
    // User-defined scoring preferences (industry, target revenue, etc.)
  },
  "companies": [
    {
      // Company data (name, website, revenue, employees, etc.)
    }
    // ...more companies
  ]
}
```

## Example Request

```json
{
  "preferences": {
    "industry": "Technology",
    "target_revenue": 25000000,
    "target_employees": 50,
    "keywords": "AI, automation, software"
  },
  "companies": [
    {
      "name": "TechCorp Solutions",
      "website": "https://techcorp.com",
      "revenue": 25000000,
      "employees": "50-100"
    }
  ]
}
```

## Successful Response

**Status** `200 OK`

```json
{
  "results": [
    {
      "company": "TechCorp Solutions",
      "analysis": {
        "total_score": 85.5,
        "investment_recommendation": "Strong Investment",
        "growth_potential": {
          "score": 75.0,
          "explanation": [
            "High year-over-year growth",
            "Expanding into new markets"
          ]
        },
        "risk": {
          "score": 15.0,
          "explanation": [
            "Low debt ratio",
            "Stable management team"
          ]
        },
        "keywords": {
          "score": 95.0,
          "explanation": [
            "Excellent match for: AI, automation, software"
          ]
        },
        "strengths": [
          "Strong revenue growth",
          "Relevant technology stack"
        ],
        "concerns": [
          "Limited international presence"
        ]
      }
    }
    // ...more companies
  ]
}
```

## Field Descriptions

| Field                                  | Description                                               |
|----------------------------------------|-----------------------------------------------------------|
| `company`                              | Name of the company                                       |
| `analysis.total_score`                 | Overall lead score (int)                                |
| `analysis.investment_recommendation`  | AI-generated recommendation string                        |
| `analysis.growth_potential.score`      | Growth score (int)                                      |
| `analysis.growth_potential.explanation`| List of reasons supporting the growth score               |
| `analysis.risk.score`                  | Risk score (int)                                        |
| `analysis.risk.explanation`            | List of risk-related explanations                         |
| `analysis.keywords.score`              | Keyword relevance score (int)                           |
| `analysis.keywords.explanation`        | List of matched keywords and relevance context            |
| `analysis.strengths`                   | List of company strengths                                 |
| `analysis.concerns`                    | List of company concerns or red flags                     |

## Error Responses

| Status Code               | Description                                  |
|---------------------------|----------------------------------------------|
| `400 Bad Request`         | No companies provided in request body        |
| `500 Internal Server Error` | Failed to return AI score                   |

## Notes

- Employee counts can be provided as ranges (e.g., `"50-100"`).
- The API expects all company data and preferences to be included in the request body.
- Current implementation takes ~20 seconds for returning score for one lead. Working on improving the speed.
