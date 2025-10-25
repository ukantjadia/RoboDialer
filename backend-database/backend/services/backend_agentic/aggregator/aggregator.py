# Aggregator + prompt builder
import logging
from typing import Dict, Any, List, Optional
import re
from datetime import datetime
import hashlib
import json

# Import agentic logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentic_logging import get_agentic_logger

logger = get_agentic_logger('aggregator')

class Aggregator:
    """
    Enhanced aggregator for merging, deduplicating, and ranking tool results
    with support for Haystack RAG system results and improved context optimization
    """
    
    def __init__(self, max_tokens: int = 4000, rag_context_ratio: float = 0.6):
        self.max_tokens = max_tokens
        self.rag_context_ratio = rag_context_ratio  # Portion of tokens reserved for RAG context
        self.deduplication_cache = set()
        self.content_hashes = set()  # For improved deduplication
    
    async def aggregate_results(self, tool_results: List[Dict[str, Any]], plan: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Enhanced aggregation and processing of results from multiple tools including Haystack RAG
        """
        try:
            logger.info(f"Aggregating {len(tool_results)} tool results")
            
            # Step 1: Normalize results with enhanced Haystack support
            normalized_results = await self._normalize_results(tool_results)
            
            # Step 2: Enhanced deduplication with content similarity
            deduplicated_results = await self._enhanced_deduplicate_results(normalized_results)
            
            # Step 3: Enhanced ranking with Haystack relevance scores
            ranked_results = await self._enhanced_rank_results(deduplicated_results, plan)
            
            # Step 4: Intelligent token budget management
            trimmed_results = await self._intelligent_trim_to_budget(ranked_results)
            
            # Step 5: Optimize context for LLM prompt construction
            optimized_results = await self._optimize_context_for_llm(trimmed_results)
            
            logger.info(f"Enhanced aggregation complete: {len(optimized_results)} final results")
            return optimized_results
            
        except Exception as e:
            logger.error(f"Error in enhanced aggregation: {str(e)}")
            return []
    
    async def _normalize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize results to common format
        """
        normalized = []
        
        for result in results:
            try:
                if result.get("tool") == "fact_db":
                    normalized.extend(self._normalize_db_results(result))
                elif result.get("tool") == "scraper":
                    normalized.extend(self._normalize_scraper_results(result))
                elif result.get("tool") == "vector_query":
                    normalized.extend(self._normalize_vector_results(result))
                elif result.get("tool") == "haystack_rag":
                    normalized.extend(self._normalize_haystack_rag_results(result))
                elif result.get("tool") == "faiss_rag":
                    normalized.extend(self._normalize_faiss_rag_results(result))
                else:
                    # Generic normalization
                    normalized.append({
                        "index": len(normalized),
                        "source": result.get("tool", "unknown"),
                        "text": str(result.get("data", "")),
                        "entity": result.get("entity", "unknown"),
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except Exception as e:
                logger.error(f"Error normalizing result: {str(e)}")
                continue
        
        return normalized
    
    def _normalize_db_results(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize database results
        """
        normalized = []
        data = result.get("data", {})
        
        # Handle both old format (entities) and new format (results)
        entities = data.get("entities", [])
        results = data.get("results", [])
        
        # Process entities (old format)
        for entity in entities:
            normalized.append({
                "index": len(normalized),
                "source": "fact_csv",
                "text": f"Entity {entity}: {data}",
                "entity": entity,
                "timestamp": datetime.now().isoformat(),
                "type": "structured_data"
            })
        
        # Process results (new format from enhanced fact retriever)
        for company_result in results:
            company_name = company_result.get("entity", company_result.get("Company Name", "Unknown"))
            # Handle industry field with trailing space issue
            industry = company_result.get("Industry ", company_result.get("Industry", "Unknown"))
            if industry == "Unknown":
                # Try alternative field names
                industry = company_result.get("industry", "Unknown")
            revenue = company_result.get("Revenue", "Unknown")
            employees = company_result.get("Employees", "Unknown")
            website = company_result.get("Website", "")
            
            # Create comprehensive text representation
            company_text = f"Company: {company_name}, Industry: {industry}, Revenue: {revenue}, Employees: {employees}"
            if website:
                company_text += f", Website: {website}"
            
            normalized.append({
                "index": len(normalized),
                "source": "fact_csv",
                "text": company_text,
                "entity": company_name,
                "timestamp": datetime.now().isoformat(),
                "type": "structured_data",
                "metadata": {
                    "company_name": company_name,
                    "industry": industry,
                    "revenue": revenue,
                    "employees": employees,
                    "website": website,
                    "operation": data.get("operation", "unknown"),
                    "total_results": data.get("total_results", 0)
                }
            })
        
        return normalized
    
    def _normalize_scraper_results(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize enhanced scraper results with SmartScraperGraph support
        """
        normalized = []
        data = result.get("data", {})
        
        # Handle enhanced scraper results
        scraped_content = data.get("scraped_content", "")
        urls_processed = data.get("urls_processed", [])
        financial_data = data.get("financial_data", {})
        business_metrics = data.get("business_metrics", {})
        methods_used = data.get("scraping_methods_used", [])
        query_intent = data.get("query_intent", "general")
        
        # Add main scraped content
        if scraped_content:
            normalized.append({
                "index": len(normalized),
                "source": "scraper",
                "text": scraped_content,
                "entity": "web_scraping",
                "timestamp": datetime.now().isoformat(),
                "type": "web_content",
                "metadata": {
                    "urls_processed": urls_processed,
                    "scraping_methods": methods_used,
                    "query_intent": query_intent,
                    "successful_scrapes": data.get("successful_scrapes", 0),
                    "total_urls_attempted": data.get("total_urls_attempted", 0)
                }
            })
        
        # Add financial data as separate normalized results
        for key, value in financial_data.items():
            if value and str(value).strip():
                normalized.append({
                    "index": len(normalized),
                    "source": "scraper_financial",
                    "text": f"Financial metric {key}: {value}",
                    "entity": "financial_data",
                    "timestamp": datetime.now().isoformat(),
                    "type": "financial_data",
                    "metadata": {
                        "metric_type": key,
                        "value": value,
                        "source_urls": urls_processed
                    }
                })
        
        # Add business metrics as separate normalized results
        for key, value in business_metrics.items():
            if value and str(value).strip():
                normalized.append({
                    "index": len(normalized),
                    "source": "scraper_metrics",
                    "text": f"Business metric {key}: {value}",
                    "entity": "business_metrics",
                    "timestamp": datetime.now().isoformat(),
                    "type": "business_metrics",
                    "metadata": {
                        "metric_type": key,
                        "value": value,
                        "source_urls": urls_processed
                    }
                })
        
        return normalized
    
    def _normalize_vector_results(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize vector query results
        """
        normalized = []
        data = result.get("data", {})
        params = data.get("params", {})
        
        normalized.append({
            "index": len(normalized),
            "source": "vector_query",
            "text": f"Vector search results: {data}",
            "entity": "vector_search",
            "timestamp": datetime.now().isoformat(),
            "type": "semantic_search"
        })
        
        return normalized
    
    def _normalize_haystack_rag_results(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize Haystack RAG results with enhanced metadata handling
        """
        normalized = []
        data = result.get("data", {})
        
        # Handle search results
        if "results" in data:
            search_results = data["results"]
            for i, search_result in enumerate(search_results):
                normalized.append({
                    "index": len(normalized),
                    "source": "haystack_rag",
                    "text": search_result.get("content", ""),
                    "entity": search_result.get("metadata", {}).get("company_name", f"document_{i}"),
                    "timestamp": datetime.now().isoformat(),
                    "type": "semantic_search",
                    "relevance_score": search_result.get("score", 0.0),
                    "metadata": search_result.get("metadata", {}),
                    "document_type": search_result.get("metadata", {}).get("document_type", "unknown")
                })
        
        # Handle RAG response
        elif "context_documents" in data:
            context_docs = data["context_documents"]
            for i, doc in enumerate(context_docs):
                normalized.append({
                    "index": len(normalized),
                    "source": "haystack_rag",
                    "text": doc.get("content", ""),
                    "entity": doc.get("metadata", {}).get("company_name", f"rag_doc_{i}"),
                    "timestamp": datetime.now().isoformat(),
                    "type": "rag_context",
                    "relevance_score": doc.get("score", 0.0),
                    "metadata": doc.get("metadata", {}),
                    "document_type": doc.get("metadata", {}).get("document_type", "unknown")
                })
            
            # Add the RAG answer if available
            if data.get("answer"):
                normalized.append({
                    "index": len(normalized),
                    "source": "haystack_rag",
                    "text": data["answer"],
                    "entity": "rag_answer",
                    "timestamp": datetime.now().isoformat(),
                    "type": "rag_answer",
                    "relevance_score": 1.0,  # Highest relevance for generated answer
                    "metadata": {"generated": True, "question": data.get("question", "")},
                    "document_type": "generated_answer"
                })
        
        # Handle similar companies results
        elif "similar_companies" in data:
            companies = data["similar_companies"]
            for company in companies:
                normalized.append({
                    "index": len(normalized),
                    "source": "haystack_rag",
                    "text": f"Company: {company.get('company_name', 'Unknown')} - {company.get('description', '')}",
                    "entity": company.get("company_name", "unknown_company"),
                    "timestamp": datetime.now().isoformat(),
                    "type": "similar_company",
                    "relevance_score": company.get("similarity_score", 0.0),
                    "metadata": company.get("metadata", {}),
                    "document_type": "company_profile"
                })
        
        return normalized
    
    def _normalize_faiss_rag_results(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Normalize FAISS RAG results for integration with other tool results
        """
        normalized = []
        data = result.get("data", {})
        
        # Handle successful RAG result
        if "rag_answer" in data and result.get("status") == "success":
            rag_answer = data["rag_answer"]
            query = data.get("query", "unknown")
            
            normalized.append({
                "index": len(normalized),
                "source": "faiss_rag",
                "text": rag_answer,
                "entity": "rag_answer",
                "timestamp": datetime.now().isoformat(),
                "type": "rag_answer",
                "relevance_score": 1.0,  # Highest relevance for RAG generated answer
                "metadata": {
                    "generated": True,
                    "question": query,
                    "rag_type": "faiss"
                },
                "document_type": "generated_answer"
            })
            
            logger.info(f"Normalized FAISS RAG result: {rag_answer[:100]}...")
        
        # Handle RAG error
        elif "error" in data and result.get("status") == "error":
            error_msg = data["error"]
            query = data.get("query", "unknown")
            
            normalized.append({
                "index": len(normalized),
                "source": "faiss_rag",
                "text": f"RAG processing error: {error_msg}",
                "entity": "rag_error",
                "timestamp": datetime.now().isoformat(),
                "type": "rag_error",
                "relevance_score": 0.1,  # Low relevance for errors
                "metadata": {
                    "error": True,
                    "question": query,
                    "rag_type": "faiss"
                },
                "document_type": "error_message"
            })
            
            logger.warning(f"Normalized FAISS RAG error: {error_msg}")
        
        return normalized
    
    async def _enhanced_deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhanced deduplication with content similarity detection for Haystack documents
        """
        deduplicated = []
        seen_content_hashes = set()
        seen_entities = {}  # Track entities to merge similar content
        
        for result in results:
            text = result.get("text", "")
            entity = result.get("entity", "unknown")
            
            # Create content hash for exact duplicate detection
            content_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
            
            # Create semantic hash for similar content detection
            semantic_content = self._normalize_text_for_comparison(text)
            semantic_hash = hashlib.md5(semantic_content.encode('utf-8')).hexdigest()
            
            # Check for exact duplicates
            if content_hash in seen_content_hashes:
                logger.debug(f"Exact duplicate found: {text[:100]}...")
                continue
            
            # Check for similar content from same entity
            if entity in seen_entities:
                existing_semantic_hash = seen_entities[entity].get("semantic_hash")
                if existing_semantic_hash == semantic_hash:
                    # Merge with existing result, keeping higher relevance score
                    existing_result = seen_entities[entity]["result"]
                    current_score = result.get("relevance_score", 0.0)
                    existing_score = existing_result.get("relevance_score", 0.0)
                    
                    if current_score > existing_score:
                        # Replace with higher scoring result
                        for i, existing in enumerate(deduplicated):
                            if existing["entity"] == entity and existing.get("semantic_hash") == existing_semantic_hash:
                                deduplicated[i] = result
                                deduplicated[i]["semantic_hash"] = semantic_hash
                                seen_entities[entity] = {"result": result, "semantic_hash": semantic_hash}
                                break
                    
                    logger.debug(f"Similar content merged for entity {entity}")
                    continue
            
            # Add new unique result
            result["semantic_hash"] = semantic_hash
            seen_content_hashes.add(content_hash)
            seen_entities[entity] = {"result": result, "semantic_hash": semantic_hash}
            deduplicated.append(result)
        
        logger.info(f"Enhanced deduplication: {len(results)} -> {len(deduplicated)} results")
        return deduplicated
    
    def _normalize_text_for_comparison(self, text: str) -> str:
        """
        Normalize text for semantic comparison
        """
        # Remove extra whitespace, convert to lowercase, remove special characters
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized
    
    async def _enhanced_rank_results(self, results: List[Dict[str, Any]], plan: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Enhanced ranking algorithm incorporating Haystack relevance scores and query context
        """
        def calculate_enhanced_score(result: Dict[str, Any]) -> float:
            score = 0.0
            
            # Base score from source type with enhanced RAG support
            source_type = result.get("type", "unknown")
            if source_type == "rag_answer":
                score += 1.0  # Highest priority for RAG generated answers
            elif source_type == "structured_data":
                score += 0.8  # High confidence for structured data
            elif source_type == "rag_context":
                score += 0.85  # Very high confidence for RAG context
            elif source_type == "financial_data":
                score += 0.9  # Very high confidence for financial data from scraping
            elif source_type == "business_metrics":
                score += 0.85  # High confidence for business metrics from scraping
            elif source_type == "semantic_search":
                score += 0.7  # Good confidence for semantic search
            elif source_type == "similar_company":
                score += 0.75  # High confidence for similar companies
            elif source_type == "web_content":
                score += 0.6  # Medium confidence for web content
            elif source_type == "rag_error":
                score += 0.1  # Very low priority for RAG errors
            
            # Incorporate Haystack relevance scores
            relevance_score = result.get("relevance_score", 0.0)
            if relevance_score > 0:
                score += relevance_score * 0.3  # Weight relevance score
            
            # Query intent alignment (if plan is available)
            if plan:
                intent = plan.get("intent", "")
                entities = plan.get("entities", [])
                
                # Boost results that match query entities
                result_entity = result.get("entity", "").lower()
                for entity in entities:
                    if entity.lower() in result_entity:
                        score += 0.15
                
                # Boost results based on intent
                if intent == "search" and source_type in ["semantic_search", "rag_context"]:
                    score += 0.1
                elif intent == "compare" and source_type == "similar_company":
                    score += 0.2
            
            # Document type scoring
            doc_type = result.get("document_type", "unknown")
            if doc_type == "generated_answer":
                score += 0.2
            elif doc_type == "company_profile":
                score += 0.15
            elif doc_type in ["financial_data", "business_metrics"]:
                score += 0.1
            
            # Freshness scoring
            timestamp = result.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    age_hours = (datetime.now() - dt).total_seconds() / 3600
                    if age_hours < 1:
                        score += 0.1  # Recent processing bonus
                    elif age_hours < 24:
                        score += 0.05  # Daily freshness bonus
                except:
                    pass
            
            # Content quality scoring
            text_length = len(result.get("text", ""))
            if 100 <= text_length <= 1000:
                score += 0.1  # Optimal length for context
            elif 50 <= text_length < 100:
                score += 0.05  # Short but useful
            elif text_length > 1000:
                score += 0.08  # Long content (slightly lower due to token cost)
            
            # Metadata richness bonus
            metadata = result.get("metadata", {})
            if len(metadata) > 3:
                score += 0.05  # Rich metadata bonus
            
            return score
        
        # Sort by enhanced score (highest first)
        ranked = sorted(results, key=calculate_enhanced_score, reverse=True)
        
        # Add ranking position to results
        for i, result in enumerate(ranked):
            result["rank"] = i + 1
            result["final_score"] = calculate_enhanced_score(result)
        
        logger.info(f"Enhanced ranking complete: {len(ranked)} results")
        return ranked
    
    async def _intelligent_trim_to_budget(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Intelligent token budget management with priority for RAG context
        """
        # Separate results by type for intelligent allocation
        rag_answers = [r for r in results if r.get("type") == "rag_answer"]
        rag_context = [r for r in results if r.get("type") == "rag_context"]
        structured_data = [r for r in results if r.get("type") == "structured_data"]
        other_results = [r for r in results if r.get("type") not in ["rag_answer", "rag_context", "structured_data"]]
        
        # Calculate token allocations
        rag_tokens = int(self.max_tokens * self.rag_context_ratio)
        other_tokens = self.max_tokens - rag_tokens
        
        trimmed_results = []
        current_tokens = 0
        
        # Always include RAG answers first (highest priority)
        for result in rag_answers:
            estimated_tokens = self._estimate_tokens(result.get("text", ""))
            if current_tokens + estimated_tokens <= self.max_tokens:
                trimmed_results.append(result)
                current_tokens += estimated_tokens
                result["token_allocation"] = "rag_answer"
        
        # Add RAG context within allocated budget
        rag_context_tokens = 0
        for result in rag_context:
            estimated_tokens = self._estimate_tokens(result.get("text", ""))
            if rag_context_tokens + estimated_tokens <= rag_tokens and current_tokens + estimated_tokens <= self.max_tokens:
                trimmed_results.append(result)
                current_tokens += estimated_tokens
                rag_context_tokens += estimated_tokens
                result["token_allocation"] = "rag_context"
        
        # Add structured data and other results with remaining budget
        remaining_results = structured_data + other_results
        for result in remaining_results:
            estimated_tokens = self._estimate_tokens(result.get("text", ""))
            if current_tokens + estimated_tokens <= self.max_tokens:
                trimmed_results.append(result)
                current_tokens += estimated_tokens
                result["token_allocation"] = "other"
            else:
                # Try to truncate long content if it's valuable
                if result.get("final_score", 0) > 0.8 and estimated_tokens > 200:
                    truncated_text = self._truncate_text_intelligently(result.get("text", ""), 150)
                    truncated_tokens = self._estimate_tokens(truncated_text)
                    if current_tokens + truncated_tokens <= self.max_tokens:
                        result["text"] = truncated_text
                        result["truncated"] = True
                        trimmed_results.append(result)
                        current_tokens += truncated_tokens
                        result["token_allocation"] = "truncated"
        
        logger.info(f"Intelligent trimming: {len(results)} -> {len(trimmed_results)} results ({current_tokens}/{self.max_tokens} tokens)")
        logger.info(f"RAG context tokens: {rag_context_tokens}/{rag_tokens}")
        
        return trimmed_results
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Improved token estimation
        """
        # More accurate token estimation: ~3.5 characters per token for English
        return max(1, int(len(text) / 3.5))
    
    def _truncate_text_intelligently(self, text: str, max_tokens: int) -> str:
        """
        Intelligently truncate text while preserving meaning
        """
        max_chars = int(max_tokens * 3.5)
        if len(text) <= max_chars:
            return text
        
        # Try to truncate at sentence boundaries
        sentences = text.split('. ')
        truncated = ""
        for sentence in sentences:
            if len(truncated + sentence + '. ') <= max_chars:
                truncated += sentence + '. '
            else:
                break
        
        if truncated:
            return truncated.strip()
        
        # Fallback to character truncation with ellipsis
        return text[:max_chars-3] + "..."
    
    async def _optimize_context_for_llm(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize context for LLM prompt construction with structured formatting
        """
        optimized_results = []
        
        # Group results by type for better organization
        result_groups = {
            "rag_answer": [],
            "rag_context": [],
            "structured_data": [],
            "financial_data": [],
            "business_metrics": [],
            "similar_company": [],
            "web_content": [],
            "other": []
        }
        
        for result in results:
            result_type = result.get("type", "other")
            if result_type in result_groups:
                result_groups[result_type].append(result)
            else:
                result_groups["other"].append(result)
        
        # Add results in priority order with enhanced formatting
        priority_order = ["rag_answer", "rag_context", "structured_data", "financial_data", "business_metrics", "similar_company", "web_content", "other"]
        
        for group_type in priority_order:
            group_results = result_groups[group_type]
            if not group_results:
                continue
            
            for result in group_results:
                # Enhance result with structured context information
                enhanced_result = result.copy()
                enhanced_result["context_type"] = group_type
                enhanced_result["formatted_text"] = self._format_result_for_context(result)
                optimized_results.append(enhanced_result)
        
        logger.info(f"Context optimization complete: {len(optimized_results)} results organized")
        return optimized_results
    
    def _format_result_for_context(self, result: Dict[str, Any]) -> str:
        """
        Format individual result for optimal LLM context
        """
        result_type = result.get("type", "unknown")
        entity = result.get("entity", "unknown")
        text = result.get("text", "")
        metadata = result.get("metadata", {})
        
        if result_type == "rag_answer":
            rag_type = metadata.get("rag_type", "unknown")
            return f"AI Generated Answer ({rag_type.upper()} RAG): {text}"
        
        elif result_type == "rag_context":
            company_name = metadata.get("company_name", entity)
            return f"Company Information ({company_name}): {text}"
        
        elif result_type == "rag_error":
            return f"RAG Processing Note: {text}"
        
        elif result_type == "structured_data":
            return f"Database Record ({entity}): {text}"
        
        elif result_type == "similar_company":
            return f"Similar Company ({entity}): {text}"
        
        elif result_type == "financial_data":
            metric_type = metadata.get("metric_type", "unknown")
            return f"Financial Data ({metric_type}): {text}"
        
        elif result_type == "business_metrics":
            metric_type = metadata.get("metric_type", "unknown")
            return f"Business Metrics ({metric_type}): {text}"
        
        elif result_type == "web_content":
            methods = metadata.get("scraping_methods", [])
            method_str = f" via {', '.join(methods)}" if methods else ""
            return f"Web Content{method_str}: {text}"
        
        else:
            return f"{result.get('source', 'Unknown')} ({entity}): {text}"
    
    def get_enhanced_context_blocks(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Convert optimized results to enhanced context blocks for prompt building
        """
        context_blocks = []
        
        # Group by context type for structured presentation
        current_type = None
        type_counter = 0
        
        for i, result in enumerate(results):
            context_type = result.get("context_type", "other")
            
            # Add section headers for different types
            if context_type != current_type:
                if context_type == "rag_answer":
                    context_blocks.append("=== AI Generated Insights ===")
                elif context_type == "rag_context":
                    context_blocks.append("=== Company Knowledge Base ===")
                elif context_type == "structured_data":
                    context_blocks.append("=== Database Information ===")
                elif context_type == "financial_data":
                    context_blocks.append("=== Financial Information ===")
                elif context_type == "business_metrics":
                    context_blocks.append("=== Business Metrics ===")
                elif context_type == "similar_company":
                    context_blocks.append("=== Similar Companies ===")
                elif context_type == "web_content":
                    context_blocks.append("=== Web Research ===")
                else:
                    context_blocks.append("=== Additional Information ===")
                
                current_type = context_type
                type_counter = 1
            else:
                type_counter += 1
            
            # Format the context block with enhanced information
            formatted_text = result.get("formatted_text", result.get("text", ""))
            relevance_score = result.get("relevance_score", 0.0)
            
            block = f"[{type_counter}] {formatted_text}"
            
            # Add relevance score for high-confidence results
            if relevance_score > 0.7:
                block += f" (Confidence: {relevance_score:.2f})"
            
            context_blocks.append(block)
        
        return context_blocks
    
    def get_context_blocks(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        Convert results to context blocks for prompt building (backward compatibility)
        """
        return self.get_enhanced_context_blocks(results) 