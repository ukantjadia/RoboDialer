# Verifier (Optional, Local Checks)
import logging
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class Verifier:
    """
    Verifier for performing local consistency checks on LLM responses
    """
    
    def __init__(self):
        self.verification_rules = {
            "number_consistency": self._check_number_consistency,
            "source_citation": self._check_source_citation,
            "format_compliance": self._check_format_compliance,
            "completeness": self._check_completeness
        }
    
    async def verify_response(self, response: str, context_results: List[Dict[str, Any]], 
                            query: str) -> Dict[str, Any]:
        """
        Perform comprehensive verification of LLM response
        """
        try:
            logger.info("Starting response verification")
            
            verification_results = {
                "overall_score": 0.0,
                "checks": {},
                "warnings": [],
                "errors": [],
                "confidence_adjustment": 0.0
            }
            
            # Run all verification checks
            for check_name, check_func in self.verification_rules.items():
                try:
                    result = await check_func(response, context_results, query)
                    verification_results["checks"][check_name] = result
                except Exception as e:
                    logger.error(f"Error in verification check {check_name}: {str(e)}")
                    verification_results["checks"][check_name] = {
                        "passed": False,
                        "score": 0.0,
                        "error": str(e)
                    }
            
            # Calculate overall score
            scores = [check.get("score", 0.0) for check in verification_results["checks"].values()]
            if scores:
                verification_results["overall_score"] = sum(scores) / len(scores)
            
            # Determine confidence adjustment
            verification_results["confidence_adjustment"] = self._calculate_confidence_adjustment(
                verification_results
            )
            
            logger.info(f"Verification complete. Overall score: {verification_results['overall_score']:.2f}")
            return verification_results
            
        except Exception as e:
            logger.error(f"Error in verification: {str(e)}")
            return {
                "overall_score": 0.0,
                "checks": {},
                "warnings": ["Verification failed"],
                "errors": [str(e)],
                "confidence_adjustment": -0.2
            }
    
    async def _check_number_consistency(self, response: str, context_results: List[Dict[str, Any]], 
                                      query: str) -> Dict[str, Any]:
        """
        Check if numbers in response match numbers in context
        """
        try:
            # Extract numbers from response
            response_numbers = self._extract_numbers(response)
            
            # Extract numbers from context
            context_numbers = []
            for result in context_results:
                context_numbers.extend(self._extract_numbers(result.get("text", "")))
            
            # Check for consistency
            inconsistencies = []
            for resp_num in response_numbers:
                if resp_num not in context_numbers:
                    # Allow for small formatting differences
                    if not any(self._numbers_close(resp_num, ctx_num) for ctx_num in context_numbers):
                        inconsistencies.append(resp_num)
            
            score = 1.0 - (len(inconsistencies) / max(len(response_numbers), 1))
            
            return {
                "passed": len(inconsistencies) == 0,
                "score": score,
                "inconsistencies": inconsistencies,
                "response_numbers": response_numbers,
                "context_numbers": context_numbers
            }
            
        except Exception as e:
            return {
                "passed": False,
                "score": 0.0,
                "error": str(e)
            }
    
    async def _check_source_citation(self, response: str, context_results: List[Dict[str, Any]], 
                                   query: str) -> Dict[str, Any]:
        """
        Check if response properly cites sources from context
        """
        try:
            # Extract source references from response
            source_patterns = [
                r"\[(\d+)\]",  # [1], [2], etc.
                r"source\s+(\d+)",  # source 1, source 2, etc.
                r"context\s+(\d+)"  # context 1, context 2, etc.
            ]
            
            cited_sources = set()
            for pattern in source_patterns:
                matches = re.findall(pattern, response, re.IGNORECASE)
                cited_sources.update(matches)
            
            # Check if cited sources exist in context
            available_sources = set(str(i) for i in range(len(context_results)))
            valid_citations = cited_sources.intersection(available_sources)
            invalid_citations = cited_sources - available_sources
            
            # Calculate score based on citation quality
            if len(context_results) == 0:
                score = 1.0  # No context to cite
            else:
                citation_ratio = len(valid_citations) / len(context_results)
                score = min(citation_ratio, 1.0)
            
            return {
                "passed": len(invalid_citations) == 0,
                "score": score,
                "cited_sources": list(cited_sources),
                "valid_citations": list(valid_citations),
                "invalid_citations": list(invalid_citations),
                "total_context_sources": len(context_results)
            }
            
        except Exception as e:
            return {
                "passed": False,
                "score": 0.0,
                "error": str(e)
            }
    
    async def _check_format_compliance(self, response: str, context_results: List[Dict[str, Any]], 
                                     query: str) -> Dict[str, Any]:
        """
        Check if response follows expected JSON format
        """
        try:
            # Try to parse as JSON
            try:
                parsed = json.loads(response)
                is_valid_json = True
            except json.JSONDecodeError:
                is_valid_json = False
                parsed = None
            
            # Check for required fields based on query intent
            required_fields = self._get_required_fields(query)
            missing_fields = []
            
            if parsed and required_fields:
                for field in required_fields:
                    if field not in parsed:
                        missing_fields.append(field)
            
            # Calculate score
            json_score = 1.0 if is_valid_json else 0.0
            field_score = 1.0 - (len(missing_fields) / max(len(required_fields), 1))
            overall_score = (json_score + field_score) / 2
            
            return {
                "passed": is_valid_json and len(missing_fields) == 0,
                "score": overall_score,
                "is_valid_json": is_valid_json,
                "missing_fields": missing_fields,
                "required_fields": required_fields
            }
            
        except Exception as e:
            return {
                "passed": False,
                "score": 0.0,
                "error": str(e)
            }
    
    async def _check_completeness(self, response: str, context_results: List[Dict[str, Any]], 
                                query: str) -> Dict[str, Any]:
        """
        Check if response addresses all aspects of the query
        """
        try:
            # Extract key terms from query
            query_terms = self._extract_key_terms(query)
            
            # Check if response contains these terms or related concepts
            response_lower = response.lower()
            addressed_terms = []
            missing_terms = []
            
            for term in query_terms:
                if term.lower() in response_lower or self._has_related_concept(term, response_lower):
                    addressed_terms.append(term)
                else:
                    missing_terms.append(term)
            
            # Calculate completeness score
            if len(query_terms) == 0:
                score = 1.0
            else:
                score = len(addressed_terms) / len(query_terms)
            
            return {
                "passed": len(missing_terms) == 0,
                "score": score,
                "addressed_terms": addressed_terms,
                "missing_terms": missing_terms,
                "total_query_terms": len(query_terms)
            }
            
        except Exception as e:
            return {
                "passed": False,
                "score": 0.0,
                "error": str(e)
            }
    
    def _extract_numbers(self, text: str) -> List[str]:
        """
        Extract numbers from text
        """
        # Pattern for various number formats
        number_pattern = r'\$?[\d,]+(?:\.\d+)?%?'
        return re.findall(number_pattern, text)
    
    def _numbers_close(self, num1: str, num2: str) -> bool:
        """
        Check if two number strings are close (accounting for formatting)
        """
        try:
            # Clean and convert to float
            def clean_number(num_str):
                return float(num_str.replace('$', '').replace(',', '').replace('%', ''))
            
            n1 = clean_number(num1)
            n2 = clean_number(num2)
            
            # Allow 1% difference
            return abs(n1 - n2) / max(abs(n1), abs(n2)) < 0.01
            
        except:
            return False
    
    def _get_required_fields(self, query: str) -> List[str]:
        """
        Get required fields based on query intent
        """
        query_lower = query.lower()
        
        if "compare" in query_lower:
            return ["comparison_table", "verdict", "reasons", "confidence"]
        elif "analyze" in query_lower:
            return ["analysis", "key_insights", "recommendations", "confidence"]
        elif "search" in query_lower:
            return ["search_results", "summary", "confidence"]
        else:
            return ["confidence"]  # Always require confidence
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """
        Extract key terms from query
        """
        # Simple extraction - in practice, you might use NLP
        terms = []
        query_lower = query.lower()
        
        # Look for common business terms
        business_terms = ["revenue", "growth", "profit", "employees", "market", "competition"]
        for term in business_terms:
            if term in query_lower:
                terms.append(term)
        
        # Look for entity references
        entity_matches = re.findall(r'lead_\d+', query_lower)
        terms.extend(entity_matches)
        
        return terms
    
    def _has_related_concept(self, term: str, response: str) -> bool:
        """
        Check if response contains concepts related to the term
        """
        # Simple synonym mapping
        synonyms = {
            "revenue": ["sales", "income", "earnings"],
            "growth": ["increase", "expansion", "development"],
            "profit": ["margin", "earnings", "income"],
            "employees": ["staff", "team", "workforce"],
            "market": ["industry", "sector", "segment"],
            "competition": ["competitive", "rival", "opponent"]
        }
        
        related_terms = synonyms.get(term.lower(), [])
        return any(related in response for related in related_terms)
    
    def _calculate_confidence_adjustment(self, verification_results: Dict[str, Any]) -> float:
        """
        Calculate confidence adjustment based on verification results
        """
        overall_score = verification_results.get("overall_score", 0.0)
        
        # Adjust confidence based on verification score
        if overall_score >= 0.9:
            return 0.1  # Boost confidence
        elif overall_score >= 0.7:
            return 0.0  # No adjustment
        elif overall_score >= 0.5:
            return -0.1  # Slight reduction
        else:
            return -0.3  # Significant reduction

# Standalone execution
async def main():
    """
    Standalone execution for testing
    """
    verifier = Verifier()
    
    # Test verification
    response = '{"comparison_table": [], "verdict": "Test", "confidence": {"score": 0.8}}'
    context_results = [{"text": "Revenue: $500,000", "source": "fact_csv"}]
    query = "Compare lead_2 and lead_3"
    
    result = await verifier.verify_response(response, context_results, query)
    print(f"Verification result: {result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 