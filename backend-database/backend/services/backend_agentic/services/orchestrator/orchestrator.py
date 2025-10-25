# LangGraph-based orchestrator supervisor
import asyncio
import logging
import json
import re
from typing import Dict, Any, List, Optional, TypedDict
import uuid
from datetime import datetime
from langgraph.graph import StateGraph, END
from dataclasses import dataclass, asdict
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class QueryState(TypedDict):
    """State management for workflow execution across all processing steps"""
    query: str
    user_id: str
    dispatch_id: str
    messages: Optional[List[Dict[str, str]]]  # Conversation context
    plan: Dict[str, Any]
    rag_context: List[Dict[str, Any]]  # RAG retrieval results
    tool_results: List[Dict[str, Any]]
    aggregated_context: List[Dict[str, Any]]
    llm_response: str
    final_result: Dict[str, Any]
    errors: List[str]
    retry_count: int
    execution_metadata: Dict[str, Any]

@dataclass
class ToolResult:
    """Structured tool result"""
    tool_name: str
    status: str  # success, error, partial
    data: Dict[str, Any]
    execution_time: float
    error_message: Optional[str]
    confidence_score: float
    timestamp: datetime

class LangGraphOrchestrator:
    """
    LangGraph-based orchestrator with state-based workflow execution,
    proper error recovery, and rollback capabilities
    """
    
    def __init__(self, router_client=None, llm_client=None, aggregator=None):
        self.router_client = router_client
        self.llm_client = llm_client
        self.aggregator = aggregator
        self.workflow = self._create_workflow()
        self.dispatch_results = {}
        self.session_context = {}
        
        # Configuration
        self.max_retries = 3
        self.tool_timeout = 30
        self.max_concurrent_tools = 3
        # CSV-gated behavior: when True, continue to enrichment (scraper/RAG/LLM) after a positive CSV hit;
        # when False, return CSV-only on hit. Defaults to True per product requirement.
        self.allow_further_tools_on_hit = os.getenv("ALLOW_FURTHER_TOOLS_ON_HIT", "true").lower() == "true"
    
    def _create_workflow(self) -> StateGraph:
        """
        Create LangGraph StateGraph workflow for query processing
        """
        workflow = StateGraph(QueryState)
        
        # Add nodes
        workflow.add_node("route_query", self._route_query)
        workflow.add_node("retrieve_rag_context", self._retrieve_rag_context)
        workflow.add_node("execute_tools", self._execute_tools)
        workflow.add_node("aggregate_results", self._aggregate_results)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("handle_errors", self._handle_errors)
        workflow.add_node("rollback", self._rollback)
        
        # Set entry point
        workflow.set_entry_point("route_query")
        
        # Add conditional edges for RAG integration
        workflow.add_conditional_edges(
            "route_query",
            self._should_use_rag,
            {
                "use_rag": "retrieve_rag_context",
                "skip_rag": "execute_tools"
            }
        )
        
        workflow.add_conditional_edges(
            "retrieve_rag_context",
            self._rag_retrieval_complete,
            {
                "continue": "execute_tools",
                "error": "handle_errors"
            }
        )
        
        workflow.add_conditional_edges(
            "execute_tools",
            self._should_retry_tools,
            {
                "retry": "execute_tools",
                "continue": "aggregate_results",
                "error": "handle_errors"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_response",
            self._should_complete,
            {
                "complete": END,
                "error": "handle_errors"
            }
        )
        
        # Add edges
        workflow.add_edge("aggregate_results", "generate_response")
        workflow.add_edge("handle_errors", "rollback")
        workflow.add_edge("rollback", END)
        
        return workflow.compile(checkpointer=None)
    
    async def process_query(self, user_id: str, query: str, options: Dict[str, Any], messages: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Main entry point for processing queries using LangGraph workflow
        """
        dispatch_id = f"d-{uuid.uuid4().hex[:8]}"
        start_time = datetime.now()
        
        try:
            # Initialize state
            initial_state = QueryState(
                query=query,
                user_id=user_id,
                dispatch_id=dispatch_id,
                messages=messages,
                plan={},
                rag_context=[],
                tool_results=[],
                aggregated_context=[],
                llm_response="",
                final_result={},
                errors=[],
                retry_count=0,
                execution_metadata={
                    "start_time": start_time,
                    "options": options
                }
            )
            
            logger.info(f"Starting workflow execution for dispatch {dispatch_id}")
            
            # Execute workflow without checkpointing
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Store result
            self.dispatch_results[dispatch_id] = final_state["final_result"]
            
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Workflow completed for dispatch {dispatch_id} in {execution_time:.2f}s")
            
            return final_state["final_result"]
            
        except Exception as e:
            logger.error(f"Critical error in workflow execution: {str(e)}")
            execution_time = (datetime.now() - start_time).total_seconds()
            
            error_response = {
                "dispatch_id": dispatch_id,
                "status": "error",
                "error": str(e),
                "execution_time": execution_time,
                "timestamp": start_time.isoformat()
            }
            
            self.dispatch_results[dispatch_id] = error_response
            return error_response
    
    async def _route_query(self, state: QueryState) -> QueryState:
        """
        Route query using LangGraph router client
        """
        try:
            logger.info(f"Routing query for dispatch {state['dispatch_id']}")
            
            if self.router_client:
                plan = await self.router_client.generate_plan(state["query"], state["user_id"], state.get("messages"))
                state["plan"] = plan
                logger.info(f"Generated plan with {len(plan.get('tools', []))} tools")
            else:
                # Fallback plan
                state["plan"] = {
                    "intent": "search",
                    "entities": [],
                    "tools": ["fact_csv"],
                    "params": {"fact_csv": {"entities": [], "fields": ["Company Name"]}},
                    "confidence": 0.3,
                    "reasoning": ["No router client available - using fallback"]
                }
                logger.warning("No router client available, using fallback plan")
            
        except Exception as e:
            logger.error(f"Error in routing: {str(e)}")
            state["errors"].append(f"Routing error: {str(e)}")
        
        return state
    
    async def _execute_tools(self, state: QueryState) -> QueryState:
        """
        Execute tools based on the plan with CSV-gated coordination and error handling
        """
        try:
            logger.info(f"Executing tools for dispatch {state['dispatch_id']}")
            
            tools = state["plan"].get("tools", [])
            params = state["plan"].get("params", {})
            
            # Always run fact_csv first (CSV-gated mode)
            fact_params = params.get("fact_csv", {}).copy()
            if not fact_params:
                # Build default fact params using entities or the raw query as candidate entity
                entities = state["plan"].get("entities") or []
                if not entities and state.get("query"):
                    entities = [state["query"]]
                fact_params = {
                    "entities": entities,
                    "fields": ["Company Name", "Industry ", "Revenue", "Employees", "Website"],
                    "operation": "get_facts",
                    "intent": state["plan"].get("intent", "search")
                }
                params["fact_csv"] = fact_params
            else:
                # If entities are missing/empty, inject the raw query as a candidate entity
                if not fact_params.get("entities") and state.get("query"):
                    fact_params["entities"] = [state["query"]]
                # Ensure required fields include Website and Industry (with trailing space variant)
                fields = fact_params.get("fields", []) or []
                required_fields = ["Company Name", "Industry ", "Revenue", "Employees", "Website"]
                # Also include "Industry" without trailing space for robustness
                alt_fields = ["Industry"]
                for fld in required_fields + alt_fields:
                    if fld not in fields:
                        fields.append(fld)
                fact_params["fields"] = fields
                params["fact_csv"] = fact_params
            
            # Execute fact_csv directly
            fact_csv_result = await self._execute_single_tool_direct("fact_csv", fact_params)
            processed_results: List[ToolResult] = [fact_csv_result]
            
            # Evaluate CSV result for gating
            csv_data = fact_csv_result.data.get("data", {}) if isinstance(fact_csv_result.data, dict) else {}
            total_results = csv_data.get("total_results", 0)
            if fact_csv_result.status != "success" or total_results == 0:
                # Short-circuit: company not found in CSV
                state["tool_results"] = [asdict(r) for r in processed_results]
                state["final_result"] = {
                    "dispatch_id": state["dispatch_id"],
                    "status": "not_found",
                    "message": "Company not found in CSV",
                    "query": state.get("query", "")
                }
                logger.info("CSV-gated: company not found, ending execution early")
                return state
            
            # If we reach here, CSV hit was found. Enrich when allowed
            if self.allow_further_tools_on_hit:
                logger.info("CSV hit found; proceeding with enrichment tools")
                # Prepare scraper params using CSV-provided website URLs when available
                website_urls = csv_data.get("website_urls", [])
                if website_urls:
                    scraper_params = params.get("scraper", {}).copy()
                    scraper_params["csv_urls"] = website_urls
                    # Map semantic intent to scraper intent (lightweight, reuse existing mapping logic)
                    intent = state.get("plan", {}).get("intent", "search")
                    intent_mapping = {
                        "analyze": "financial",
                        "compare": "financial",
                        "search": "about",
                        "summarize": "about"
                    }
                    scraper_params["query_intent"] = intent_mapping.get(intent, "general")
                    scraper_params["semantic_intent"] = intent
                    scraper_params["intent_confidence"] = state.get("plan", {}).get("confidence", 0.5)
                    scraper_result = await self._execute_single_tool_direct("scraper", scraper_params)
                    processed_results.append(scraper_result)
                
                # Execute any remaining planned tools (excluding fact_csv and scraper already handled)
                remaining_tools = [t for t in tools if t not in ["fact_csv"]]
                if remaining_tools:
                    remaining_results = await self._execute_concurrent_tools(remaining_tools, params)
                    processed_results.extend(remaining_results)
            else:
                logger.info("CSV hit found; enrichment disabled by configuration")
            
            # Persist tool results for downstream aggregation/LLM
            state["tool_results"] = [asdict(r) for r in processed_results]
            
        except Exception as e:
            logger.error(f"Error in tool execution: {str(e)}")
            state["errors"].append(f"Tool execution error: {str(e)}")
        
        return state
    
    async def _execute_coordinated_workflow(self, tools: List[str], params: Dict[str, Any], state: QueryState) -> List[ToolResult]:
        """
        Execute coordinated workflow where fact retriever provides URLs to scraper
        """
        processed_results = []
        fact_csv_result = None
        
        try:
            # Step 1: Execute fact_csv to get company data and URLs
            if "fact_csv" in tools:
                logger.info("Step 1: Executing fact_csv to get company data and URLs")
                fact_csv_result = await self._execute_single_tool_direct("fact_csv", params.get("fact_csv", {}))
                processed_results.append(fact_csv_result)
                
                # Check if fact_csv provided website URLs
                if (fact_csv_result.status == "success" and 
                    "website_urls" in fact_csv_result.data.get("data", {})):
                    
                    website_urls = fact_csv_result.data["data"]["website_urls"]
                    logger.info(f"Fact retriever provided {len(website_urls)} website URLs for scraping")
                    
                    # Step 2: Execute scraper with URLs from fact_csv
                    if "scraper" in tools and website_urls:
                        logger.info("Step 2: Executing scraper with URLs from fact_csv")
                        
                        # Enhance scraper params with CSV data
                        scraper_params = params.get("scraper", {}).copy()
                        scraper_params["csv_urls"] = website_urls
                        
                        # Use semantic intent from router plan instead of pattern-based detection
                        plan = state.get("plan", {})
                        semantic_intent = plan.get("intent", "search")
                        
                        # Map semantic intents to scraper-specific intents
                        intent_mapping = {
                            "analyze": "financial",  # Analysis queries often want financial data
                            "compare": "financial",  # Comparison queries often compare financial metrics
                            "search": "about",       # Search queries often want general company info
                            "summarize": "about"     # Summary queries want overview information
                        }
                        
                        # Use mapped intent or fall back to pattern-based detection
                        scraper_intent = intent_mapping.get(semantic_intent, "general")
                        
                        # Refine intent based on query content if needed
                        query_lower = state.get("query", "").lower()
                        if any(word in query_lower for word in ["financial", "revenue", "profit", "earnings", "growth"]):
                            scraper_intent = "financial"
                        elif any(word in query_lower for word in ["team", "leadership", "management", "founder", "ceo"]):
                            scraper_intent = "team"
                        elif any(word in query_lower for word in ["product", "service", "solution", "offering"]):
                            scraper_intent = "products"
                        elif any(word in query_lower for word in ["news", "press", "announcement", "recent"]):
                            scraper_intent = "news"
                        
                        scraper_params["query_intent"] = scraper_intent
                        scraper_params["semantic_intent"] = semantic_intent  # Keep original semantic intent
                        scraper_params["intent_confidence"] = plan.get("confidence", 0.5)
                        
                        scraper_result = await self._execute_single_tool_direct("scraper", scraper_params)
                        processed_results.append(scraper_result)
                    else:
                        logger.warning("No website URLs available for scraping or scraper not in tools")
                else:
                    logger.warning("Fact retriever did not provide website URLs")
            
            # Execute remaining tools concurrently
            remaining_tools = [tool for tool in tools if tool not in ["fact_csv", "scraper"]]
            if remaining_tools:
                logger.info(f"Executing remaining tools concurrently: {remaining_tools}")
                remaining_results = await self._execute_concurrent_tools(remaining_tools, params)
                processed_results.extend(remaining_results)
            
        except Exception as e:
            logger.error(f"Error in coordinated workflow: {str(e)}")
            # Add error result
            processed_results.append(ToolResult(
                tool_name="coordinated_workflow",
                status="error",
                data={},
                execution_time=0.0,
                error_message=f"Coordinated workflow error: {str(e)}",
                confidence_score=0.0,
                timestamp=datetime.now()
            ))
        
        return processed_results
    
    async def _execute_concurrent_tools(self, tools: List[str], params: Dict[str, Any]) -> List[ToolResult]:
        """
        Execute tools concurrently with rate limiting
        """
        # Execute tools concurrently with semaphore for rate limiting
        semaphore = asyncio.Semaphore(self.max_concurrent_tools)
        tasks = []
        
        for tool in tools:
            task = self._execute_single_tool(tool, params.get(tool, {}), semaphore)
            tasks.append(task)
        
        # Wait for all tools to complete
        tool_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(tool_results):
            if isinstance(result, Exception):
                logger.error(f"Tool {tools[i]} failed: {str(result)}")
                processed_results.append(ToolResult(
                    tool_name=tools[i],
                    status="error",
                    data={},
                    execution_time=0.0,
                    error_message=str(result),
                    confidence_score=0.0,
                    timestamp=datetime.now()
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _execute_single_tool_direct(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """
        Execute a single tool directly without semaphore (for coordinated workflows)
        """
        start_time = datetime.now()
        
        try:
            logger.debug(f"Executing tool: {tool_name}")
            
            # Execute tool with timeout
            if tool_name == "fact_csv":
                result = await asyncio.wait_for(
                    self._call_fact_retriever(params),
                    timeout=self.tool_timeout
                )
            elif tool_name == "scraper":
                result = await asyncio.wait_for(
                    self._call_scraper(params),
                    timeout=self.tool_timeout * 2  # Give scraper more time
                )
            elif tool_name == "vector_query":
                result = await asyncio.wait_for(
                    self._call_vector_query(params),
                    timeout=self.tool_timeout
                )
            elif tool_name == "haystack_rag":
                result = await asyncio.wait_for(
                    self._call_haystack_rag(params),
                    timeout=self.tool_timeout
                )
            else:
                raise Exception(f"Unknown tool: {tool_name}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ToolResult(
                tool_name=tool_name,
                status="success",
                data=result,
                execution_time=execution_time,
                error_message=None,
                confidence_score=result.get("confidence", 0.8),
                timestamp=start_time
            )
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ToolResult(
                tool_name=tool_name,
                status="error",
                data={},
                execution_time=execution_time,
                error_message=f"Tool execution timeout after {self.tool_timeout}s",
                confidence_score=0.0,
                timestamp=start_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ToolResult(
                tool_name=tool_name,
                status="error",
                data={},
                execution_time=execution_time,
                error_message=str(e),
                confidence_score=0.0,
                timestamp=start_time
            )
    
    async def _execute_single_tool(self, tool_name: str, params: Dict[str, Any], semaphore: asyncio.Semaphore) -> ToolResult:
        """
        Execute a single tool with timeout and error handling
        """
        async with semaphore:
            start_time = datetime.now()
            
            try:
                logger.debug(f"Executing tool: {tool_name}")
                
                # Execute tool with timeout
                if tool_name == "fact_csv":
                    result = await asyncio.wait_for(
                        self._call_fact_retriever(params),
                        timeout=self.tool_timeout
                    )
                elif tool_name == "scraper":
                    result = await asyncio.wait_for(
                        self._call_scraper(params),
                        timeout=self.tool_timeout
                    )
                elif tool_name == "vector_query":
                    result = await asyncio.wait_for(
                        self._call_vector_query(params),
                        timeout=self.tool_timeout
                    )
                elif tool_name == "haystack_rag":
                    result = await asyncio.wait_for(
                        self._call_haystack_rag(params),
                        timeout=self.tool_timeout
                    )
                else:
                    raise Exception(f"Unknown tool: {tool_name}")
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return ToolResult(
                    tool_name=tool_name,
                    status="success",
                    data=result,
                    execution_time=execution_time,
                    error_message=None,
                    confidence_score=result.get("confidence", 0.8),
                    timestamp=start_time
                )
                
            except asyncio.TimeoutError:
                execution_time = (datetime.now() - start_time).total_seconds()
                return ToolResult(
                    tool_name=tool_name,
                    status="error",
                    data={},
                    execution_time=execution_time,
                    error_message=f"Tool execution timeout after {self.tool_timeout}s",
                    confidence_score=0.0,
                    timestamp=start_time
                )
                
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                return ToolResult(
                    tool_name=tool_name,
                    status="error",
                    data={},
                    execution_time=execution_time,
                    error_message=str(e),
                    confidence_score=0.0,
                    timestamp=start_time
                )
    
    async def _aggregate_results(self, state: QueryState) -> QueryState:
        """
        Aggregate and process tool results
        """
        try:
            logger.info(f"Aggregating results for dispatch {state['dispatch_id']}")
            
            if self.aggregator:
                # Combine tool results with RAG context for aggregation
                all_results = state["tool_results"].copy()
                
                # Add RAG context as tool results for aggregation
                for rag_result in state.get("rag_context", []):
                    all_results.append(rag_result)
                
                # Use enhanced aggregator with plan context
                aggregated_context = await self.aggregator.aggregate_results(
                    all_results,
                    state["plan"]
                )
                state["aggregated_context"] = aggregated_context
            else:
                # Simple aggregation fallback
                successful_results = [
                    result for result in state["tool_results"] 
                    if result["status"] == "success"
                ]
                
                state["aggregated_context"] = successful_results
                logger.info(f"Aggregated {len(successful_results)} successful tool results")
            
        except Exception as e:
            logger.error(f"Error in result aggregation: {str(e)}")
            state["errors"].append(f"Aggregation error: {str(e)}")
        
        return state
    
    async def _generate_response(self, state: QueryState) -> QueryState:
        """
        Generate final response using LLM
        """
        try:
            logger.info(f"Generating response for dispatch {state['dispatch_id']}")
            
            # Early exit if final_result already set to a terminal state (e.g., not_found)
            if state.get("final_result") and state["final_result"].get("status") == "not_found":
                logger.info("Final result already set to not_found; skipping LLM generation")
                return state
            
            if self.llm_client:
                # Build prompt
                prompt = self._build_prompt(state["query"], state["aggregated_context"], state["plan"])
                
                # Get LLM response
                response = await self.llm_client.generate_response(prompt)
                
                if response.status == "success":
                    state["llm_response"] = response.content
                    
                    # Format final result
                    state["final_result"] = self._format_response(
                        state["dispatch_id"],
                        state["query"],
                        response,
                        state["aggregated_context"],
                        state["execution_metadata"]
                    )
                else:
                    raise Exception(f"LLM response failed: {response.status}")
            else:
                # Enhanced fallback response that properly formats tool results
                state["llm_response"] = "No LLM client available"
                
                # Generate intelligent fallback response based on tool results
                fallback_verdict = self._generate_fallback_verdict(
                    state["query"], 
                    state["aggregated_context"], 
                    state["plan"]
                )
                
                state["final_result"] = {
                    "dispatch_id": state["dispatch_id"],
                    "status": "completed",
                    "result": {
                        "verdict": fallback_verdict,
                        "tool_results": state["aggregated_context"],
                        "confidence": {"score": 0.5}
                    }
                }
                logger.warning("No LLM client available, using enhanced fallback response")
            
        except Exception as e:
            logger.error(f"Error in response generation: {str(e)}")
            state["errors"].append(f"Response generation error: {str(e)}")
        
        return state
    
    async def _handle_errors(self, state: QueryState) -> QueryState:
        """
        Enhanced error handling with RAG system fallback strategies
        """
        logger.warning(f"Handling errors for dispatch {state['dispatch_id']}: {state['errors']}")
        
        # Categorize errors
        rag_errors = [e for e in state["errors"] if "rag" in e.lower() or "haystack" in e.lower()]
        tool_errors = [e for e in state["errors"] if "tool" in e.lower()]
        other_errors = [e for e in state["errors"] if e not in rag_errors and e not in tool_errors]
        
        # Implement RAG fallback strategies
        if rag_errors:
            logger.info("Implementing RAG fallback strategies")
            
            # Fallback 1: Disable RAG and continue with other tools
            if state["retry_count"] == 0:
                state["plan"]["disable_rag"] = True
                logger.info("Disabling RAG for this query, continuing with other tools")
                
                # Remove RAG from tool list if present
                tools = state["plan"].get("tools", [])
                if "haystack_rag" in tools:
                    tools.remove("haystack_rag")
                    state["plan"]["tools"] = tools
                
                # Clear RAG errors for retry
                state["errors"] = [e for e in state["errors"] if e not in rag_errors]
                state["retry_count"] += 1
                return state
            
            # Fallback 2: Use simplified vector search
            elif state["retry_count"] == 1:
                logger.info("Attempting simplified vector search fallback")
                
                # Modify plan to use basic vector query instead of RAG
                tools = state["plan"].get("tools", [])
                if "haystack_rag" in tools:
                    tools[tools.index("haystack_rag")] = "vector_query"
                    state["plan"]["tools"] = tools
                    state["plan"]["params"]["vector_query"] = {
                        "query": state["query"],
                        "top_k": 5
                    }
                
                state["errors"] = [e for e in state["errors"] if e not in rag_errors]
                state["retry_count"] += 1
                return state
        
        # Standard error recovery for other errors
        if state["retry_count"] < self.max_retries:
            # Clear transient errors
            transient_errors = ["timeout", "network", "connection", "temporary"]
            remaining_errors = []
            
            for error in state["errors"]:
                if not any(keyword in error.lower() for keyword in transient_errors):
                    remaining_errors.append(error)
            
            # If we cleared some errors, attempt retry
            if len(remaining_errors) < len(state["errors"]):
                state["errors"] = remaining_errors
                state["retry_count"] += 1
                logger.info(f"Attempting error recovery, retry {state['retry_count']}/{self.max_retries}")
                return state
        
        # If we have partial results, continue with degraded functionality
        successful_results = [r for r in state["tool_results"] if r.get("status") == "success"]
        rag_context = state.get("rag_context", [])
        
        if successful_results or rag_context:
            logger.info(f"Continuing with partial results: {len(successful_results)} tool results, {len(rag_context)} RAG results")
            
            # Clear non-critical errors and continue
            critical_errors = [e for e in state["errors"] if "critical" in e.lower() or "fatal" in e.lower()]
            state["errors"] = critical_errors
            
            if not critical_errors:
                # Continue to aggregation with partial results
                return state
        
        logger.error(f"Error recovery failed for dispatch {state['dispatch_id']}")
        return state
    
    async def _rollback(self, state: QueryState) -> QueryState:
        """
        Rollback and provide error response
        """
        logger.error(f"Rolling back workflow for dispatch {state['dispatch_id']}")
        
        execution_time = 0.0
        if "start_time" in state["execution_metadata"]:
            execution_time = (datetime.now() - state["execution_metadata"]["start_time"]).total_seconds()
        
        state["final_result"] = {
            "dispatch_id": state["dispatch_id"],
            "status": "error",
            "errors": state["errors"],
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "partial_results": state.get("aggregated_context", [])
        }
        
        return state
    
    async def _retrieve_rag_context(self, state: QueryState) -> QueryState:
        """
        Retrieve RAG context step in the query processing workflow
        """
        try:
            logger.info(f"Retrieving RAG context for dispatch {state['dispatch_id']}")
            
            query = state["query"]
            plan = state["plan"]
            
            # Determine RAG operation based on query intent
            intent = plan.get("intent", "search")
            entities = plan.get("entities", [])
            
            # Configure RAG parameters
            rag_params = {
                "query": query,
                "top_k": 5,
                "operation": "search"  # Default operation
            }
            
            # Adjust parameters based on intent
            if intent == "compare" and entities:
                rag_params["operation"] = "similar_companies"
                rag_params["company_description"] = query
                rag_params["top_k"] = 10
            elif intent in ["analyze", "research"]:
                rag_params["operation"] = "rag_response"
                rag_params["top_k"] = 7
            
            # Add entity filters if available
            if entities:
                rag_params["filters"] = {"entities": entities}
            
            # Execute RAG retrieval
            rag_result = await self._call_haystack_rag(rag_params)
            
            # Store RAG context in state
            if "rag_context" not in state:
                state["rag_context"] = []
            
            state["rag_context"].append(rag_result)
            
            # Update plan to include RAG-informed tool selection
            if rag_result.get("confidence", 0) > 0.7:
                # RAG provided good context, adjust tool priorities
                current_tools = plan.get("tools", [])
                if "haystack_rag" not in current_tools:
                    current_tools.insert(0, "haystack_rag")  # Prioritize RAG
                    plan["tools"] = current_tools
                    plan["params"]["haystack_rag"] = rag_params
            
            logger.info(f"RAG context retrieved successfully with confidence {rag_result.get('confidence', 0)}")
            
        except Exception as e:
            logger.error(f"Error in RAG context retrieval: {str(e)}")
            state["errors"].append(f"RAG context retrieval error: {str(e)}")
        
        return state
    
    # Conditional edge functions
    def _should_use_rag(self, state: QueryState) -> str:
        """Determine if RAG context retrieval should be used"""
        plan = state.get("plan", {})
        intent = plan.get("intent", "")
        query = state.get("query", "")
        
        # Use RAG for semantic search queries, company research, and comparisons
        if intent in ["search", "compare", "analyze", "research"]:
            return "use_rag"
        
        # Use RAG for queries that mention companies or business terms
        business_keywords = ["company", "business", "industry", "revenue", "employees", "market", "competitor"]
        if any(keyword in query.lower() for keyword in business_keywords):
            return "use_rag"
        
        # Skip RAG for simple factual queries or when explicitly disabled
        if intent in ["fact", "simple"] or plan.get("disable_rag", False):
            return "skip_rag"
        
        # Default to using RAG
        return "use_rag"
    
    def _rag_retrieval_complete(self, state: QueryState) -> str:
        """Determine if RAG retrieval completed successfully"""
        if state["errors"]:
            # Check if RAG errors are critical
            rag_errors = [e for e in state["errors"] if "rag" in e.lower()]
            if rag_errors and len(rag_errors) == len(state["errors"]):
                # Only RAG errors, continue with other tools
                logger.warning("RAG retrieval failed, continuing with other tools")
                state["errors"] = []  # Clear RAG-only errors
                return "continue"
            return "error"
        return "continue"
    
    def _should_retry_tools(self, state: QueryState) -> str:
        """Determine if tool execution should retry"""
        if state["errors"]:
            if state["retry_count"] < self.max_retries:
                # Check if we have any successful results
                successful_results = [r for r in state["tool_results"] if r.get("status") == "success"]
                if not successful_results:
                    return "retry"
            return "error"
        return "continue"
    
    def _should_complete(self, state: QueryState) -> str:
        """Determine if workflow should complete or handle errors"""
        if state["errors"] or not state.get("final_result"):
            return "error"
        return "complete"
    
    # Tool execution methods with actual implementations
    async def _call_fact_retriever(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call fact retriever tool with CSV-driven data fetching"""
        try:
            # Import here to avoid circular imports
            from workers.fact_retriever_worker import FactRetrieverWorker
            
            # Initialize fact retriever worker
            fact_worker = FactRetrieverWorker()
            
            # Extract parameters
            entities = params.get("entities", [])
            fields = params.get("fields", None)
            operation = params.get("operation", "get_facts")
            
            results = []
            
            if operation == "search":
                # Search companies based on query
                query = params.get("query", "")
                limit = params.get("limit", 10)
                search_results = await fact_worker.search_companies(query, limit)
                results = search_results
                
            elif operation == "industry_filter":
                # Get companies by industry
                industry = params.get("industry", "")
                limit = params.get("limit", 10)
                industry_results = await fact_worker.get_companies_by_industry(industry, limit)
                results = industry_results
                
            elif operation == "revenue_range":
                # Get companies by revenue range
                min_revenue = params.get("min_revenue", 0)
                max_revenue = params.get("max_revenue", float('inf'))
                revenue_results = await fact_worker.get_companies_by_revenue_range(min_revenue, max_revenue)
                results = revenue_results
                
            elif operation == "employee_range":
                # Get companies by employee count
                min_employees = params.get("min_employees", 0)
                max_employees = params.get("max_employees", 10000)
                employee_results = await fact_worker.get_companies_by_employee_count(min_employees, max_employees)
                results = employee_results
                
            else:
                # Default: get facts for specific entities
                if entities:
                    for entity in entities:
                        fact_result = await fact_worker.get_facts(entity, fields)
                        if "error" not in fact_result:
                            results.append(fact_result)
                else:
                    # If no entities specified, get available companies
                    available_companies = await fact_worker.get_available_companies()
                    results = [{"available_companies": available_companies[:20]}]  # Limit to first 20
            
            # Extract website URLs for potential scraping coordination, with sanitization
            def sanitize_url(raw: str) -> str:
                if not raw:
                    return ""
                url = str(raw).strip()
                if url.startswith("@"):  # remove leading tags like '@https://...'
                    url = url[1:].strip()
                # Prepend scheme if missing
                if not url.lower().startswith(("http://", "https://")):
                    url = "https://" + url.lstrip("/")
                # Basic validation: ensure netloc exists
                parsed = urlparse(url)
                if not parsed.netloc:
                    return ""
                return url
            
            website_urls = []
            for result in results:
                if isinstance(result, dict):
                    # Handle different result formats and field variants
                    raw_website = (
                        result.get("Website") or
                        result.get("Website ") or
                        result.get("website") or
                        result.get("website_url")
                    )
                    company_name = result.get("entity", result.get("Company Name", "Unknown"))
                    cleaned_url = sanitize_url(raw_website) if raw_website else ""
                    if cleaned_url:
                        website_urls.append({
                            "company": company_name,
                            "url": cleaned_url,
                            "industry": result.get("Industry", result.get("Industry ", "")),
                            "revenue": result.get("Revenue", "")
                        })
            
            return {
                "tool": "fact_csv",
                "data": {
                    "results": results,
                    "website_urls": website_urls,  # For scraper coordination
                    "operation": operation,
                    "total_results": len(results)
                },
                "confidence": 0.9 if results else 0.3
            }
            
        except Exception as e:
            logger.error(f"Error calling fact retriever: {str(e)}")
            return {
                "tool": "fact_csv",
                "data": {"error": str(e), "results": []},
                "confidence": 0.0
            }
    
    async def _call_scraper(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call scraper tool with semantic intent-based content extraction and CSV coordination"""
        try:
            # Import here to avoid circular imports
            from tools.scraper import ScraperTool, setup_windows_event_loop
            
            # Ensure Windows compatibility
            setup_windows_event_loop()
            
            # Initialize scraper
            scraper = ScraperTool(timeout=30, max_retries=2, delay_between_requests=1.0)
            
            try:
                # Extract parameters with semantic intent support
                urls = params.get("urls", [])
                query_intent = params.get("query_intent", "general")
                semantic_intent = params.get("semantic_intent", None)
                intent_confidence = params.get("intent_confidence", 0.5)
                company_context = params.get("company_context", {})
                
                # If no URLs provided, check for CSV coordination data
                if not urls and "csv_urls" in params:
                    csv_urls = params["csv_urls"]
                    urls = [item["url"] for item in csv_urls if item.get("url")]
                    company_context = {item["url"]: item for item in csv_urls}
                
                if not urls:
                    return {
                        "tool": "scraper",
                        "data": {"error": "No URLs provided for scraping", "results": []},
                        "confidence": 0.0
                    }
                
                # Generate intelligent selectors based on query intent
                selectors = self._generate_intelligent_selectors(query_intent)
                
                results = []
                
                # Scrape URLs with intelligent content extraction
                for url in urls[:5]:  # Limit to 5 URLs to avoid overload
                    try:
                        semantic_info = f" (semantic: {semantic_intent}, confidence: {intent_confidence:.2f})" if semantic_intent else ""
                        logger.info(f"Scraping URL with intent '{query_intent}'{semantic_info}: {url}")
                        
                        # Get company context for this URL
                        context = company_context.get(url, {})
                        company_name = context.get("company", "Unknown")
                        
                        # Scrape with intelligent selectors
                        scrape_result = await scraper.scrape_url(url, selectors)
                        
                        if scrape_result["metadata"]["status"] == "success":
                            # Apply content relevance filtering
                            filtered_content = self._filter_business_relevant_content(
                                scrape_result["content"], 
                                query_intent,
                                context
                            )
                            
                            # Enhance with company context
                            enhanced_result = {
                                "company": company_name,
                                "url": url,
                                "content": filtered_content,
                                "financial_data": scrape_result["financial_data"],
                                "business_metrics": scrape_result["business_metrics"],
                                "query_intent": query_intent,
                                "semantic_intent": semantic_intent,
                                "intent_confidence": intent_confidence,
                                "selectors_used": selectors,
                                "company_context": context,
                                "metadata": scrape_result["metadata"]
                            }
                            
                            results.append(enhanced_result)
                            logger.info(f"Successfully scraped {company_name}: {len(filtered_content)} chars")
                            
                        else:
                            # Handle scraping failure with fallback
                            error_result = {
                                "company": company_name,
                                "url": url,
                                "content": "",
                                "error": scrape_result["metadata"].get("error", "Unknown error"),
                                "query_intent": query_intent,
                                "semantic_intent": semantic_intent,
                                "intent_confidence": intent_confidence,
                                "company_context": context,
                                "metadata": scrape_result["metadata"]
                            }
                            results.append(error_result)
                            logger.warning(f"Failed to scrape {company_name}: {error_result['error']}")
                        
                        # Add delay between requests
                        await asyncio.sleep(1.0)
                        
                    except Exception as url_error:
                        logger.error(f"Error scraping URL {url}: {str(url_error)}")
                        results.append({
                            "company": company_context.get(url, {}).get("company", "Unknown"),
                            "url": url,
                            "content": "",
                            "error": str(url_error),
                            "query_intent": query_intent,
                            "metadata": {"status": "error", "error": str(url_error)}
                        })
                
                # Calculate overall confidence based on success rate
                successful_scrapes = [r for r in results if r.get("content") and not r.get("error")]
                confidence = len(successful_scrapes) / len(results) if results else 0.0
                
                return {
                    "tool": "scraper",
                    "data": {
                        "results": results,
                        "query_intent": query_intent,
                        "semantic_intent": semantic_intent,
                        "intent_confidence": intent_confidence,
                        "total_urls": len(urls),
                        "successful_scrapes": len(successful_scrapes),
                        "selectors_used": selectors
                    },
                    "confidence": confidence
                }
                
            finally:
                await scraper.close()
                
        except Exception as e:
            logger.error(f"Error calling scraper: {str(e)}")
            return {
                "tool": "scraper",
                "data": {"error": str(e), "results": []},
                "confidence": 0.0
            }
    
    async def _call_vector_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call vector query tool"""
        # TODO: Implement actual vector query call
        await asyncio.sleep(0.15)  # Simulate work
        return {
            "tool": "vector_query",
            "data": {"params": params},
            "confidence": 0.9
        }
    
    async def _call_haystack_rag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call Haystack RAG tool with actual implementation"""
        try:
            # Import here to avoid circular imports
            from tools.haystack_rag import HaystackRAGSystem
            from config.config_manager import ConfigManager
            
            # Get configuration
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            # Initialize Haystack RAG system
            rag_system = HaystackRAGSystem(
                embedding_model=config.haystack.embedding_model,
                document_store_type=config.haystack.document_store_type,
                qdrant_url=getattr(config.haystack, 'qdrant_url', None),
                qdrant_api_key=getattr(config.haystack, 'qdrant_api_key', None),
                collection_name=config.haystack.collection_name
            )
            
            # Determine the type of RAG operation
            operation = params.get("operation", "search")
            query = params.get("query", "")
            top_k = params.get("top_k", 5)
            filters = params.get("filters")
            
            if operation == "search":
                result = await rag_system.search(query, top_k, filters)
            elif operation == "rag_response":
                result = await rag_system.generate_rag_response(query, top_k, filters)
            elif operation == "similar_companies":
                company_description = params.get("company_description", query)
                industry_filter = params.get("industry_filter")
                result = await rag_system.get_similar_companies(company_description, top_k, industry_filter)
            else:
                # Default to search
                result = await rag_system.search(query, top_k, filters)
            
            return {
                "tool": "haystack_rag",
                "data": result,
                "confidence": 0.9 if result.get("status") == "success" else 0.3,
                "operation": operation
            }
            
        except Exception as e:
            logger.error(f"Error calling Haystack RAG: {str(e)}")
            return {
                "tool": "haystack_rag",
                "data": {"status": "error", "error": str(e)},
                "confidence": 0.0,
                "operation": params.get("operation", "search")
            }
    
    def _build_prompt(self, query: str, context: List[Dict[str, Any]], plan: Dict[str, Any]) -> str:
        """Build prompt for LLM"""
        prompt_parts = [
            f"Query: {query}",
            f"Intent: {plan.get('intent', 'unknown')}",
            f"Context from {len(context)} tools:",
        ]
        
        for i, ctx in enumerate(context):
            try:
                # Convert datetime objects to strings for JSON serialization
                ctx_copy = self._serialize_for_json(ctx)
                prompt_parts.append(f"Tool {i+1}: {json.dumps(ctx_copy, indent=2)}")
            except Exception as e:
                prompt_parts.append(f"Tool {i+1}: {str(ctx)}")
        
        return "\n\n".join(prompt_parts)
    
    def _generate_intelligent_selectors(self, query_intent: str) -> List[str]:
        """
        Generate intelligent CSS selectors based on query intent for targeted content extraction
        """
        base_selectors = [
            # Common content areas
            'main', 'article', '.content', '#content', '.main-content',
            # Text content
            'p', 'div', 'section'
        ]
        
        intent_selectors = {
            "financial": [
                # Financial data selectors
                '[class*="financial"]', '[id*="financial"]',
                '[class*="revenue"]', '[id*="revenue"]', 
                '[class*="profit"]', '[id*="profit"]',
                '[class*="earnings"]', '[id*="earnings"]',
                '[class*="investor"]', '[id*="investor"]',
                '.financial-data', '.revenue-info', '.profit-margin',
                # Common financial page patterns
                '[href*="investor"]', '[href*="financial"]',
                'h1', 'h2', 'h3', 'h4'  # Will filter by content later
            ],
            "about": [
                # About/company info selectors
                '[class*="about"]', '[id*="about"]',
                '[class*="company"]', '[id*="company"]',
                '[class*="mission"]', '[id*="mission"]',
                '[class*="vision"]', '[id*="vision"]',
                '[class*="history"]', '[id*="history"]',
                '.about-us', '.company-info', '.mission-statement',
                # Common about page patterns
                '[href*="about"]', '[href*="company"]',
                'h1', 'h2', 'h3', 'h4'  # Will filter by content later
            ],
            "news": [
                # News/press selectors
                '[class*="news"]', '[id*="news"]',
                '[class*="press"]', '[id*="press"]',
                '[class*="blog"]', '[id*="blog"]',
                '[class*="announcement"]', '[id*="announcement"]',
                '.news-item', '.press-release', '.blog-post',
                # Common news page patterns
                '[href*="news"]', '[href*="press"]', '[href*="blog"]',
                'h1', 'h2', 'h3', 'h4'  # Will filter by content later
            ],
            "team": [
                # Team/leadership selectors
                '[class*="team"]', '[id*="team"]',
                '[class*="leadership"]', '[id*="leadership"]',
                '[class*="management"]', '[id*="management"]',
                '[class*="executive"]', '[id*="executive"]',
                '[class*="founder"]', '[id*="founder"]',
                '.team-member', '.leadership-team', '.executive-team',
                # Common team page patterns
                '[href*="team"]', '[href*="leadership"]',
                'h1', 'h2', 'h3', 'h4'  # Will filter by content later
            ],
            "products": [
                # Products/services selectors
                '[class*="product"]', '[id*="product"]',
                '[class*="service"]', '[id*="service"]',
                '[class*="solution"]', '[id*="solution"]',
                '[class*="offering"]', '[id*="offering"]',
                '.product-info', '.service-description', '.solution-overview',
                # Common product page patterns
                '[href*="product"]', '[href*="service"]',
                'h1', 'h2', 'h3', 'h4'  # Will filter by content later
            ]
        }
        
        # Combine base selectors with intent-specific ones
        selectors = base_selectors.copy()
        
        if query_intent in intent_selectors:
            selectors.extend(intent_selectors[query_intent])
        else:
            # For general queries, include a mix of common business sections
            selectors.extend(intent_selectors["about"][:3])
            selectors.extend(intent_selectors["products"][:3])
        
        return selectors
    
    def _filter_business_relevant_content(self, content: str, query_intent: str, company_context: Dict[str, Any]) -> str:
        """
        Filter content to extract only business-relevant information, 
        skipping navigation, ads, footers, etc.
        """
        if not content:
            return ""
        
        # Split content into lines for filtering
        lines = content.split('\n')
        filtered_lines = []
        
        # Common non-business content patterns to skip
        skip_patterns = [
            # Navigation and UI elements
            r'^(home|about|contact|login|register|sign up|sign in)$',
            r'^(menu|navigation|nav|sidebar)$',
            r'^(search|filter|sort by)$',
            
            # Footer and legal content
            r'^(copyright|©|\(c\)|all rights reserved).*',
            r'^(privacy policy|terms of service|cookie policy).*',
            r'^(follow us|social media|connect with us).*',
            
            # Ads and promotional content
            r'^(advertisement|sponsored|promoted).*',
            r'^(click here|learn more|read more|view all)$',
            r'^(subscribe|newsletter|email updates).*',
            
            # Generic UI text
            r'^(loading|please wait|error|404|page not found).*',
            r'^(back to top|scroll to top|return to).*',
            
            # Short non-informative lines
            r'^.{1,10}$',  # Very short lines
            r'^[^a-zA-Z]*$'  # Lines with no letters
        ]
        
        # Business-relevant keywords to prioritize
        business_keywords = [
            # Company information
            'company', 'business', 'organization', 'corporation', 'enterprise',
            'founded', 'established', 'headquarters', 'location', 'industry',
            
            # Financial terms
            'revenue', 'profit', 'earnings', 'financial', 'growth', 'investment',
            'funding', 'valuation', 'market', 'sales', 'income',
            
            # Business operations
            'employees', 'team', 'staff', 'workforce', 'leadership', 'management',
            'products', 'services', 'solutions', 'offerings', 'customers', 'clients',
            
            # Performance metrics
            'performance', 'results', 'achievements', 'success', 'awards',
            'recognition', 'expansion', 'growth', 'development'
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip lines matching non-business patterns
            skip_line = False
            for pattern in skip_patterns:
                if re.match(pattern, line.lower()):
                    skip_line = True
                    break
            
            if skip_line:
                continue
            
            # Prioritize lines with business keywords
            line_lower = line.lower()
            has_business_content = any(keyword in line_lower for keyword in business_keywords)
            
            # Include lines that are substantial and potentially business-relevant
            if (len(line) > 20 and  # Substantial length
                (has_business_content or  # Contains business keywords
                 any(char.isalpha() for char in line) and  # Contains letters
                 len([word for word in line.split() if len(word) > 3]) >= 3)):  # Has meaningful words
                filtered_lines.append(line)
        
        # Join filtered content
        filtered_content = '\n'.join(filtered_lines)
        
        # Apply intent-specific filtering
        if query_intent == "financial":
            filtered_content = self._extract_financial_sections(filtered_content)
        elif query_intent == "about":
            filtered_content = self._extract_company_info_sections(filtered_content)
        elif query_intent == "team":
            filtered_content = self._extract_team_sections(filtered_content)
        
        # Limit content length to avoid overwhelming the LLM
        max_length = 3000  # Reasonable limit for LLM context
        if len(filtered_content) > max_length:
            # Truncate but try to end at a sentence boundary
            truncated = filtered_content[:max_length]
            last_period = truncated.rfind('.')
            if last_period > max_length * 0.8:  # If we can find a period in the last 20%
                filtered_content = truncated[:last_period + 1]
            else:
                filtered_content = truncated + "..."
        
        return filtered_content
    
    def _extract_financial_sections(self, content: str) -> str:
        """Extract sections likely to contain financial information"""
        financial_keywords = [
            'revenue', 'profit', 'earnings', 'financial', 'growth', 'investment',
            'funding', 'valuation', 'market cap', 'sales', 'income', 'ebitda',
            'margin', 'roi', 'quarterly', 'annual', 'fiscal', 'billion', 'million'
        ]
        
        lines = content.split('\n')
        financial_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in financial_keywords):
                financial_lines.append(line)
        
        return '\n'.join(financial_lines) if financial_lines else content
    
    def _extract_company_info_sections(self, content: str) -> str:
        """Extract sections likely to contain company information"""
        company_keywords = [
            'about', 'company', 'mission', 'vision', 'history', 'founded',
            'established', 'headquarters', 'leadership', 'team', 'culture',
            'values', 'purpose', 'story', 'background', 'overview'
        ]
        
        lines = content.split('\n')
        company_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in company_keywords):
                company_lines.append(line)
        
        return '\n'.join(company_lines) if company_lines else content
    
    def _extract_team_sections(self, content: str) -> str:
        """Extract sections likely to contain team/leadership information"""
        team_keywords = [
            'team', 'leadership', 'management', 'executive', 'founder', 'ceo',
            'president', 'director', 'manager', 'staff', 'employees', 'personnel',
            'board', 'advisory', 'key people', 'our team', 'leadership team'
        ]
        
        lines = content.split('\n')
        team_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in team_keywords):
                team_lines.append(line)
        
        return '\n'.join(team_lines) if team_lines else content

    def _generate_fallback_verdict(self, query: str, context: List[Dict[str, Any]], plan: Dict[str, Any]) -> str:
        """
        Generate intelligent fallback verdict when LLM is not available
        """
        try:
            # Extract information from tool results
            fact_csv_results = []
            vector_query_results = []
            scraper_results = []
            
            for result in context:
                if result.get("tool_name") == "fact_csv" and result.get("status") == "success":
                    if "data" in result and "data" in result["data"]:
                        fact_csv_results = result["data"]["data"].get("results", [])
                elif result.get("tool_name") == "vector_query" and result.get("status") == "success":
                    vector_query_results = result.get("data", {}).get("results", [])
                elif result.get("tool_name") == "scraper" and result.get("status") == "success":
                    scraper_results = result.get("data", {}).get("results", [])
            
            # Determine query intent and generate appropriate response
            query_lower = query.lower()
            intent = plan.get("intent", "search")
            
            # Generate response based on available results
            if fact_csv_results:
                # Format fact CSV results
                search_results = []
                for company in fact_csv_results:
                    company_name = company.get('entity', company.get('Company Name', 'Unknown'))
                    industry = company.get('Industry', company.get('Industry ', 'Unknown'))
                    revenue = company.get('Revenue', 'Unknown')
                    employees = company.get('Employees', 'Unknown')
                    website = company.get('Website', '')
                    
                    search_results.append({
                        "company_name": company_name,
                        "industry": industry,
                        "revenue": revenue,
                        "employees": employees,
                        "website": website
                    })
                
                # Determine if user wants "top" company
                if "top" in query_lower or "best" in query_lower or "highest" in query_lower:
                    # Sort by revenue (convert to numeric for comparison)
                    def parse_revenue(rev_str):
                        if not rev_str or rev_str == 'Unknown':
                            return 0
                        try:
                            # Handle formats like "10M", "11.7M", etc.
                            rev_clean = rev_str.replace('M', '').replace('$', '').replace(',', '')
                            return float(rev_clean) * 1000000
                        except:
                            return 0
                    
                    sorted_companies = sorted(search_results, key=lambda x: parse_revenue(x['revenue']), reverse=True)
                    top_company = sorted_companies[0] if sorted_companies else None
                    
                    if top_company:
                        summary = f"Found {len(search_results)} education companies. The top company by revenue is {top_company['company_name']} with {top_company['revenue']} in revenue."
                    else:
                        summary = f"Found {len(search_results)} education companies, but could not determine the top company by revenue."
                else:
                    # General search results
                    if "education" in query_lower:
                        summary = f"Found {len(search_results)} education companies in the database."
                    else:
                        summary = f"Found {len(search_results)} companies matching your search criteria."
                
                # Generate JSON response
                response_data = {
                    "search_results": search_results,
                    "summary": summary,
                    "total_results": len(search_results),
                    "confidence": {
                        "score": 0.8,
                        "factors": ["csv_data_available", "successful_tool_execution"]
                    }
                }
                
                return f"```json\n{json.dumps(response_data, indent=2)}\n```"
            
            else:
                # No results found
                if "education" in query_lower:
                    summary = "No education companies found in the database."
                else:
                    summary = "No companies found matching your search criteria."
                
                response_data = {
                    "search_results": [],
                    "summary": summary,
                    "total_results": 0,
                    "confidence": {
                        "score": 0.2,
                        "factors": ["no_results_found"]
                    }
                }
                
                return f"```json\n{json.dumps(response_data, indent=2)}\n```"
                
        except Exception as e:
            logger.error(f"Error generating fallback verdict: {str(e)}")
            # Ultimate fallback
            return f"```json\n{json.dumps({'search_results': [], 'summary': 'Error processing results', 'total_results': 0, 'confidence': {'score': 0.0, 'factors': ['processing_error']}}, indent=2)}\n```"

    def _serialize_for_json(self, obj):
        """Convert objects to JSON-serializable format"""
        if isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj
    
    def _format_response(self, dispatch_id: str, query: str, llm_response, 
                        context: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format final response"""
        execution_time = 0.0
        if "start_time" in metadata:
            execution_time = (datetime.now() - metadata["start_time"]).total_seconds()
        
        return {
            "dispatch_id": dispatch_id,
            "status": "completed",
            "result": {
                "verdict": llm_response.content if hasattr(llm_response, 'content') else str(llm_response),
                "tool_results": context,
                "confidence": {"score": getattr(llm_response, 'validation_result', {}).get('confidence', 0.8)},
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def get_dispatch_result(self, dispatch_id: str) -> Optional[Dict[str, Any]]:
        """Get dispatch result by ID"""
        return self.dispatch_results.get(dispatch_id)
    
    # Tool integration methods for direct access (used by simple_server.py)
    # Note: _call_fact_retriever is defined above in the main tool execution methods section
    
    async def _call_scraper(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call scraper with intelligent content extraction based on CSV URLs and query intent
        """
        try:
            from tools.scraper import ScraperTool, setup_windows_event_loop
            
            # Ensure Windows compatibility
            setup_windows_event_loop()
            
            # Initialize scraper if not already done
            if not hasattr(self, 'scraper'):
                self.scraper = ScraperTool()
            
            csv_urls = params.get("csv_urls", [])
            query_intent = params.get("query_intent", "general")
            selectors = params.get("selectors", ["/about", "/company"])
            timeout = params.get("timeout", 30)
            max_retries = params.get("max_retries", 2)
            
            if not csv_urls:
                return {
                    "tool": "scraper",
                    "data": {
                        "error": "No URLs provided for scraping",
                        "results": []
                    },
                    "confidence": 0.0
                }
            
            results = []
            
            # Process each company URL
            for url_info in csv_urls:
                company = url_info.get("company", "Unknown")
                base_url = url_info.get("url", "")
                
                if not base_url:
                    continue
                
                try:
                    logger.info(f"Scraping {company} website: {base_url}")
                    
                    # Determine target pages based on query intent
                    target_urls = [base_url]  # Always scrape main page
                    
                    # Add intent-specific pages
                    if query_intent == "financial":
                        target_urls.extend([
                            f"{base_url.rstrip('/')}/investors",
                            f"{base_url.rstrip('/')}/financials",
                            f"{base_url.rstrip('/')}/annual-report"
                        ])
                    elif query_intent == "about":
                        target_urls.extend([
                            f"{base_url.rstrip('/')}/about",
                            f"{base_url.rstrip('/')}/about-us",
                            f"{base_url.rstrip('/')}/company"
                        ])
                    elif query_intent == "team":
                        target_urls.extend([
                            f"{base_url.rstrip('/')}/team",
                            f"{base_url.rstrip('/')}/leadership",
                            f"{base_url.rstrip('/')}/management"
                        ])
                    elif query_intent == "products":
                        target_urls.extend([
                            f"{base_url.rstrip('/')}/products",
                            f"{base_url.rstrip('/')}/services",
                            f"{base_url.rstrip('/')}/solutions"
                        ])
                    
                    # Scrape target URLs
                    company_content = []
                    for url in target_urls[:3]:  # Limit to 3 URLs per company
                        try:
                            scraped_data = await self.scraper.scrape_url(
                                url, 
                                selectors=None,
                                timeout=timeout
                            )
                            
                            if scraped_data.get("metadata", {}).get("status") == "success" and scraped_data.get("content"):
                                # Apply intent-based content filtering
                                filtered_content = self._filter_content_by_intent(
                                    scraped_data["content"], 
                                    query_intent
                                )
                                
                                if filtered_content:
                                    company_content.append({
                                        "url": url,
                                        "content": filtered_content[:2000],  # Limit content length
                                        "title": scraped_data.get("metadata", {}).get("title", ""),
                                        "intent_match": query_intent
                                    })
                        except Exception as url_error:
                            logger.warning(f"Failed to scrape {url}: {str(url_error)}")
                            continue
                    
                    if company_content:
                        results.append({
                            "company": company,
                            "base_url": base_url,
                            "scraped_pages": company_content,
                            "query_intent": query_intent,
                            "pages_scraped": len(company_content)
                        })
                        logger.info(f"Successfully scraped {len(company_content)} pages for {company}")
                    else:
                        logger.warning(f"No content extracted for {company}")
                
                except Exception as company_error:
                    logger.error(f"Error scraping {company}: {str(company_error)}")
                    results.append({
                        "company": company,
                        "base_url": base_url,
                        "error": str(company_error),
                        "query_intent": query_intent
                    })
            
            logger.info(f"Scraper processed {len(csv_urls)} companies, got content for {len([r for r in results if 'scraped_pages' in r])}")
            
            return {
                "tool": "scraper",
                "data": {
                    "results": results,
                    "operation": "csv_driven_scraping",
                    "query_intent": query_intent,
                    "total_companies": len(csv_urls),
                    "successful_scrapes": len([r for r in results if 'scraped_pages' in r])
                },
                "confidence": 0.8 if results else 0.1
            }
            
        except Exception as e:
            logger.error(f"Error in scraper: {str(e)}")
            return {
                "tool": "scraper",
                "data": {
                    "error": str(e),
                    "results": []
                },
                "confidence": 0.0
            }
    
    async def _call_vector_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call vector query tool for semantic search
        """
        try:
            # This is a placeholder - vector query tool would need to be implemented
            query = params.get("query", "")
            top_k = params.get("top_k", 5)
            entities = params.get("entities", [])
            
            logger.info(f"Vector query called with query: {query}, entities: {entities}")
            
            # Mock response for now
            return {
                "tool": "vector_query",
                "data": {
                    "query": query,
                    "results": [],
                    "message": "Vector query tool not yet implemented"
                },
                "confidence": 0.0
            }
            
        except Exception as e:
            logger.error(f"Error in vector query: {str(e)}")
            return {
                "tool": "vector_query",
                "data": {
                    "error": str(e),
                    "results": []
                },
                "confidence": 0.0
            }
    
    async def _call_haystack_rag(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Haystack RAG system for advanced retrieval
        """
        try:
            from tools.haystack_rag import HaystackRAG
            
            # Initialize Haystack RAG if not already done
            if not hasattr(self, 'haystack_rag'):
                self.haystack_rag = HaystackRAG()
                await self.haystack_rag.initialize()
            
            query = params.get("query", "")
            operation = params.get("operation", "search")
            top_k = params.get("top_k", 5)
            
            logger.info(f"Haystack RAG called with operation: {operation}, query: {query}")
            
            if operation == "search":
                results = await self.haystack_rag.search(query, top_k=top_k)
            elif operation == "similar_companies":
                company_description = params.get("company_description", query)
                results = await self.haystack_rag.find_similar_companies(company_description, top_k=top_k)
            elif operation == "rag_response":
                results = await self.haystack_rag.get_rag_response(query, top_k=top_k)
            else:
                results = await self.haystack_rag.search(query, top_k=top_k)
            
            return {
                "tool": "haystack_rag",
                "data": {
                    "operation": operation,
                    "query": query,
                    "results": results,
                    "total_results": len(results) if isinstance(results, list) else 1
                },
                "confidence": 0.8 if results else 0.1
            }
            
        except Exception as e:
            logger.error(f"Error in Haystack RAG: {str(e)}")
            return {
                "tool": "haystack_rag",
                "data": {
                    "error": str(e),
                    "results": [],
                    "message": "Haystack RAG system error"
                },
                "confidence": 0.0
            }
    
    def _filter_content_by_intent(self, content: str, query_intent: str) -> str:
        """
        Filter content based on query intent to extract relevant sections
        """
        if not content:
            return ""
        
        try:
            if query_intent == "financial":
                return self._extract_financial_sections(content)
            elif query_intent == "about":
                return self._extract_company_info_sections(content)
            elif query_intent == "team":
                return self._extract_team_sections(content)
            elif query_intent == "products":
                return self._extract_product_sections(content)
            elif query_intent == "news":
                return self._extract_news_sections(content)
            else:
                # For general intent, return cleaned content with reasonable length
                return content[:2000] if len(content) > 2000 else content
                
        except Exception as e:
            logger.warning(f"Error filtering content by intent {query_intent}: {str(e)}")
            return content[:1000] if len(content) > 1000 else content
    
    def _extract_financial_sections(self, content: str) -> str:
        """Extract sections likely to contain financial information"""
        financial_keywords = [
            'revenue', 'profit', 'earnings', 'financial', 'income', 'sales',
            'growth', 'funding', 'investment', 'valuation', 'ipo', 'public',
            'quarterly', 'annual', 'report', 'balance', 'cash', 'debt',
            'margin', 'ebitda', 'roi', 'market cap', 'stock', 'dividend'
        ]
        
        lines = content.split('\n')
        financial_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in financial_keywords):
                financial_lines.append(line)
        
        return '\n'.join(financial_lines) if financial_lines else content[:1000]
    
    def _extract_company_info_sections(self, content: str) -> str:
        """Extract sections likely to contain company information"""
        company_keywords = [
            'about', 'company', 'mission', 'vision', 'history', 'founded',
            'established', 'headquarters', 'leadership', 'team', 'culture',
            'values', 'purpose', 'story', 'background', 'overview', 'who we are'
        ]
        
        lines = content.split('\n')
        company_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in company_keywords):
                company_lines.append(line)
        
        return '\n'.join(company_lines) if company_lines else content[:1000]
    
    def _extract_team_sections(self, content: str) -> str:
        """Extract sections likely to contain team/leadership information"""
        team_keywords = [
            'team', 'leadership', 'management', 'executive', 'founder', 'ceo',
            'president', 'director', 'manager', 'staff', 'employees', 'personnel',
            'board', 'advisory', 'key people', 'our team', 'leadership team',
            'meet the team', 'management team'
        ]
        
        lines = content.split('\n')
        team_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in team_keywords):
                team_lines.append(line)
        
        return '\n'.join(team_lines) if team_lines else content[:1000]
    
    def _extract_product_sections(self, content: str) -> str:
        """Extract sections likely to contain product/service information"""
        product_keywords = [
            'product', 'service', 'solution', 'offering', 'platform', 'software',
            'technology', 'feature', 'capability', 'tool', 'application', 'system',
            'what we do', 'our products', 'our services', 'solutions', 'portfolio'
        ]
        
        lines = content.split('\n')
        product_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in product_keywords):
                product_lines.append(line)
        
        return '\n'.join(product_lines) if product_lines else content[:1000]
    
    def _extract_news_sections(self, content: str) -> str:
        """Extract sections likely to contain news/press information"""
        news_keywords = [
            'news', 'press', 'announcement', 'release', 'update', 'launch',
            'partnership', 'acquisition', 'funding', 'expansion', 'milestone',
            'achievement', 'award', 'recognition', 'media', 'blog', 'article'
        ]
        
        lines = content.split('\n')
        news_lines = []
        
        for line in lines:
            if any(keyword in line.lower() for keyword in news_keywords):
                news_lines.append(line)
        
        return '\n'.join(news_lines) if news_lines else content[:1000]


# Legacy OrchestratorSupervisor wrapper for backward compatibility
class OrchestratorSupervisor:
    """
    Backward compatibility wrapper for the new LangGraph orchestrator
    """
    
    def __init__(self, router_client=None, llm_client=None, aggregator=None):
        self.langgraph_orchestrator = LangGraphOrchestrator(router_client, llm_client, aggregator)
    
    async def process_query(self, user_id: str, query: str, options: Dict[str, Any], messages: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Process query - delegates to LangGraph orchestrator"""
        return await self.langgraph_orchestrator.process_query(user_id, query, options, messages)
    
    def get_dispatch_result(self, dispatch_id: str) -> Optional[Dict[str, Any]]:
        """Get dispatch result by ID"""
        return self.langgraph_orchestrator.get_dispatch_result(dispatch_id) 