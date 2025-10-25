# Prompt builder
import logging
from typing import Dict, Any, List, Optional
import json

# Import agentic logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentic_logging import get_agentic_logger

logger = get_agentic_logger('aggregator.prompt_builder')

class PromptBuilder:
    """
    Prompt builder for constructing LLM prompts with context
    """
    
    def __init__(self):
        self.templates = {
            "compare": self._get_compare_template(),
            "analyze": self._get_analyze_template(),
            "search": self._get_search_template(),
            "summarize": self._get_summarize_template()
        }
    
    async def build_prompt(self, query: str, context_results: List[Dict[str, Any]], 
                          intent: str = "search") -> str:
        """
        Build a prompt for the LLM based on query and context
        """
        try:
            logger.info(f"Building prompt for intent: {intent}")
            
            # Check if this is a simple factual query
            is_simple_factual = self._is_simple_factual_query(query)
            
            # Get appropriate template
            if is_simple_factual and intent == "analyze":
                # Use a more direct template for simple factual questions
                template = self._get_factual_template()
                logger.info("Using factual template for simple question")
            else:
                template = self.templates.get(intent, self.templates["search"])
            
            # Build context blocks
            context_blocks = self._build_context_blocks(context_results)
            
            # Format the prompt
            prompt = template.format(
                query=query,
                context_blocks="\n".join(context_blocks),
                context_count=len(context_blocks)
            )
            
            logger.info(f"Built prompt with {len(context_blocks)} context blocks")
            return prompt
            
        except Exception as e:
            logger.error(f"Error building prompt: {str(e)}")
            # Return fallback prompt
            return f"Query: {query}\n\nPlease provide a response based on the available information."
    
    def _is_simple_factual_query(self, query: str) -> bool:
        """
        Detect if this is a simple factual query that needs a direct answer
        """
        query_lower = query.lower()
        
        # Simple factual question patterns
        factual_patterns = [
            "what is their revenue",
            "what's their revenue", 
            "how much revenue",
            "what is the revenue",
            "revenue of",
            "how many employees",
            "what's their employee count",
            "where are they located",
            "what's their location",
            "when were they founded",
            "what year founded",
            "who is the ceo",
            "who founded",
            "what industry",
            "what do they do",
            "what's their business model"
        ]
        
        return any(pattern in query_lower for pattern in factual_patterns)
    
    def _get_factual_template(self) -> str:
        """
        Template for simple factual queries that need direct answers
        """
        return """You are a helpful assistant providing direct answers to factual questions about companies.

QUERY: {query}

CONTEXT INFORMATION:
{context_blocks}

INSTRUCTIONS:
1. **Provide a direct, concise answer first**
2. **Use ONLY the data from the provided context**
3. **Keep the response brief and to the point**
4. **If additional context is helpful, add it after the direct answer**

EXAMPLE RESPONSES:
- For "What's their revenue?": "Their revenue is $15.8M."
- For "How many employees?": "They have 66 employees."
- For "Where are they located?": "They are located in New York, NY."

IMPORTANT: Give the direct answer first, then any additional relevant context if needed. Use the exact data from the provided context."""
    
    def _build_context_blocks(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Build formatted context blocks from results
        """
        context_blocks = []
        
        for result in results:
            try:
                index = result.get("index", 0)
                source = result.get("source", "unknown")
                text = result.get("text", "")
                entity = result.get("entity", "unknown")
                
                block = f"[{index}] Source: {source}, Entity: {entity}\n{text}\n"
                context_blocks.append(block)
                
            except Exception as e:
                logger.error(f"Error building context block: {str(e)}")
                continue
        
        return context_blocks
    
    def _get_compare_template(self) -> str:
        """
        Template for comparison queries
        """
        return """You are an expert business analyst. Your task is to compare companies based on the provided context.

QUERY: {query}

CONTEXT INFORMATION:
{context_blocks}

INSTRUCTIONS:
1. Analyze the provided context carefully
2. Create a detailed comparison of the companies mentioned
3. Provide specific metrics and data points from the context
4. Give a clear verdict on which company has better potential
5. Support your conclusions with evidence from the context
6. Format your response as JSON with the following structure:
   {{
     "comparison_table": [
       {{
         "metric": "metric_name",
         "company_1": "value",
         "company_2": "value",
         "winner": "company_1 or company_2 or tie"
       }}
     ],
     "verdict": "Overall conclusion about which company is better",
     "reasons": ["reason1", "reason2", "reason3"],
     "confidence": {{
       "score": 0.85,
       "factors": ["factor1", "factor2"]
     }}
   }}

IMPORTANT: Only use information from the provided context. If information is missing, acknowledge it in your response."""

    def _get_analyze_template(self) -> str:
        """
        Template for analysis queries - Enhanced for comprehensive responses
        """
        return """You are an expert business analyst and researcher. Your task is to provide comprehensive, detailed analysis based on the provided company data.

QUERY: {query}

CONTEXT INFORMATION:
{context_blocks}

INSTRUCTIONS:
1. **For simple factual questions**: Provide a direct answer PLUS comprehensive context and additional insights
2. **For complex analysis questions**: Provide detailed, thorough analysis with insights, trends, and business intelligence
3. **Always use ALL available data from the provided context**
4. **Provide comprehensive responses that give maximum value to the user**

RESPONSE GUIDELINES:
- Start with the direct answer if it's a factual question
- Then provide comprehensive context, background, and additional relevant information
- Include business insights, industry context, and analytical observations
- Use specific data points, metrics, and figures from the context
- Provide a thorough, informative response that demonstrates deep understanding
- If multiple data sources are available, synthesize them into comprehensive insights

ENHANCED RESPONSE FORMAT:
- **Direct Answer** (if applicable): The specific answer to the question
- **Comprehensive Analysis**: Detailed breakdown of all relevant information
- **Business Context**: Industry positioning, competitive landscape insights
- **Key Metrics**: All relevant financial and operational data
- **Additional Insights**: Trends, implications, and analytical observations

IMPORTANT: Use ALL available information from the provided context to create the most comprehensive, valuable response possible. Don't just answer the question - provide business intelligence."""

    def _get_search_template(self) -> str:
        """
        Template for search queries - Enhanced for detailed responses
        """
        return """You are an expert business intelligence analyst. Your task is to provide comprehensive, detailed information about companies based on the available data.

QUERY: {query}

CONTEXT INFORMATION:
{context_blocks}

INSTRUCTIONS:
1. Provide a comprehensive, detailed response about the company/companies mentioned
2. Include ALL relevant information from the context in a conversational, informative manner
3. Structure your response to be thorough and insightful
4. Format your response as JSON with the following enhanced structure:
   {{
     "search_results": [
       {{
         "company_name": "company_name",
         "key_information": "comprehensive_detailed_information_including_all_relevant_data",
         "relevance_score": 0.85
       }}
     ],
     "summary": "Detailed, comprehensive summary that covers all important aspects found in the context",
     "total_results": {context_count},
     "confidence": {{
       "score": 0.85,
       "factors": ["factor1", "factor2", "factor3"]
     }}
   }}

RESPONSE GUIDELINES:
- Be thorough and comprehensive in your descriptions
- Include specific details like revenue figures, employee counts, industry information, business models, etc.
- Provide context and insights about the company's position in their industry
- If multiple data sources are available, synthesize them into a cohesive narrative
- Make the response informative and valuable for business research
- Include any financial metrics, growth indicators, or business intelligence available

IMPORTANT: Use ALL relevant information from the provided context to create a detailed, comprehensive response."""

    def _get_summarize_template(self) -> str:
        """
        Template for summarization queries
        """
        return """You are an expert summarizer. Your task is to create a comprehensive summary of the provided company information.

QUERY: {query}

CONTEXT INFORMATION:
{context_blocks}

INSTRUCTIONS:
1. Create a comprehensive summary of the provided context
2. Highlight key points and important information about companies
3. Maintain accuracy and completeness
4. Format your response as JSON with the following structure:
   {{
     "summary": "Comprehensive summary of the information",
     "key_points": ["point1", "point2", "point3"],
     "important_metrics": ["metric1", "metric2"],
     "conclusions": ["conclusion1", "conclusion2"],
     "confidence": {{
       "score": 0.85,
       "factors": ["factor1", "factor2"]
     }}
   }}

IMPORTANT: Only use information from the provided context."""
    
    def estimate_tokens(self, prompt: str) -> int:
        """
        Estimate the number of tokens in a prompt
        """
        # Rough estimation: 1 token ≈ 4 characters
        return len(prompt) // 4
    
    def truncate_prompt(self, prompt: str, max_tokens: int = 8000) -> str:
        """
        Truncate prompt if it exceeds token limit
        """
        estimated_tokens = self.estimate_tokens(prompt)
        
        if estimated_tokens <= max_tokens:
            return prompt
        
        # Simple truncation (in practice, you'd want more sophisticated tokenization)
        max_chars = max_tokens * 4
        truncated = prompt[:max_chars]
        
        logger.warning(f"Prompt truncated from {estimated_tokens} to {max_tokens} tokens")
        return truncated + "\n\n[Prompt truncated due to length]" 