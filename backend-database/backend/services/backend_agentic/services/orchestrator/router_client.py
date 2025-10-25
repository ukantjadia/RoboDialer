# LangGraph-powered router client
import logging
import json
from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
import re
import os
from ...llm.deepseek_client import DeepSeekClient

# Import agentic logging
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from agentic_logging import get_agentic_logger

logger = get_agentic_logger('services.orchestrator')

# Optional HuggingFace extractor integration (disabled by default)
USE_HF_EXTRACTOR = False

# Control raw LLM logging for entity extraction
LOG_LLM_ENTITY_RAW = os.getenv("LOG_LLM_ENTITY_RAW", "false").lower() == "true"

def hf_extract(_query: str) -> Dict[str, Any]:
    """Stub for HF extractor; replace when integrating real model."""
    return {"entities": [], "confidence": 0.0, "reasoning": ["hf_extract stub"]}

# Import semantic detection components
SEMANTIC_DETECTION_AVAILABLE = False
try:
    from ..semantic_detection.hybrid_detector import HybridIntentDetector
    from ..semantic_detection.entity_extractor import SemanticEntityExtractor
    from ..semantic_detection.semantic_intent_detector import SemanticIntentDetector
    from ..semantic_detection.embedding_manager import Word2VecEmbeddingManager
    from ..semantic_detection.config_loader import SemanticConfigLoader
    SEMANTIC_DETECTION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Semantic detection not available: {e}")
    SEMANTIC_DETECTION_AVAILABLE = False

class RouterState(TypedDict):
    """State management for routing workflow"""
    query: str
    user_id: str
    messages: Optional[List[Dict[str, str]]]
    lead_ids: Optional[List[str]]  # <-- NEW: Add lead_ids to the state
    intent: str
    entities: List[str]
    tools: List[str]
    params: Dict[str, Any]
    confidence: float
    reasoning: List[str]
    errors: List[str]
    entity_metadata: Dict[str, Dict[str, Any]]

class LangGraphRouter:
    """
    LangGraph-powered intelligent router with semantic intent detection
    and entity extraction, with LLM and pattern-based fallbacks
    """
    
    def __init__(self, llm_client=None, semantic_config_path=None):
        # Always default to DeepSeekClient unless an alternative llm_client is provided
        self.llm_client = llm_client or DeepSeekClient()
        self.workflow = self._create_routing_graph()
        
        # Initialize semantic detection components
        self.semantic_detector = None
        self.entity_extractor = None
        self.hybrid_detector = None
        self.semantic_initialized = False
        
        if SEMANTIC_DETECTION_AVAILABLE:
            try:
                # Initialize semantic components
                self.semantic_detector = SemanticIntentDetector(semantic_config_path)
                self.hybrid_detector = HybridIntentDetector(
                    semantic_detector=self.semantic_detector,
                    config_path=semantic_config_path
                )
                logger.info("Semantic detection components initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic detection: {e}")
                # Don't modify global variable, just mark as not available for this instance
                self.semantic_detector = None
                self.hybrid_detector = None
        
        # Fallback patterns for when semantic and LLM are unavailable
        self.intent_patterns = {
            "compare": r"\b(compare|versus|vs|difference|which|better|higher|lower|contrast|against)\b",
            "analyze": r"\b(analyze|analysis|examine|study|investigate|evaluate|assess|review|inspect)\b",
            "search": r"\b(search|find|look|get|retrieve|locate|discover|lookup|fetch|obtain)\b",
            "summarize": r"\b(summarize|summary|overview|brief|outline|recap)\b"
        }
        
        self.entity_patterns = {
            "company": r"\b(company|corp|inc|llc|ltd)\b",
            "revenue": r"\b(revenue|sales|income|earnings)\b",
            "growth": r"\b(growth|increase|decrease|change)\b",
            "industry": r"\b(industry|sector|market)\b",
            "employees": r"\b(employees|staff|workforce|team)\b"
        }
    
    def _create_routing_graph(self) -> StateGraph:
        """
        Create LangGraph workflow for intelligent routing
        """
        workflow = StateGraph(RouterState)
        
        # Add nodes
        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("extract_entities", self._extract_entities)
        workflow.add_node("select_tools", self._select_tools)
        workflow.add_node("generate_parameters", self._generate_parameters)
        workflow.add_node("validate_plan", self._validate_plan)
        workflow.add_node("handle_errors", self._handle_errors)
        
        # Set entry point
        workflow.set_entry_point("analyze_intent")
        
        # Add edges
        workflow.add_edge("analyze_intent", "extract_entities")
        workflow.add_edge("extract_entities", "select_tools")
        workflow.add_edge("select_tools", "generate_parameters")
        workflow.add_edge("generate_parameters", "validate_plan")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "validate_plan",
            self._should_retry,
            {
                "retry": "analyze_intent",
                "error": "handle_errors",
                "complete": END
            }
        )
        
        workflow.add_edge("handle_errors", END)
        
        return workflow.compile(checkpointer=None)
    
    async def initialize_semantic_detection(self) -> bool:
        """
        Initialize semantic detection components.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if not SEMANTIC_DETECTION_AVAILABLE or self.semantic_initialized:
            return self.semantic_initialized
        
        try:
            # Initialize semantic detector
            if self.semantic_detector:
                semantic_success = await self.semantic_detector.initialize()
                if not semantic_success:
                    logger.warning("Semantic detector initialization failed")
                    return False
            
            # Initialize hybrid detector
            if self.hybrid_detector:
                hybrid_success = await self.hybrid_detector.initialize()
                if not hybrid_success:
                    logger.warning("Hybrid detector initialization failed")
                    return False
            
            # Initialize entity extractor with embedding manager
            if self.semantic_detector and self.semantic_detector.embedding_manager:
                self.entity_extractor = SemanticEntityExtractor(
                    self.semantic_detector.embedding_manager
                )
                logger.info("Semantic entity extractor initialized")
            
            self.semantic_initialized = True
            logger.info("Semantic detection fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic detection: {e}")
            return False
    
    async def generate_plan(self, query: str, user_id: str, messages: Optional[List[Dict[str, str]]] = None, lead_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate execution plan using LangGraph workflow with semantic detection.
        Now accepts optional lead_ids.
        """
        try:
            if not self.semantic_initialized and SEMANTIC_DETECTION_AVAILABLE:
                await self.initialize_semantic_detection()
            
            logger.debug(f"[Router] generate_plan start | user={user_id} | query={query} | lead_ids={lead_ids}")
            
            # Initialize state, now including lead_ids
            initial_state = RouterState(
                query=query,
                user_id=user_id,
                messages=messages,
                lead_ids=lead_ids, # <-- THIS WAS THE MISSING PIECE
                intent="",
                entities=[],
                tools=[],
                params={},
                confidence=0.0,
                reasoning=[],
                errors=[],
                entity_metadata={}
            )
            
            final_state = await self.workflow.ainvoke(initial_state)
            
            if final_state.get("intent") == "compare" and len(final_state.get("entities", [])) < 2:
                logger.debug("[Router] Downgrading intent from compare to analyze due to <2 entities")
                final_state["reasoning"].append("Downgraded compare to analyze: fewer than 2 entities")
                final_state["intent"] = "analyze"
            
            plan = {
                "intent": final_state["intent"],
                "entities": final_state["entities"],
                "tools": final_state["tools"],
                "params": final_state["params"],
                "confidence": final_state["confidence"],
                "reasoning": final_state["reasoning"]
            }
            
            logger.info(f"[Router] plan | intent={plan['intent']} | entities={plan['entities']} | tools={plan['tools']} | confidence={plan['confidence']:.2f}")
            return plan
            
        except Exception as e:
            logger.error(f"Error in LangGraph routing workflow: {str(e)}")
            return await self._fallback_routing(query, user_id, messages)
    
    async def _analyze_intent(self, state: RouterState) -> RouterState:
        """
        Analyze query intent using semantic detection, LLM, or pattern matching fallback
        """
        try:
            logger.debug(f"[Router] _analyze_intent | query={state['query']}")
            # Try semantic first
            if self.semantic_initialized and self.hybrid_detector:
                semantic_result = await self.hybrid_detector.detect_intent(state["query"])
                state["intent"] = semantic_result.intent
                state["confidence"] = semantic_result.confidence
                state["reasoning"].append(f"Semantic ({semantic_result.method}): {semantic_result.reasoning}")
                logger.info(f"[Router] intent(semantic)={state['intent']} conf={state['confidence']:.3f}")
                return state
            # LLM intent
            elif self.llm_client:
                system_prompt = """You are an expert query analyzer. Analyze the user query and determine the primary intent, considering the conversation context.

Available intents:
- compare: When user wants to compare multiple entities (e.g., "compare Microsoft vs Apple", "which is better")
- analyze: When user wants detailed information, analysis, or comprehensive data about specific entities (e.g., "tell me about Microsoft", "analyze Microsoft's performance", "what is their revenue", "information about X company")
- search: When user wants to find or discover unknown entities (e.g., "find tech companies in Seattle", "show me companies that do X")
- summarize: When user wants a brief summary or overview (e.g., "summarize the company", "give me a quick overview")

Intent Classification Rules:
- "Tell me about [Company]" = ANALYZE (detailed information request)
- "What is [Company]" = ANALYZE (information request)
- "Information about [Company]" = ANALYZE (information request)
- "[Company] details" = ANALYZE (information request)
- "Find companies that..." = SEARCH (discovery request)
- "Show me companies..." = SEARCH (discovery request)
- "Compare A vs B" = COMPARE (comparison request)
- "Brief overview of..." = SUMMARIZE (summary request)

Context Guidelines:
- Use conversation history to understand references like "their", "it", "them", "the company"
- If previous messages mention specific companies, pronouns likely refer to those companies
- Questions about specific metrics (revenue, growth, employees) of previously mentioned entities are typically "analyze" intent
- Requests to compare previously mentioned entities with others are "compare" intent
- When in doubt between analyze and search, choose ANALYZE if a specific entity is mentioned

Return ONLY JSON:
{"intent":"compare|analyze|search|summarize","confidence":0-1,"reasoning":"explanation of why this intent was chosen"}
"""
                # Use context-aware call if messages are available
                if state.get("messages"):
                    # Build message array with system prompt and conversation context
                    messages = [{"role": "system", "content": system_prompt}]
                    # Add conversation history
                    messages.extend(state["messages"])
                    # Add current query
                    messages.append({"role": "user", "content": f"Query: {state['query']}"})
                    response = await self.llm_client.generate_response_with_context(messages)
                else:
                    user_prompt = f"Query: {state['query']}"
                    response = await self.llm_client.generate_response(user_prompt, system_prompt)
                if response.status == "success" and response.validation_result.get("is_json", False):
                    try:
                        result = json.loads(response.content)
                        state["intent"] = result.get("intent", "search")
                        confidence = result.get("confidence", 0.5)
                        if isinstance(confidence, dict):
                            confidence = confidence.get("score", 0.5)
                        state["confidence"] = float(confidence)
                        state["reasoning"].append(result.get("reasoning", "LLM-based intent detection"))
                        logger.info(f"[Router] intent(llm)={state['intent']} conf={state['confidence']:.3f}")
                        return state
                    except json.JSONDecodeError:
                        raise Exception("Invalid JSON response from LLM")
                else:
                    raise Exception("LLM response validation failed")
            else:
                raise Exception("No semantic detection or LLM client available")
        except Exception as e:
            logger.warning(f"Advanced intent detection failed: {str(e)}, falling back to pattern matching")
            # Final fallback to pattern matching
            state["intent"] = self._detect_intent_fallback(state["query"])
            state["confidence"] = 0.6
            state["reasoning"].append("Pattern-based intent detection (final fallback)")
        return state
    
    async def _extract_entities(self, state: RouterState) -> RouterState:
        """
        Extract entities using HF, semantic extraction, LLM, or pattern matching fallback
        """
        try:
            logger.debug(f"[Router] _extract_entities | query={state['query']} | lead_ids={state.get('lead_ids')}")            # If entities already seeded, keep them
            # If lead_ids are provided in the state, use them directly as entities
            if state.get("lead_ids"):
                provided_ids = state["lead_ids"]
                logger.info(f"[Router] Prioritizing provided lead_ids as entities: {provided_ids}")
                state["entities"] = provided_ids
                state["confidence"] = 1.0  # We have 100% confidence in user-provided IDs
                state["reasoning"].append(f"Using {len(provided_ids)} provided lead_ids as primary entities.")
                return state # IMPORTANT: We return here, skipping all other extraction logic
            
            
            if state.get("entities"):
                return state
            logger.debug("No lead_ids provided, proceeding with entity extraction from query.")
            # HF extractor first if enabled
            if USE_HF_EXTRACTOR:
                try:
                    result = hf_extract(state["query"])
                    if result.get("entities"):
                        state["entities"] = result["entities"][:3]
                        state["reasoning"].extend(result.get("reasoning", []))
                        state["confidence"] = max(state["confidence"], float(result.get("confidence", 0.6)))
                        logger.info(f"[Router] entities(hf)={state['entities']}")
                        return state
                except Exception as hf_err:
                    logger.warning(f"HF entity extraction failed: {hf_err}")
            
            # Semantic extraction
            if self.semantic_initialized and self.entity_extractor:
                logger.debug("Using semantic entity extraction")
                known_entities = [
                    # Placeholder known list; in production, derive from database
                    "Microsoft", "Apple", "Google", "Amazon", "Meta", "Tesla", "Netflix", "Adobe",
                    "Salesforce", "Oracle", "IBM", "Intel", "NVIDIA", "AMD", "Cisco", "VMware",
                    "Lumious", "Kwik Brain", "QiO Technologies", "CustomGuide", "AdaptedMind", "Canopy Ed"
                ]
                entity_matches = await self.entity_extractor.extract_entities(state["query"], known_entities, entity_type="company")
                extracted_entities: List[str] = []
                entity_confidences: Dict[str, Any] = {}
                total_confidence = 0.0
                for match in entity_matches:
                    min_threshold = 0.8 if match.method == "direct" else 0.7
                    if match.confidence >= min_threshold:
                        extracted_entities.append(match.entity)
                        entity_confidences[match.entity] = {
                            "confidence": match.confidence,
                            "method": match.method,
                            "matched_text": match.matched_text,
                            "position": match.position,
                        }
                        total_confidence += match.confidence
                # Dedup and sort
                unique_entities: List[str] = []
                seen = set()
                for ent in extracted_entities:
                    if ent not in seen:
                        unique_entities.append(ent); seen.add(ent)
                sorted_entities = sorted(unique_entities, key=lambda e: entity_confidences.get(e, {}).get("confidence", 0.0), reverse=True)
                state["entities"] = sorted_entities[:3]
                state["entity_metadata"] = {k: v for k, v in entity_confidences.items() if k in state["entities"]}
                if extracted_entities:
                    avg = total_confidence / len(extracted_entities)
                    state["confidence"] = (state["confidence"] * 0.5) + (avg * 0.5)
                    logger.info(f"[Router] entities(semantic)={state['entities']} conf_avg={avg:.3f}")
                else:
                    state["reasoning"].append("Semantic entity extraction: no entities found above threshold")
                return state
            
            # LLM extraction
            if self.llm_client:
                logger.debug("Using LLM entity extraction")
                system_prompt = """Extract company names from the user query, using conversation context to resolve references.

Context Resolution Rules:
- "their", "its", "the company's" → refer to companies mentioned in previous messages
- "them", "those companies" → refer to multiple companies mentioned previously  
- "it", "this company" → refer to the most recently mentioned company
- Direct company names should always be extracted as-is

Examples:
- Previous: "Tell me about Microsoft" → Current: "their revenue" → Extract: ["Microsoft"]
- Previous: "Compare Apple and Google" → Current: "their market share" → Extract: ["Apple", "Google"]
- Current: "Microsoft revenue" → Extract: ["Microsoft"]

Return ONLY valid JSON:
{"entities":["CompanyName1","CompanyName2"],"confidence":0.0-1.0}

Confidence Guidelines:
- 0.9-1.0: Direct company names or clear context references
- 0.7-0.8: Probable context references with some ambiguity
- 0.5-0.6: Uncertain references or partial matches
- 0.0-0.4: Very uncertain or no clear entities found
"""
                # Use context-aware call if messages are available
                if state.get("messages"):
                    # Build message array with system prompt and conversation context
                    messages = [{"role": "system", "content": system_prompt}]
                    # Add conversation history
                    messages.extend(state["messages"])
                    # Add current query
                    messages.append({"role": "user", "content": state["query"]})
                    response = await self.llm_client.generate_response_with_context(messages)
                else:
                    user_prompt = state["query"]
                    response = await self.llm_client.generate_response(user_prompt, system_prompt)
                # Log raw LLM content for debugging (full when LOG_LLM_ENTITY_RAW enabled, otherwise truncated)
                try:
                    raw_content = getattr(response, "content", None)
                    if raw_content is not None:
                        if LOG_LLM_ENTITY_RAW:
                            logger.info(f"[Router] LLM entity raw: {raw_content}")
                        else:
                            snippet = raw_content if len(raw_content) <= 500 else raw_content[:500] + "..."
                            logger.debug(f"[Router] LLM entity raw (truncated): {snippet}")
                except Exception as _log_err:
                    logger.debug(f"[Router] failed to log raw LLM entity content: {_log_err}")
                if response.status == "success" and response.validation_result.get("is_json", False):
                    try:
                        result = json.loads(response.content)
                        ents = result.get("entities", [])
                        state["entities"] = ents[:3]
                        conf = result.get("confidence", 0.6)
                        if isinstance(conf, dict):
                            conf = conf.get("score", 0.6)
                        state["confidence"] = max(state["confidence"], float(conf))
                        logger.info(f"[Router] entities(llm)={state['entities']}")
                        return state
                    except json.JSONDecodeError:
                        logger.warning("LLM entity JSON decode failed")
                else:
                    logger.warning("LLM entity response invalid or non-JSON")
            
            # Pattern fallback
            logger.debug("Pattern-based entity fallback")
            extracted = self._extract_entities_fallback(state["query"])  # method exists elsewhere in file
            state["entities"] = extracted[:3]
            logger.info(f"[Router] entities(pattern)={state['entities']}")
            return state
        except Exception as e:
            logger.warning(f"Advanced entity extraction failed: {e}, falling back to pattern matching")
            state["entities"] = self._extract_entities_fallback(state["query"])[:3]
            return state
    
    async def _select_tools(self, state: RouterState) -> RouterState:
        """Select tools based on intent/entities with safe defaults."""
        try:
            intent = state.get("intent") or "search"
            entities = state.get("entities") or []
            tools: List[str] = []
            # Always start with fact_db under database-gated policy
            tools.append("fact_db")
            # Add vector_query for richer context on analyze/compare/summarize
            if intent in ("analyze", "compare", "summarize"):
                tools.append("vector_query")
            # Optionally suggest scraper when at least one entity present
            if entities:
                tools.append("scraper")
            # De-duplicate while preserving order
            seen = set()
            deduped = []
            for t in tools:
                if t not in seen:
                    deduped.append(t); seen.add(t)
            state["tools"] = deduped
            state["reasoning"].append(f"Tool selection: {deduped} for intent={intent} entities={len(entities)}")
            logger.debug(f"[Router] _select_tools | intent={intent} | entities={entities} | tools={deduped}")
            return state
        except Exception as e:
            logger.warning(f"Tool selection failed: {e}, falling back to rule-based")
            state["tools"] = ["fact_db"]
            return state
    
    async def _generate_parameters(self, state: RouterState) -> RouterState:
        """
        Generate parameters for selected tools with conditional logic
        """
        try:
            params = {}
            logger.debug(f"[Router] _generate_parameters | intent={state.get('intent')} | entities={state.get('entities')}")
            
            # Derive candidate entities directly from raw query when extractor found none
            query_entities: List[str] = []
            try:
                if (not state.get("entities")) and state.get("query"):
                    raw = state["query"].strip()
                    q = raw
                    import re as _re
                    # Remove common leading phrases
                    q = _re.sub(r"^(give me|provide|show|tell me|what is|based on|suggest)\b.*?\bof\b\s+", "", q, flags=_re.IGNORECASE)
                    q = _re.sub(r"^(give me|provide|show|tell me|what is|based on|suggest)\b\s+", "", q, flags=_re.IGNORECASE)
                    # Normalize separators to commas
                    q = _re.sub(r"\s+(?:and|vs|versus|&)\s+", ",", q, flags=_re.IGNORECASE)
                    # Split on commas
                    parts = [p.strip() for p in q.split(",") if p.strip()]
                    # Basic filter
                    filtered: List[str] = []
                    for p in parts:
                        if len(p) < 2:
                            continue
                        if _re.search(r"[A-Za-z]", p):
                            filtered.append(p)
                    query_entities = filtered[:4]
            except Exception as seg_err:
                logger.debug(f"[Router] segmenting error: {seg_err}")
            
            # Generate parameters for each selected tool
            for tool in state["tools"]:
                if tool == "fact_db":
                    if query_entities:
                        entity_params = {
                            "entities": query_entities,
                            "fields": [
                                "Company Name", "Industry ", "Revenue", "Employees", 
                                "Year Founded", "Business Type (B2B, B2B2C) ", 
                                "Product/Service Category", "City", "State", "Website"
                            ],
                            "intent": state["intent"]
                        }
                        params["fact_db"] = entity_params
                        logger.debug(f"[Router] fact_db params (derived)={entity_params}")
                        continue
                    
                    # Determine the appropriate operation based on intent and query content
                    operation = "get_facts"  # default
                    query_lower = state["query"].lower()
                    
                    # Check for industry-specific searches
                    if any(industry in query_lower for industry in ["education", "technology", "healthcare", "finance", "manufacturing", "retail"]):
                        operation = "industry_filter"
                        # Extract industry from query
                        industry = None
                        if "education" in query_lower:
                            industry = "Education"
                        elif "technology" in query_lower:
                            industry = "Technology"
                        elif "healthcare" in query_lower:
                            industry = "Healthcare"
                        elif "finance" in query_lower:
                            industry = "Finance"
                        elif "manufacturing" in query_lower:
                            industry = "Manufacturing"
                        elif "retail" in query_lower:
                            industry = "Retail"
                        
                        # Detect 'top N' pattern to set limit
                        limit = 10
                        try:
                            m = _re.search(r"top\s+(\d+)", state["query"], flags=_re.IGNORECASE)
                            if m:
                                limit = max(1, int(m.group(1)))
                        except Exception:
                            pass
                        
                        params["fact_db"] = {
                            "operation": operation,
                            "industry": industry,
                            "limit": limit,
                            "fields": [
                                "Company Name", "Industry ", "Revenue", "Employees", 
                                "Year Founded", "Business Type (B2B, B2B2C) ", 
                                "Product/Service Category", "City", "State", "Website"
                            ],
                            "sort_by": "Revenue",
                            "intent": state["intent"]
                        }
                    elif state["intent"] == "search" and not state["entities"]:
                        # General search operation (fallback)
                        operation = "search"
                        # Extract search terms from query
                        search_terms = []
                        if "companies" in query_lower:
                            # Look for descriptive terms before "companies"
                            import re
                            pattern = r'(\w+)\s+companies'
                            matches = re.findall(pattern, query_lower)
                            search_terms.extend(matches)
                        
                        # If no specific search terms, use a broad search
                        search_query = " ".join(search_terms) if search_terms else "company"
                        
                        params["fact_db"] = {
                            "operation": operation,
                            "query": search_query,
                            "limit": 10,
                            "fields": [
                                "Company Name", "Industry ", "Revenue", "Employees", 
                                "Year Founded", "Business Type (B2B, B2B2C) ", 
                                "Product/Service Category", "City", "State", "Website"
                            ],
                            "intent": state["intent"]
                        }
                    else:
                        # Default entity-based operation with confidence propagation
                        entity_params = {
                            "entities": state["entities"],
                            "fields": [
                                "Company Name", "Industry ", "Revenue", "Employees", 
                                "Year Founded", "Business Type (B2B, B2B2C) ", 
                                "Product/Service Category", "City", "State", "Website"
                            ],
                            "intent": state["intent"]
                        }
                        
                        # If no entities extracted, fall back to using the raw query as candidate entity
                        if (not entity_params.get("entities")) and state.get("query"):
                            entity_params["entities"] = [state["query"]]
                        
                        # Add entity confidence information if available
                        if hasattr(state, "entity_metadata") and state["entity_metadata"]:
                            entity_params["entity_confidences"] = state["entity_metadata"]
                            # Sort entities by confidence for prioritized processing
                            sorted_entities = sorted(
                                entity_params["entities"], 
                                key=lambda e: state["entity_metadata"].get(e, {}).get("confidence", 0.0),
                                reverse=True
                            )
                            entity_params["entities"] = sorted_entities
                        
                        params["fact_db"] = entity_params
                
                elif tool == "scraper":
                    # Conditional scraper parameters based on intent with entity confidence
                    selectors = ["/about", "/company"]
                    if state["intent"] == "analyze":
                        selectors.extend(["/financials", "/news", "/investors"])
                    elif state["intent"] == "compare":
                        selectors.extend(["/financials", "/products"])
                    
                    scraper_params = {
                        "selectors": selectors,
                        "timeout": 30,
                        "max_retries": 2,
                        "intent": state["intent"]
                    }
                    
                    # Add entity confidence information for prioritized scraping
                    if hasattr(state, "entity_metadata") and state["entity_metadata"]:
                        scraper_params["entity_confidences"] = state["entity_metadata"]
                        # Adjust timeout based on entity confidence
                        avg_confidence = sum(
                            meta.get("confidence", 0.0) 
                            for meta in state["entity_metadata"].values()
                        ) / len(state["entity_metadata"])
                        
                        if avg_confidence > 0.8:
                            scraper_params["timeout"] = 45  # More time for high-confidence entities
                        elif avg_confidence < 0.5:
                            scraper_params["timeout"] = 20  # Less time for low-confidence entities
                    
                    params["scraper"] = scraper_params
                
                elif tool == "vector_query":
                    # Adjust parameters based on intent and entity confidence
                    top_k = 5
                    if state["intent"] == "analyze":
                        top_k = 10  # More results for analysis
                    elif state["intent"] == "compare":
                        top_k = 8   # Moderate results for comparison
                    
                    vector_params = {
                        "top_k": top_k,
                        "similarity_threshold": 0.7,
                        "intent": state["intent"],
                        "entities": state["entities"]
                    }
                    
                    # Adjust similarity threshold based on entity confidence
                    if hasattr(state, "entity_metadata") and state["entity_metadata"]:
                        vector_params["entity_confidences"] = state["entity_metadata"]
                        avg_confidence = sum(
                            meta.get("confidence", 0.0) 
                            for meta in state["entity_metadata"].values()
                        ) / len(state["entity_metadata"])
                        
                        # Lower threshold for high-confidence entities to get more results
                        if avg_confidence > 0.8:
                            vector_params["similarity_threshold"] = 0.6
                        # Higher threshold for low-confidence entities to be more selective
                        elif avg_confidence < 0.5:
                            vector_params["similarity_threshold"] = 0.75
                    
                    params["vector_query"] = vector_params
                
                elif tool == "haystack_rag":
                    rag_params = {
                        "top_k": 5,
                        "retrieval_mode": "hybrid",  # Use hybrid search
                        "intent": state["intent"],
                        "entities": state["entities"]
                    }
                    
                    # Enhance RAG parameters with entity confidence information
                    if hasattr(state, "entity_metadata") and state["entity_metadata"]:
                        rag_params["entity_confidences"] = state["entity_metadata"]
                        avg_confidence = sum(
                            meta.get("confidence", 0.0) 
                            for meta in state["entity_metadata"].values()
                        ) / len(state["entity_metadata"])
                        
                        # Adjust retrieval parameters based on confidence
                        if avg_confidence > 0.8:
                            rag_params["top_k"] = 7  # More results for high-confidence entities
                            rag_params["retrieval_mode"] = "semantic"  # Use semantic for precise matches
                        elif avg_confidence < 0.5:
                            rag_params["top_k"] = 3  # Fewer results for low-confidence entities
                            rag_params["retrieval_mode"] = "keyword"  # Use keyword for broader matches
                    
                    params["haystack_rag"] = rag_params
            
            state["params"] = params
            state["reasoning"].append("Generated parameters for selected tools")
            logger.debug(f"[Router] params keys={list(params.keys())}")
            return state
        except Exception as e:
            logger.error(f"Error generating parameters: {e}")
            state["errors"].append(str(e))
            return state
    
    async def _validate_plan(self, state: RouterState) -> RouterState:
        """
        Validate the generated plan for completeness and consistency
        """
        try:
            validation_errors = []
            
            # Check if intent is valid
            valid_intents = ["compare", "analyze", "search", "summarize"]
            if state["intent"] not in valid_intents:
                validation_errors.append(f"Invalid intent: {state['intent']}")
            
            # Check if tools are selected
            if not state["tools"]:
                validation_errors.append("No tools selected")
            
            # Check if parameters are generated for selected tools
            for tool in state["tools"]:
                if tool not in state["params"]:
                    validation_errors.append(f"Missing parameters for tool: {tool}")
            
            # Check confidence threshold
            if state["confidence"] < 0.3:
                validation_errors.append(f"Low confidence score: {state['confidence']}")
            
            # Intent-specific validations
            if state["intent"] == "compare" and len(state["entities"]) < 2:
                validation_errors.append("Compare intent requires at least 2 entities")
            
            if validation_errors:
                state["errors"].extend(validation_errors)
                logger.warning(f"Plan validation failed: {validation_errors}")
            else:
                state["reasoning"].append("Plan validation successful")
                logger.info("Plan validation passed")
            
        except Exception as e:
            logger.error(f"Error during plan validation: {str(e)}")
            state["errors"].append(f"Validation error: {str(e)}")
        
        return state
    
    async def _handle_errors(self, state: RouterState) -> RouterState:
        """
        Handle errors and provide fallback plan
        """
        logger.warning(f"Handling routing errors: {state['errors']}")
        
        # Provide minimal fallback plan
        state["intent"] = "search"
        state["entities"] = []
        state["tools"] = ["fact_db"]
        state["params"] = {
            "fact_db": {
                "entities": [],
                "fields": ["Company Name", "Industry", "Revenue"],
                "operation": "get_facts",
                "intent": "search"
            }
        }
        state["confidence"] = 0.3
        state["reasoning"].append("Fallback plan due to errors")
        
        return state
    
    def _should_retry(self, state: RouterState) -> str:
        """
        Determine if the workflow should retry, handle errors, or complete
        """
        if state["errors"]:
            # Don't retry if we've already tried multiple times or have critical errors
            if len(state["errors"]) > 3 or state["confidence"] < 0.2:
                return "error"
            # Only retry for specific error types
            retry_errors = ["validation", "timeout", "network"]
            if any(error_type in str(state["errors"]).lower() for error_type in retry_errors):
                return "retry"
            else:
                return "error"
        return "complete"
    
    # Fallback methods for when LLM is unavailable
    def _detect_intent_fallback(self, query: str) -> str:
        """Fallback intent detection using pattern matching"""
        query_lower = query.lower()
        for intent, pattern in self.intent_patterns.items():
            if re.search(pattern, query_lower):
                return intent
        return "search"
    
    def _extract_entities_fallback(self, query: str) -> List[str]:
        """Fallback entity extraction using pattern matching"""
        entities = []
        
        # Handle specific known patterns first
        query_lower = query.lower()
        
        # Check for specific company mentions
        if "canopy ed" in query_lower:
            entities.append("Canopy Ed")
        if "lumious" in query_lower:
            entities.append("Lumious")
        if "kwik brain" in query_lower:
            entities.append("Kwik Brain")
        if "quimbee" in query_lower:
            entities.append("Quimbee")
        if "microsoft" in query_lower:
            entities.append("Microsoft")
        if "apple" in query_lower:
            entities.append("Apple")
        if "google" in query_lower:
            entities.append("Google")
        if "tesla" in query_lower:
            entities.append("Tesla")
        if "amazon" in query_lower:
            entities.append("Amazon")
        if "weldstar" in query_lower:
            entities.append("Weldstar")
            
        # If we found specific companies, return them
        if entities:
            return entities[:2]  # Limit to 2 most relevant
        
        # Extract company names (quoted strings first)
        company_matches = re.findall(r'"([^"]+)"', query)
        
        if not company_matches:
            # For comparison queries, look for patterns like "Compare X and Y"
            compare_pattern = r'compare\s+([A-Za-z\s]+?)\s+and\s+([A-Za-z\s]+?)(?:\s+and\s+tell|\s+tell|\s*$)'
            compare_matches = re.findall(compare_pattern, query, re.IGNORECASE)
            
            if compare_matches:
                # Extract both companies from comparison
                for match in compare_matches:
                    company1 = match[0].strip()
                    company2 = match[1].strip()
                    # Clean up common words from the end
                    company1 = re.sub(r'\s+(and|tell|which|has|better|growth|potential).*$', '', company1, flags=re.IGNORECASE)
                    company2 = re.sub(r'\s+(and|tell|which|has|better|growth|potential).*$', '', company2, flags=re.IGNORECASE)
                    entities.extend([company1.strip(), company2.strip()])
            else:
                # Fallback to general capitalized word extraction, but filter out common words
                stop_words = {'Compare', 'And', 'The', 'Which', 'Has', 'Better', 'Growth', 'Potential', 'Tell', 'Me', 'That'}
                all_matches = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', query)
                company_matches = [match for match in all_matches if match not in stop_words]
                entities.extend(company_matches)
        else:
            entities.extend(company_matches)
        
        # Extract other entities (but not if they're already captured as companies)
        query_lower = query.lower()
        for entity_type, pattern in self.entity_patterns.items():
            if re.search(pattern, query_lower) and entity_type not in entities:
                entities.append(entity_type)
        
        return entities
    
    def _determine_tools_fallback(self, intent: str, entities: List[str]) -> List[str]:
        """Fallback tool selection using rule-based logic"""
        tools = []
        
        if intent == "compare":
            tools.extend(["fact_db", "vector_query"])
            if len(entities) > 1:
                tools.append("scraper")
        elif intent == "analyze":
            tools.extend(["fact_db", "scraper", "vector_query"])
        elif intent == "search":
            tools.append("fact_db")
            if any("company" in str(entity).lower() for entity in entities):
                tools.append("vector_query")
        elif intent == "summarize":
            tools.extend(["fact_db", "vector_query"])
        
        return tools
    
    async def _fallback_routing(self, query: str, user_id: str, messages: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Conservative fallback: always run fact_db first, avoid open-web tools."""
        intent = "search"
        # Use raw query as candidate entity to force database attempt
        entities = [query] if query else []
        tools = ["fact_db"]
        params: Dict[str, Any] = {
            "fact_db": {
                "entities": entities,
                "fields": ["Company Name", "Industry ", "Revenue", "Employees", "Website"],
                "operation": "get_facts",
                "intent": intent
            }
        }
        return {
            "intent": intent,
            "entities": entities,
            "tools": tools,
            "params": params,
            "confidence": 0.5,
            "reasoning": ["Fallback routing: CSV-gated execution"]
        }


# Legacy RouterClient wrapper for backward compatibility
class RouterClient:
    """
    Backward compatibility wrapper for the new LangGraph router with semantic detection
    """
    
    def __init__(self, llm_client=None, semantic_config_path=None):
        self.langgraph_router = LangGraphRouter(llm_client, semantic_config_path)
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize the router and semantic detection components.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        if self._initialized:
            return True
        
        try:
            # Initialize semantic detection
            success = await self.langgraph_router.initialize_semantic_detection()
            self._initialized = True
            logger.info(f"RouterClient initialized with semantic detection: {success}")
            return True
        except Exception as e:
            logger.warning(f"RouterClient initialization failed: {e}")
            self._initialized = True  # Still mark as initialized to avoid repeated attempts
            return False
    
    async def generate_plan(self, query: str, user_id: str, messages: Optional[List[Dict[str, str]]] = None, lead_ids: Optional[List[str]] = None) -> Dict[str, Any]: # <-- MODIFIED: Add lead_ids parameter
        """
        Generate execution plan - delegates to LangGraph router with automatic initialization
        """
        # Auto-initialize if not done yet
        if not self._initialized:
            await self.initialize()
        
        return await self.langgraph_router.generate_plan(query, user_id, messages, lead_ids=lead_ids)
    
    def get_semantic_status(self) -> Dict[str, Any]:
        """
        Get status of semantic detection components.
        
        Returns:
            Dictionary with semantic detection status information
        """
        return {
            "semantic_available": SEMANTIC_DETECTION_AVAILABLE,
            "semantic_initialized": self.langgraph_router.semantic_initialized,
            "has_semantic_detector": self.langgraph_router.semantic_detector is not None,
            "has_hybrid_detector": self.langgraph_router.hybrid_detector is not None,
            "has_entity_extractor": self.langgraph_router.entity_extractor is not None
        } 