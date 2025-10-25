# 🎯 Lead Scoring System - Dynamic AI-Powered Scoring

## 📋 Overview

This is a complete lead scoring system that dynamically scores leads using AI analysis, website scraping, and industry-specific criteria. **No hardcoded scores** - all scoring is calculated fresh every time.

## 🚀 Key Features

- **✅ Dynamic Scoring**: All scores calculated fresh, no hardcoded values
- **🤖 AI Analysis**: Keyword analysis, risk assessment, growth potential
- **🌐 Website Scraping**: Fresh content analysis every time (no caching)
- **🏭 Industry-Specific**: Different weights and criteria per industry
- **🔍 Fuzzy Matching**: Company name deduplication and matching
- **📊 Employee Parsing**: Handles ranges like "50-100" → 75 (average)
- **🎯 API Endpoints**: Complete REST API for search and recommend

## 🛠️ Setup Instructions

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/Caprae-Capital-Partners/LeadGenAI.git
cd LeadGenAI/backendLeadscoring

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup
```bash
# Create .env file
touch .env

# Add your Gemini API key (get from https://makersuite.google.com/app/apikey)
echo "GEMINI_API_KEY=your_actual_api_key_here" >> .env
```

### 3. Start Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🧪 Testing Commands

### Test API Endpoints

**Search Endpoint:**
```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "Technology", 
    "minEmployees": 0, 
    "maxEmployees": 1000, 
    "minRevenue": 0, 
    "maxRevenue": 100000000, 
    "targetRevenue": 25000000, 
    "targetEmployees": 50, 
    "keywords": "AI, automation, software"
  }' | python -m json.tool
```

**Recommend Endpoint:**
```bash
curl -X POST "http://localhost:8000/api/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "Technology", 
    "min_employees": 0, 
    "max_employees": 1000, 
    "min_revenue": 0, 
    "max_revenue": 100000000, 
    "target_revenue": 25000000, 
    "target_employees": 50, 
    "keywords": "AI, automation, software"
  }' | python -m json.tool
```

**Analytics Endpoint:**
```bash
curl "http://localhost:8000/api/analytics" | python -m json.tool
```

### Test Direct Script
```bash
python test_scoring_direct.py
```

### Test Website Scraping
```bash
python test_customguide_scraping.py
```

## 🎯 Employee Parsing Examples

The system handles various employee count formats:

| **Input** | **Result** | **Logic** |
|-----------|------------|-----------|
| `"50-100"` | `75` | Average of range |
| `"25 to 50"` | `37` | Average of range |
| `"50+"` | `62` | 125% of base |
| `"<50"` | `30` | 60% of upper bound |
| `">50"` | `75` | 150% of lower bound |
| `"fifty"` | `50` | Word recognition |
| `"1,000"` | `1000` | Comma removal |

## 🏭 Industry-Specific Scoring

### Supported Industries:
- **Technology**: Higher weight on keywords and growth
- **Healthcare**: Balanced scoring with compliance focus
- **Education**: Learning platform emphasis
- **Manufacturing**: Revenue and employee focus
- **Construction**: Project-based scoring

### Scoring Components:
- **Revenue (30%)**: Range-based scoring with industry thresholds
- **Employees (25%)**: Team size optimization
- **Keywords (20%)**: AI-powered relevance analysis
- **Contact Quality (10%)**: Email/website validation
- **Growth Potential (15%)**: AI growth indicators

## 🔧 Troubleshooting

### Port Already in Use
```bash
lsof -ti:8000 | xargs kill -9  # On Windows: netstat -ano | findstr :8000
```

### Module Errors
```bash
# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
```

### API Key Issues
- Get a valid Gemini API key from https://makersuite.google.com/app/apikey
- Ensure the key is added to `.env` file
- Check API quota limits

## 📊 Expected Output

```json
{
  "results": [
    {
      "id": "1",
      "name": "TechCorp Solutions",
      "score": 85.5,
      "explanation": "Revenue: $25,000,000 (Score: 28/30) | Employees: 75 (Score: 22/25) | Keywords: 95/100 (Excellent match) | Growth: 75/100 (High potential) | 🎯 Strong Investment"
    }
  ]
}
```

## 🎯 Key Improvements Made

1. **✅ No Hardcoded Scores**: All scores calculated dynamically
2. **✅ Fresh Website Scraping**: No caching, always fresh content
3. **✅ AI Analysis**: Keyword, risk, and growth assessment
4. **✅ Employee Range Handling**: "50-100" → 75 (average)
5. **✅ Industry Filtering**: Hard filters by industry
6. **✅ Fuzzy Matching**: Company name deduplication
7. **✅ Complete API**: Search, recommend, and analytics endpoints

## 🔗 Files Structure

```
backendLeadscoring/
├── app/
│   ├── api/
│   │   └── search.py          # API endpoints
│   ├── models/
│   │   └── search.py          # Pydantic models
│   ├── services/
│   │   ├── ml_service.py      # Main scoring logic
│   │   ├── llm_utils.py       # AI integration
│   │   └── enhanced_scraping_service.py  # Website scraping
│   ├── data.py                # Mock lead data
│   └── main.py                # FastAPI app
├── requirements.txt           # Dependencies
├── test_scoring_direct.py     # Direct testing script
└── test_customguide_scraping.py  # Website scraping test
```

## 🚀 Ready for Production

This system is ready to be integrated into production by:
1. Replacing mock data with real database queries
2. Adding authentication and authorization
3. Connecting to real MongoDB/PostgreSQL
4. Adding rate limiting and monitoring

**The core scoring logic is production-ready and fully tested!** 🎯 