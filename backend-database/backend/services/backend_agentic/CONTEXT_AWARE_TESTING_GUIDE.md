# Context-Aware Routing Testing Guide

## 🎯 Overview

This document provides comprehensive test cases for the context-aware routing system. Each test case includes the exact payloads to send and the expected responses based on the CSV data.

**Base URL**: `http://localhost:8000/api/query`

**Important**: Always include `"use_context": true` to enable context-aware processing.

---

## 📋 Test Case Categories

### 🏢 Education Companies
### 🏗️ Construction Companies  
### 💻 Software Companies
### 🔄 Multi-Turn Conversations
### 🧪 Edge Cases

---

## 🏢 Education Companies

### Test Case 1: Lumious (Learning Solutions)

**Company Data**: Revenue: $10M, Employees: 42, Location: Erie, PA, Founded: 1992

#### Step 1: Establish Context
```json
{
  "query": "Tell me about Lumious",
  "user_id": "edu_test_1",
  "session_id": "lumious_session",
  "use_context": true
}
```

**Expected Response**: Detailed company information about Lumious learning solutions.

#### Step 2: Revenue Query
```json
{
  "query": "What's their revenue?",
  "user_id": "edu_test_1", 
  "session_id": "lumious_session",
  "use_context": true
}
```

**Expected Response**: `"Their revenue is $10M."`

#### Step 3: Employee Count
```json
{
  "query": "How many employees do they have?",
  "user_id": "edu_test_1",
  "session_id": "lumious_session", 
  "use_context": true
}
```

**Expected Response**: `"They have 42 employees."`

#### Step 4: Location Query
```json
{
  "query": "Where are they located?",
  "user_id": "edu_test_1",
  "session_id": "lumious_session",
  "use_context": true
}
```

**Expected Response**: `"They are located in Erie, Pennsylvania."`

---

### Test Case 2: SafetySkills (E-Learning)

**Company Data**: Revenue: $15M, Employees: 31, Location: Oklahoma City, OK, Founded: 1993

#### Step 1: Establish Context
```json
{
  "query": "I want to learn about SafetySkills",
  "user_id": "edu_test_2",
  "session_id": "safetyskills_session",
  "use_context": true
}
```

#### Step 2: Revenue Query
```json
{
  "query": "What is their revenue?",
  "user_id": "edu_test_2",
  "session_id": "safetyskills_session",
  "use_context": true
}
```

**Expected Response**: `"Their revenue is $15M."`

#### Step 3: Founding Year
```json
{
  "query": "When were they founded?",
  "user_id": "edu_test_2",
  "session_id": "safetyskills_session",
  "use_context": true
}
```

**Expected Response**: `"They were founded in 1993."`

---

### Test Case 3: Digital Marketer (High Revenue)

**Company Data**: Revenue: $17.8M, Employees: 320, Location: Austin, TX, Founded: 2001

#### Step 1: Establish Context
```json
{
  "query": "What do you know about Digital Marketer?",
  "user_id": "edu_test_3",
  "session_id": "digitalmarketer_session",
  "use_context": true
}
```

#### Step 2: Employee Count
```json
{
  "query": "How many employees do they have?",
  "user_id": "edu_test_3",
  "session_id": "digitalmarketer_session",
  "use_context": true
}
```

**Expected Response**: `"They have 320 employees."`

#### Step 3: Revenue Query
```json
{
  "query": "What's their revenue?",
  "user_id": "edu_test_3",
  "session_id": "digitalmarketer_session",
  "use_context": true
}
```

**Expected Response**: `"Their revenue is $17.8M."`

---

## 🏗️ Construction Companies

### Test Case 4: Ed Bell Construction (Large Construction)

**Company Data**: Revenue: $22.3M, Employees: 80, Location: Dallas, TX, Founded: 1963

#### Step 1: Establish Context
```json
{
  "query": "Tell me about Ed Bell Construction Company",
  "user_id": "const_test_1",
  "session_id": "edbell_session",
  "use_context": true
}
```

#### Step 2: Revenue Query
```json
{
  "query": "What's their revenue?",
  "user_id": "const_test_1",
  "session_id": "edbell_session",
  "use_context": true
}
```

**Expected Response**: `"Their revenue is $22.3M."`

#### Step 3: Industry Confirmation
```json
{
  "query": "What industry are they in?",
  "user_id": "const_test_1",
  "session_id": "edbell_session",
  "use_context": true
}
```

**Expected Response**: `"They are in the Construction industry."`

---

### Test Case 5: Clear Companies (Mid-Size Construction)

**Company Data**: Revenue: $19.6M, Employees: 31, Location: Cypress, TX, Founded: 1996

#### Step 1: Establish Context
```json
{
  "query": "I'm researching Clear companies",
  "user_id": "const_test_2",
  "session_id": "clear_session",
  "use_context": true
}
```

#### Step 2: Location Query
```json
{
  "query": "Where are they located?",
  "user_id": "const_test_2",
  "session_id": "clear_session",
  "use_context": true
}
```

**Expected Response**: `"They are located in Cypress, Texas."`

#### Step 3: Employee Count
```json
{
  "query": "How many employees?",
  "user_id": "const_test_2",
  "session_id": "clear_session",
  "use_context": true
}
```

**Expected Response**: `"They have 31 employees."`

---

## 💻 Software Companies

### Test Case 6: AIMDek Technologies (Healthcare Software)

**Company Data**: Revenue: $17.1M, Employees: 76, Location: Austin, TX, Founded: 2014

#### Step 1: Establish Context
```json
{
  "query": "Tell me about AIMDek Technologies Inc",
  "user_id": "soft_test_1",
  "session_id": "aimdek_session",
  "use_context": true
}
```

#### Step 2: Revenue Query
```json
{
  "query": "What is their revenue?",
  "user_id": "soft_test_1",
  "session_id": "aimdek_session",
  "use_context": true
}
```

**Expected Response**: `"Their revenue is $17.1M."`

#### Step 3: Founding Year
```json
{
  "query": "When were they founded?",
  "user_id": "soft_test_1",
  "session_id": "aimdek_session",
  "use_context": true
}
```

**Expected Response**: `"They were founded in 2014."`

---

### Test Case 7: DataCaliper (Data Management)

**Company Data**: Revenue: $12M, Employees: 84, Location: Apex, NC, Founded: 2008

#### Step 1: Establish Context
```json
{
  "query": "What do you know about DataCaliper?",
  "user_id": "soft_test_2",
  "session_id": "datacaliper_session",
  "use_context": true
}
```

#### Step 2: Employee Count
```json
{
  "query": "How many employees do they have?",
  "user_id": "soft_test_2",
  "session_id": "datacaliper_session",
  "use_context": true
}
```

**Expected Response**: `"They have 84 employees."`

#### Step 3: Location Query
```json
{
  "query": "Where are they based?",
  "user_id": "soft_test_2",
  "session_id": "datacaliper_session",
  "use_context": true
}
```

**Expected Response**: `"They are located in Apex, North Carolina."`

---

## 🔄 Multi-Turn Conversations

### Test Case 8: Comprehensive Company Analysis

**Target**: Canopy Partners (Healthcare IT)
**Company Data**: Revenue: $26.2M, Employees: 52, Location: Greensboro, NC, Founded: 2010

#### Step 1: Initial Query
```json
{
  "query": "I need information about Canopy Partners",
  "user_id": "multi_test_1",
  "session_id": "canopy_comprehensive",
  "use_context": true
}
```

#### Step 2: Revenue
```json
{
  "query": "What's their revenue?",
  "user_id": "multi_test_1",
  "session_id": "canopy_comprehensive",
  "use_context": true
}
```

**Expected Response**: `"Their revenue is $26.2M."`

#### Step 3: Team Size
```json
{
  "query": "How big is their team?",
  "user_id": "multi_test_1",
  "session_id": "canopy_comprehensive",
  "use_context": true
}
```

**Expected Response**: `"They have 52 employees."`

#### Step 4: Location
```json
{
  "query": "Where are they located?",
  "user_id": "multi_test_1",
  "session_id": "canopy_comprehensive",
  "use_context": true
}
```

**Expected Response**: `"They are located in Greensboro, North Carolina."`

#### Step 5: Age of Company
```json
{
  "query": "When were they established?",
  "user_id": "multi_test_1",
  "session_id": "canopy_comprehensive",
  "use_context": true
}
```

**Expected Response**: `"They were founded in 2010."`

---

## 🧪 Edge Cases

### Test Case 9: Company with Special Characters

**Target**: GLSS (GoLeanSixSigma.com)
**Company Data**: Revenue: $3.2M, Employees: 15, Location: Waianae, HI, Founded: 2012

#### Step 1: Establish Context
```json
{
  "query": "Tell me about GLSS",
  "user_id": "edge_test_1",
  "session_id": "glss_session",
  "use_context": true
}
```

#### Step 2: Revenue Query
```json
{
  "query": "What's their revenue?",
  "user_id": "edge_test_1",
  "session_id": "glss_session",
  "use_context": true
}
```

**Expected Response**: `"Their revenue is $3.2M."`

---

### Test Case 10: Ambiguous Reference

**Target**: Management Consulted
**Company Data**: Revenue: $1.6M, Employees: 30, Location: Redding, CA, Founded: 2008

#### Step 1: Establish Context
```json
{
  "query": "I'm interested in Management Consulted",
  "user_id": "edge_test_2",
  "session_id": "mgmt_consulted_session",
  "use_context": true
}
```

#### Step 2: Ambiguous Follow-up
```json
{
  "query": "What do they do?",
  "user_id": "edge_test_2",
  "session_id": "mgmt_consulted_session",
  "use_context": true
}
```

**Expected Response**: Information about management consulting services.

#### Step 3: Revenue
```json
{
  "query": "How much revenue?",
  "user_id": "edge_test_2",
  "session_id": "mgmt_consulted_session",
  "use_context": true
}
```

**Expected Response**: `"Their revenue is $1.6M."`

---

## 🚀 Quick Test Sequences

### Rapid Fire Test 1: Lumious
```bash
curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d '{"query": "Tell me about Lumious", "user_id": "rapid_1", "session_id": "lumious_rapid", "use_context": true}'

curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d '{"query": "What'\''s their revenue?", "user_id": "rapid_1", "session_id": "lumious_rapid", "use_context": true}'
```

### Rapid Fire Test 2: Digital Marketer
```bash
curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d '{"query": "What do you know about Digital Marketer?", "user_id": "rapid_2", "session_id": "dm_rapid", "use_context": true}'

curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d '{"query": "How many employees?", "user_id": "rapid_2", "session_id": "dm_rapid", "use_context": true}'
```

---

## ✅ Success Criteria

### Response Quality Indicators:
- **Concise answers**: Simple factual queries should return < 100 characters
- **Accurate data**: Responses must match CSV data exactly
- **Context awareness**: Follow-up questions work without mentioning company name
- **Status**: API returns `"status": "completed"`

### Failure Indicators:
- **Verbose responses**: > 500 characters for simple questions
- **Wrong data**: External knowledge instead of CSV data
- **Context failure**: `"status": "not_found"` for follow-up questions
- **Generic responses**: No specific company data

---

## 📊 Expected Response Patterns

### Revenue Queries:
- **Pattern**: `"Their revenue is $[amount]."`
- **Examples**: 
  - `"Their revenue is $10M."`
  - `"Their revenue is $17.8M."`

### Employee Queries:
- **Pattern**: `"They have [number] employees."`
- **Examples**:
  - `"They have 42 employees."`
  - `"They have 320 employees."`

### Location Queries:
- **Pattern**: `"They are located in [city], [state]."`
- **Examples**:
  - `"They are located in Austin, Texas."`
  - `"They are located in Erie, Pennsylvania."`

### Founding Queries:
- **Pattern**: `"They were founded in [year]."`
- **Examples**:
  - `"They were founded in 1992."`
  - `"They were founded in 2014."`

---

## 🔧 Troubleshooting

### If Context-Aware Routing Fails:
1. **Check `use_context` parameter**: Must be `true`
2. **Verify session consistency**: Same `session_id` and `user_id`
3. **Wait for first response**: Complete before sending follow-up
4. **Check server logs**: Look for entity extraction issues

### If Responses Are Verbose:
1. **Check prompt builder**: Ensure factual template is being used
2. **Verify CSV data**: Ensure tool results include correct data
3. **Check LLM path**: Should use prompt with tool results, not just context

### If Wrong Data Returned:
1. **Verify CSV lookup**: Check if company exists in CSV
2. **Check entity extraction**: Ensure correct company name is extracted
3. **Review tool execution**: Ensure fact_csv tool runs successfully

---

## 📈 Performance Expectations

- **First query (context establishment)**: 3-10 seconds
- **Follow-up queries (context-aware)**: 2-5 seconds
- **Success rate**: ~90% (some intermittent LLM issues expected)
- **Response size**: 50-200 characters for factual queries

---

*Last Updated: August 28, 2025*
*Version: 1.0*