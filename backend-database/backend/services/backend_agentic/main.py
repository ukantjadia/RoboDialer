import os
import uuid
import json
import logging
import asyncio
import re
import threading
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
from flask_login import login_required, current_user

# Import your backend components
from .workers.fact_retriever_worker import FactRetrieverWorker
from .services.orchestrator.router_client import RouterClient
from .aggregator.prompt_builder import PromptBuilder
from .llm.deepseek_client import DeepSeekClient
from .aggregator.aggregator import Aggregator
from .load_faiss_and_rag import query_faiss_and_rag
from models.user_lead_drafts_model import UserLeadDraft

# Import context components
from .context.context_manager import ContextManager
from .context.session_store import SessionStore
from .context.models import ContextConfig
from .context.message_array_builder import MessageArrayBuilder

# Load environment variables and set up dedicated logger
load_dotenv()
from .agentic_logging import setup_agentic_logging, get_agentic_logger, AgenticLogContext

# Initialize dedicated agentic logging
setup_agentic_logging()
logger = get_agentic_logger('routes')

# Create blueprint
agentic_backend_bp = Blueprint('agentic_backend', __name__)

# --- Global Components ---
fact_retriever = FactRetrieverWorker()
router_client = RouterClient()
prompt_builder = PromptBuilder()
deepseek_client = DeepSeekClient()
aggregator = Aggregator()
context_config = ContextConfig(
    max_messages_per_session=int(os.getenv("CONTEXT_MAX_MESSAGES_PER_SESSION", "50")),
    max_tokens_per_session=int(os.getenv("CONTEXT_MAX_TOKENS_PER_SESSION", "20000")),
    session_timeout_minutes=int(os.getenv("CONTEXT_SESSION_TIMEOUT_MINUTES", "30")),
    cleanup_interval_minutes=int(os.getenv("CONTEXT_CLEANUP_INTERVAL_MINUTES", "5")),
    system_prompt=os.getenv("CONTEXT_SYSTEM_PROMPT", "You are a helpful AI assistant for lead generation and business analysis."),
    enable_token_management=os.getenv("CONTEXT_ENABLE_TOKEN_MANAGEMENT", "true").lower() == "true",
    truncation_strategy=os.getenv("CONTEXT_TRUNCATION_STRATEGY", "oldest_first"),
    max_sessions_per_user=int(os.getenv("CONTEXT_MAX_SESSIONS_PER_USER", "10"))
)
session_store = SessionStore(max_sessions=int(os.getenv("SESSION_STORE_MAX_SESSIONS", "1000")))
context_manager = ContextManager(session_store, context_config)
dispatch_results = {}

# --- Cancellation Management ---
stream_cancellation_flags = {}
stream_cancellation_lock = threading.Lock()

def set_stream_cancelled(session_id):
    with stream_cancellation_lock:
        stream_cancellation_flags[session_id] = True

def is_stream_cancelled(session_id):
    with stream_cancellation_lock:
        return stream_cancellation_flags.get(session_id, False)

def clear_stream_cancelled(session_id):
    with stream_cancellation_lock:
        if session_id in stream_cancellation_flags:
            del stream_cancellation_flags[session_id]

# --- Async Utilities ---
def run_async(coro):
    """Utility to run an async function in a sync Flask route."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- Synchronous Counterparts ---
def get_or_create_session_sync(user_id: str, session_id: Optional[str] = None):
    """Synchronous version of context_manager.get_or_create_session"""
    return asyncio.run(context_manager.get_or_create_session(user_id, session_id))

def get_conversation_array_sync(session_id: str):
    """Synchronous version of context_manager.get_conversation_array"""
    return asyncio.run(context_manager.get_conversation_array(session_id))

def add_user_message_sync(session_id: str, message: str):
    """Synchronous version of context_manager.add_user_message"""
    return asyncio.run(context_manager.add_user_message(session_id, message))

def add_assistant_message_sync(session_id: str, message: str):
    """Synchronous version of context_manager.add_assistant_message"""
    return asyncio.run(context_manager.add_assistant_message(session_id, message))

def generate_plan_sync(query: str, user_id: str, messages: Optional[List[Dict[str, str]]] = None, lead_ids: Optional[List[str]] = None):
    """Synchronous version of router_client.generate_plan"""
    return asyncio.run(router_client.generate_plan(query, user_id, messages, lead_ids=lead_ids))

def get_facts_by_lead_id_sync(lead_id: str, fields: Optional[List[str]] = None):
    """Synchronous version of fact_retriever.get_facts_by_lead_id"""
    return asyncio.run(fact_retriever.get_facts_by_lead_id(lead_id, fields))

def get_facts_sync(entity: str, fields: Optional[List[str]] = None):
    """Synchronous version of fact_retriever.get_facts"""
    return asyncio.run(fact_retriever.get_facts(entity, fields))

def aggregate_results_sync(tool_results: List[Dict[str, Any]]):
    """Synchronous version of aggregator.aggregate_results"""
    return asyncio.run(aggregator.aggregate_results(tool_results))

def build_prompt_sync(query: str, context_results: List[Dict[str, Any]], intent: str = "search"):
    """Synchronous version of prompt_builder.build_prompt"""
    return asyncio.run(prompt_builder.build_prompt(query, context_results, intent))

def call_scraper_directly_sync(params: Dict[str, Any], session_id=None):
    """Synchronous version of call_scraper_directly"""
    return asyncio.run(call_scraper_directly(params, session_id))

def get_llm_response_sync(prompt: str):
    """Synchronous version of get_llm_response"""
    async def _run():
        async with DeepSeekClient() as client:
            return await client.generate_response(prompt)
    return asyncio.run(_run())

def run_async_generator(async_gen):
    """Utility to run an async generator in a sync Flask context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def consume():
        results = []
        async for item in async_gen:
            results.append(item)
        return results

    all_chunks = loop.run_until_complete(consume())
    for chunk in all_chunks:
        yield chunk

def is_lead_id(s: str) -> bool:
    """Checks if a string is likely a lead_id (e.g., a long hex string)."""
    if not isinstance(s, str):
        return False
    # A lead_id is typically long (>20 chars), has no spaces, and is often a hex string.
    return len(s) > 20 and ' ' not in s and re.match(r'^[a-f0-9-]+$', s.lower()) is not None

# --- ROUTES ---

@agentic_backend_bp.route("/api/query/stream/cancel", methods=["POST"])
@login_required
def cancel_query_stream():
    """
    Cancel the current query stream for a session.
    """
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
    set_stream_cancelled(session_id)
    logger.info(f"Stream cancellation requested for session {session_id}")
    return jsonify({"status": "cancelled", "session_id": session_id})

@agentic_backend_bp.route("/api/query/stream", methods=["POST"])
@login_required
def query_stream_endpoint():
    """
    Handles queries and streams the final 'verdict' using Server-Sent Events (SSE).
    """
    data = request.get_json(force=True)
    query = data.get("query")
    initial_session_id = data.get("session_id")
    use_context = data.get("use_context", True)
    lead_ids = data.get("lead_ids")
    
    if not query:
        return Response(json.dumps({"error": "Query is required"}), status=400, mimetype='application/json')
    
    user_id = current_user.user_id

    async def async_generator():
        try:
            # Get logger for this function scope
            func_logger = get_agentic_logger('routes')
            func_logger.info(f"Streaming query received: '{query}' | lead_ids: {lead_ids}")
            
            active_session_id = initial_session_id
            session_info = None

            if use_context and context_manager:
                session = await context_manager.get_or_create_session(user_id, active_session_id)
                active_session_id = session.session_id
                session_info = {
                    "session_id": active_session_id,
                    "message_count": session.get_message_count(),
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat()
                }

            # Check for cancellation before starting
            if is_stream_cancelled(active_session_id):
                func_logger.info(f"Stream cancelled before starting for session {active_session_id}")
                clear_stream_cancelled(active_session_id)
                yield f"data: {json.dumps({'type': 'cancelled'})}\n\n"
                return

            messages = await context_manager.get_conversation_array(active_session_id) if use_context and active_session_id else None
            plan = await router_client.generate_plan(query, user_id, messages, lead_ids=lead_ids)
            tool_results = []

            func_logger.info("Fetching facts from database based on plan...")
            entities_from_plan = plan.get("entities", [])
            fact_params = plan.get("params", {}).get("fact_db", {})
            fields = fact_params.get("fields")

            retrieved_fact_data = []
            if entities_from_plan:
                for entity in entities_from_plan:
                    if is_lead_id(entity):
                        func_logger.info(f"Entity '{entity}' detected as lead_id. Using direct lookup.")
                        result = await fact_retriever.get_facts_by_lead_id(entity, fields)
                        if result:
                            retrieved_fact_data.append(result)
                    else:
                        func_logger.warning(f"Entity '{entity}' detected as company name. Using fuzzy lookup.")
                        result = await fact_retriever.get_facts(entity, fields)
                        if result and not result.get("error"):
                            retrieved_fact_data.append(result)

            fact_result = {
                "tool": "fact_db",
                "status": "success",
                "data": {
                    "operation": fact_params.get("operation", "get_facts"),
                    "total_results": len(retrieved_fact_data),
                    "results": retrieved_fact_data,
                    "website_urls": [r.get("Website", "") for r in retrieved_fact_data if r.get("Website")]
                }
            }
            tool_results.append(fact_result)

            csv_data = fact_result.get("data", {})
            if csv_data.get("total_results", 0) > 0:
                website_urls = [url for url in csv_data.get("website_urls", []) if url and url.strip().startswith("http")]
                if website_urls:
                    scraper_params = plan.get("params", {}).get("scraper", {})
                    scraper_params["csv_urls"] = website_urls
                    scraper_result = await call_scraper_directly(scraper_params, active_session_id)
                    tool_results.append(scraper_result)

            rag_lead_ids = [entity for entity in entities_from_plan if is_lead_id(entity)]
            rag_result_content = query_faiss_and_rag(query, user_id, lead_ids=rag_lead_ids)
            tool_results.append({
                "tool": "faiss_rag",
                "data": {"rag_answer": rag_result_content},
                "status": "success"
            })

            aggregated_context = await aggregator.aggregate_results(tool_results)

            prompt = await prompt_builder.build_prompt(
                query=query,
                context_results=aggregated_context,
                intent=plan.get("intent")
            )
            metadata = {
                "comparison_table": [],
                "reasons": ["Data processed successfully"],
                "confidence": {"score": 0.8, "factors": ["Fact data available"]},
                "sources": [f"Tool results: {len(tool_results)} tools executed"],
                "context_used": len(aggregated_context),
                "plan_used": plan,
                "session_info": session_info
            }

            func_logger.info(f"Query metadata generated (not streamed): {json.dumps(metadata, indent=2)}")

            func_logger.info("Starting LLM stream for verdict...")
            full_verdict = ""
            async with DeepSeekClient() as client:
                async for chunk in client.stream_response(prompt):
                    if is_stream_cancelled(active_session_id):
                        func_logger.info(f"Stream cancelled during LLM streaming for session {active_session_id}")
                        clear_stream_cancelled(active_session_id)
                        yield f"data: {json.dumps({'type': 'cancelled'})}\n\n"
                        return
                    full_verdict += chunk
                    yield f"data: {json.dumps({'type': 'verdict_chunk', 'data': chunk})}\n\n"

            if use_context and active_session_id and context_manager:
                await context_manager.add_user_message(active_session_id, query)
                await context_manager.add_assistant_message(active_session_id, full_verdict)
                func_logger.info(f"Stored full streamed interaction in session {active_session_id}")

            func_logger.info("Stream completed successfully.")
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            func_logger.error(f"Error during stream generation: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"


    return Response(
        stream_with_context(run_async_generator(async_generator())),
        content_type="text/event-stream"
    )



@agentic_backend_bp.route("/api/query", methods=["POST"])
@login_required
def query_endpoint():
    """
    Main query endpoint that accepts natural language queries with optional context support
    """
    try:
        data = request.get_json(force=True)
        query = data.get("query")
        session_id = data.get("session_id")
        options = data.get("options", {})
        use_context = data.get("use_context", True)
        lead_ids = data.get("lead_ids")

        if not query:
            return jsonify({"error": "Query is required"}), 400

        dispatch_id = f"d-{uuid.uuid4().hex[:8]}"
        user_id = current_user.user_id
        logger.info(f"user_id from main.py is {user_id}")
        logger.info(f"Non-streaming query received: '{query}' | lead_ids: {lead_ids}")
        session_info = None

        # Handle session creation/retrieval if context is enabled
        if use_context and context_manager:
            try:
                session = get_or_create_session_sync(user_id, session_id)
                session_id = session.session_id
                session_info = {
                    "session_id": session_id,
                    "message_count": session.get_message_count(),
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat()
                }
                logger.info(f"Using session {session_id} for user {user_id}")
            except Exception as session_error:
                logger.warning(f"Session handling failed: {session_error}, proceeding without context")
                use_context = False
                session_id = None

        # Process query using same logic as streaming endpoint
        messages = get_conversation_array_sync(session_id) if use_context and session_id else None
        plan = generate_plan_sync(query, user_id, messages, lead_ids=lead_ids)
        tool_results = []

        logger.info("Fetching facts from database based on plan...")
        entities_from_plan = plan.get("entities", [])
        fact_params = plan.get("params", {}).get("fact_db", {})
        fields = fact_params.get("fields")

        retrieved_fact_data = []
        if entities_from_plan:
            for entity in entities_from_plan:
                if is_lead_id(entity):
                    logger.info(f"Entity '{entity}' detected as lead_id. Using direct lookup.")
                    result = get_facts_by_lead_id_sync(entity, fields)
                    if result:
                        retrieved_fact_data.append(result)
                else:
                    logger.warning(f"Entity '{entity}' detected as company name. Using fuzzy lookup.")
                    result = get_facts_sync(entity, fields)
                    if result and not result.get("error"):
                        retrieved_fact_data.append(result)

        fact_result = {
            "tool": "fact_db",
            "status": "success",
            "data": {
                "operation": fact_params.get("operation", "get_facts"),
                "total_results": len(retrieved_fact_data),
                "results": retrieved_fact_data,
                "website_urls": [r.get("Website", "") for r in retrieved_fact_data if r.get("Website")]
            }
        }
        tool_results.append(fact_result)

        csv_data = fact_result.get("data", {})
        if csv_data.get("total_results", 0) > 0:
            website_urls = [url for url in csv_data.get("website_urls", []) if url and url.strip().startswith("http")]
            if website_urls:
                scraper_params = plan.get("params", {}).get("scraper", {})
                scraper_params["csv_urls"] = website_urls
                scraper_result = call_scraper_directly_sync(scraper_params, session_id)
                tool_results.append(scraper_result)

        rag_lead_ids = [entity for entity in entities_from_plan if is_lead_id(entity)]
        rag_result_content = query_faiss_and_rag(query, user_id, lead_ids=rag_lead_ids)
        tool_results.append({
            "tool": "faiss_rag",
            "data": {"rag_answer": rag_result_content},
            "status": "success"
        })

        aggregated_context = aggregate_results_sync(tool_results)

        prompt = build_prompt_sync(
            query=query,
            context_results=aggregated_context,
            intent=plan.get("intent")
        )

        llm_response = get_llm_response_sync(prompt)

        if use_context and session_id and context_manager:
            try:
                add_user_message_sync(session_id, query)
                if hasattr(llm_response, 'content'):
                    add_assistant_message_sync(session_id, llm_response.content)
                else:
                    add_assistant_message_sync(session_id, str(llm_response))
                logger.info(f"Stored interaction in session {session_id}")
            except Exception as context_error:
                logger.warning(f"Failed to store interaction in context: {context_error}")

        if hasattr(llm_response, 'content'):
            verdict = llm_response.content
        else:
            verdict = str(llm_response)

        # Full result for backend logging
        result = {
            "comparison_table": [],
            "verdict": verdict,
            "reasons": ["Data processed successfully"],
            "confidence": {"score": 0.8, "factors": ["Fact data available"]},
            "sources": [f"Tool results: {len(tool_results)} tools executed"],
            "raw_llm_response": llm_response if isinstance(llm_response, dict) else str(llm_response),
            "context_used": len(aggregated_context),
            "plan_used": plan,
            "tool_results": tool_results
        }
        if session_info:
            result["session_info"] = session_info

        # Store + log for backend
        dispatch_results[dispatch_id] = {
            "dispatch_id": dispatch_id,
            "status": "completed" if verdict else "not_found",
            "result": result,
        }
        logger.info(f"Full result stored for dispatch {dispatch_id}: {result}")

        # Only return verdict to frontend
        return jsonify({"verdict": verdict})

    except Exception as e:
        logger.error(f"Error in query endpoint: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@agentic_backend_bp.route("/api/result/<string:dispatch_id>", methods=["GET"])
@login_required
def get_result(dispatch_id):
    """
    Get the result of a dispatch by ID
    """
    if dispatch_id not in dispatch_results:
        return jsonify({"error": "Dispatch not found"}), 404
    return jsonify(dispatch_results[dispatch_id])

@agentic_backend_bp.route("/api/session/new", methods=["POST"])
@login_required
def create_session():
    """
    Create a new conversation session
    """
    try:
        data = request.get_json(force=True)
        user_id = data.get("user_id") or getattr(current_user, "user_id", None)
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        if not context_manager:
            return jsonify({"error": "Context management not available"}), 503
        session = get_or_create_session_sync(user_id)
        return jsonify({
            "session_id": session.session_id,
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "message_count": session.get_message_count(),
            "status": "created"
        })
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return jsonify({"error": "Failed to create session"}), 500

@agentic_backend_bp.route("/api/session/<string:session_id>/clear", methods=["DELETE"])
@login_required
def clear_session(session_id):
    """
    Clear all messages from a session while keeping the session active
    """
    try:
        user_id = request.args.get("user_id") or getattr(current_user, "user_id", None)
        if not context_manager:
            return jsonify({"error": "Context management not available"}), 503
        if user_id:
            session = asyncio.run(context_manager.session_store.get_session(session_id))
            if not session:
                return jsonify({"error": "Session not found"}), 404
            if session.user_id != user_id:
                return jsonify({"error": "Access denied"}), 403
        asyncio.run(context_manager.clear_session(session_id))
        return jsonify({
            "session_id": session_id,
            "status": "cleared",
            "message": "Session messages cleared successfully"
        })
    except Exception as e:
        logger.error(f"Error clearing session: {str(e)}")
        return jsonify({"error": "Failed to clear session"}), 500

@agentic_backend_bp.route("/api/session/<string:session_id>/history", methods=["GET"])
@login_required
def get_session_history(session_id):
    """
    Get conversation history for a session
    """
    try:
        user_id = request.args.get("user_id") or getattr(current_user, "user_id", None)
        if not context_manager:
            return jsonify({"error": "Context management not available"}), 503
        session_info = asyncio.run(context_manager.get_session_info(session_id))
        if not session_info:
            return jsonify({"error": "Session not found"}), 404
        if user_id and session_info["user_id"] != user_id:
            return jsonify({"error": "Access denied"}), 403
        conversation_messages = get_conversation_array_sync(session_id)
        return jsonify({
            "session_id": session_id,
            "session_info": session_info,
            "messages": conversation_messages,
            "total_messages": len(conversation_messages)
        })
    except Exception as e:
        logger.error(f"Error getting session history: {str(e)}")
        return jsonify({"error": "Failed to get session history"}), 500

@agentic_backend_bp.route("/api/session/<string:session_id>/delete", methods=["DELETE"])
@login_required
def delete_session(session_id):
    """
    Delete a session completely
    """
    try:
        user_id = request.args.get("user_id") or getattr(current_user, "user_id", None)
        if not context_manager:
            return jsonify({"error": "Context management not available"}), 503
        if user_id:
            session = asyncio.run(context_manager.session_store.get_session(session_id))
            if not session:
                return jsonify({"error": "Session not found"}), 404
            if session.user_id != user_id:
                return jsonify({"error": "Access denied"}), 403
        deleted = asyncio.run(context_manager.delete_session(session_id))
        if deleted:
            return jsonify({
                "session_id": session_id,
                "status": "deleted",
                "message": "Session deleted successfully"
            })
        else:
            return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        return jsonify({"error": "Failed to delete session"}), 500

@agentic_backend_bp.route("/api/user/<string:user_id>/sessions", methods=["GET"])
@login_required
def get_user_sessions(user_id):
    """
    Get all sessions for a user
    """
    try:
        if not context_manager:
            return jsonify({"error": "Context management not available"}), 503
        sessions_info = asyncio.run(context_manager.get_user_sessions_info(user_id))
        return jsonify({
            "user_id": user_id,
            "sessions": sessions_info,
            "total_sessions": len(sessions_info)
        })
    except Exception as e:
        logger.error(f"Error getting user sessions: {str(e)}")
        return jsonify({"error": "Failed to get user sessions"}), 500

@agentic_backend_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint with context management status
    """
    health_status = {"status": "healthy", "message": "Agentic Backend API is running"}
    if context_manager:
        try:
            context_health = asyncio.run(context_manager.health_check())
            health_status["context_management"] = context_health
        except Exception as e:
            health_status["context_management"] = {
                "status": "error",
                "error": str(e)
            }
    else:
        health_status["context_management"] = {
            "status": "disabled",
            "message": "Context management not initialized"
        }
    return jsonify(health_status)


async def call_fact_retriever_directly(params: Dict[str, Any], fact_retriever: FactRetrieverWorker, session_id=None) -> Dict[str, Any]:
    """
    Call fact retriever directly with proper parameter handling and cancellation support
    """
    try:
        operation = params.get("operation", "get_facts")
        entities = params.get("entities", [])
        fields = params.get("fields", [])

        logger.info(f"Fact retriever operation: {operation}")
        logger.info(f"Fact retriever entities: {entities}")

        if operation == "industry_filter":
            # Handle industry filtering
            industry = params.get("industry", "")
            limit = params.get("limit", 10)
            sort_by = params.get("sort_by", "Revenue")

            logger.info(f"Industry filter: {industry}, limit: {limit}, sort_by: {sort_by}")

            # Get all companies and filter by industry
            results = []
            for company_name in fact_retriever.facts_cache.keys():
                if session_id and is_stream_cancelled(session_id):
                    logger.info(f"Fact retriever cancelled for session {session_id}")
                    clear_stream_cancelled(session_id)
                    break
                company_data = fact_retriever.facts_cache[company_name]
                company_industry = company_data.get("Industry ", "") or company_data.get("Industry", "")

                if industry.lower() in company_industry.lower():
                    result_data = {"entity": company_name}
                    if fields:
                        for field in fields:
                            if field in company_data:
                                result_data[field] = company_data[field]
                    else:
                        result_data.update(company_data)
                    results.append(result_data)

            # Sort results
            if sort_by and results:
                try:
                    results.sort(key=lambda x: float(str(x.get(sort_by, "0")).replace("$", "").replace("M", "000000").replace("K", "000").replace(",", "")), reverse=True)
                except:
                    pass  # If sorting fails, keep original order

            # Limit results
            results = results[:limit]

            return {
                "tool": "fact_csv",
                "status": "success",
                "data": {
                    "operation": operation,
                    "industry": industry,
                    "total_results": len(results),
                    "results": results,
                    "website_urls": [r.get("Website", "") for r in results if r.get("Website")]
                }
            }
        else:
            # Handle regular entity lookup
            results = []
            for entity in entities:
                if session_id and is_stream_cancelled(session_id):
                    logger.info(f"Fact retriever cancelled for session {session_id}")
                    clear_stream_cancelled(session_id)
                    break
                entity_result = await fact_retriever.get_facts(entity, fields)
                if entity_result and not entity_result.get("error"):
                    results.append(entity_result)

            return {
                "tool": "fact_csv",
                "status": "success",
                "data": {
                    "operation": operation,
                    "total_results": len(results),
                    "results": results,
                    "website_urls": [r.get("Website", "") for r in results if r.get("Website")]
                }
            }
    except Exception as e:
        logger.error(f"Error in fact retriever: {str(e)}")
        return {
            "tool": "fact_csv",
            "status": "error",
            "data": {
                "error": str(e),
                "operation": params.get("operation", "unknown")
            }
        }

async def call_scraper_directly(params: Dict[str, Any], session_id=None) -> Dict[str, Any]:
    """
    Call enhanced scraper with SmartScraperGraph integration
    Checks for cancellation during scraping.
    """
    try:
        from workers.scraper_worker import ScraperWorker

        csv_urls = params.get("csv_urls", [])
        query_intent = params.get("query_intent", "general")

        if not csv_urls:
            logger.warning("No URLs provided to scraper")
            return {
                "tool": "scraper",
                "status": "success",
                "data": {
                    "scraped_content": "No URLs to scrape",
                    "urls_processed": []
                }
            }

        intent_prompts = {
            "financial": "Extract financial information, revenue data, profit margins, growth rates, and any business metrics from this company website",
            "about": "Extract company information including mission, vision, history, founding details, and general company overview from this website",
            "team": "Extract information about company leadership, management team, founders, and key personnel from this website",
            "news": "Extract recent news, press releases, announcements, and company updates from this website",
            "products": "Extract information about products, services, solutions, and offerings from this company website",
            "general": "Extract comprehensive company information including business details, services, financial data, and key company facts from this website"
        }

        prompt = intent_prompts.get(query_intent, intent_prompts["general"])

        logger.info(f"Scraping {len(csv_urls)} URLs with intent: {query_intent}")
        logger.info(f"Using prompt: {prompt}")

        async with ScraperWorker() as scraper_worker:
            scraped_results = []

            for url in csv_urls[:3]:  # Limit to first 3 URLs to avoid timeout
                if session_id and is_stream_cancelled(session_id):
                    logger.info(f"Scraper cancelled for session {session_id}")
                    clear_stream_cancelled(session_id)
                    break
                if not url or url.strip() == "":
                    continue

                logger.info(f"Scraping URL: {url}")

                try:
                    result = await scraper_worker.scrape_url(
                        url=url.strip(),
                        prompt=prompt
                    )

                    if result and result.get("metadata", {}).get("status") == "success":
                        content = result.get("content", "")
                        financial_data = result.get("financial_data", {})
                        business_metrics = result.get("business_metrics", {})
                        method = result.get("metadata", {}).get("scraping_method", "unknown")

                        scraped_results.append({
                            "url": url,
                            "content": content,
                            "financial_data": financial_data,
                            "business_metrics": business_metrics,
                            "scraping_method": method,
                            "content_length": len(content)
                        })
                    else:
                        error_msg = result.get("metadata", {}).get("error", "Unknown error")
                        logger.warning(f"Failed to scrape {url}: {error_msg}")

                except Exception as scrape_error:
                    logger.error(f"Error scraping {url}: {str(scrape_error)}")
                    continue

        combined_content = ""
        all_financial_data = {}
        all_business_metrics = {}
        methods_used = []

        for result in scraped_results:
            url = result['url']
            content = result['content']
            combined_content += f"\n\nContent from {url}:\n{content}"

            for key, value in result.get("financial_data", {}).items():
                if value and value != "":
                    all_financial_data[f"{key}_{url}"] = value

            for key, value in result.get("business_metrics", {}).items():
                if value and value != "":
                    all_business_metrics[f"{key}_{url}"] = value

            method = result.get("scraping_method", "unknown")
            if method not in methods_used:
                methods_used.append(method)

        return {
            "tool": "scraper",
            "status": "success",
            "data": {
                "scraped_content": combined_content.strip(),
                "urls_processed": [r["url"] for r in scraped_results],
                "total_urls_attempted": len(csv_urls),
                "successful_scrapes": len(scraped_results),
                "financial_data": all_financial_data,
                "business_metrics": all_business_metrics,
                "scraping_methods_used": methods_used,
                "query_intent": query_intent,
                "prompt_used": prompt
            }
        }

    except Exception as e:
        logger.error(f"Error in enhanced scraper: {str(e)}")
        return {
            "tool": "scraper",
            "status": "error",
            "data": {
                "error": str(e),
                "urls_processed": []
            }
        }

async def process_query_with_orchestrator(
    query: str,
    user_id: str,
    session_id: Optional[str] = None,
    use_context: bool = False
) -> Dict[str, Any]:
    """
    Process query through a simplified orchestrator pipeline (bypassing LangGraph for now)
    CSV-gated: Always run fact_csv first; if not found, return immediately.
    """
    try:
        logger.info(f"Processing query with simplified orchestrator: {query}")

        # Step 1: Get plan from router (with context if available)
        logger.info("Getting plan from router...")
        messages = None
        if use_context and session_id and context_manager:
            try:
                messages = await context_manager.get_conversation_array(session_id)
                logger.info(f"Retrieved {len(messages) if messages else 0} context messages for routing")
            except Exception as e:
                logger.warning(f"Failed to get context messages for routing: {e}")

        plan = await router_client.generate_plan(query, user_id, messages)
        logger.info(f"Generated plan: {plan}")

        tools = plan.get("tools", [])
        params = plan.get("params", {})
        tool_results = []

        # CSV-gated: Ensure fact_csv runs first even if not explicitly in tools
        fact_params = params.get("fact_csv", {}).copy()
        if not fact_params:
            entities = plan.get("entities") or ([query] if query else [])
            fact_params = {
                "entities": entities,
                "fields": ["Company Name", "Industry ", "Revenue", "Employees", "Website", "Industry"],
                "operation": "get_facts",
                "intent": plan.get("intent", "search")
            }
            params["fact_csv"] = fact_params
        else:
            # IMPORTANT: Don't override the operation from the router plan
            # The router may have set specific operations like "industry_filter"
            logger.info(f"Using router-generated fact_csv params: {fact_params}")

            # Only inject raw query if entities are empty, and ensure required fields
            if not fact_params.get("entities") and query:
                fact_params["entities"] = [query]
            fields = fact_params.get("fields", []) or []
            for fld in ["Company Name", "Industry ", "Industry", "Revenue", "Employees", "Website"]:
                if fld not in fields:
                    fields.append(fld)
            fact_params["fields"] = fields
            params["fact_csv"] = fact_params

        logger.info(f"Calling fact_retriever with params: {fact_params}")

        # Call fact retriever directly since orchestrator methods don't exist
        fact_result = await call_fact_retriever_directly(fact_params, fact_retriever, session_id)
        logger.info(f"Fact retriever result: {fact_result}")
        tool_results.append(fact_result)

        # Gate on CSV results
        csv_data = fact_result.get("data", {}) if isinstance(fact_result, dict) else {}
        total_results = csv_data.get("total_results", 0)
        if total_results == 0:
            logger.info("CSV-gated: company not found, returning early without scraping/LLM")
            return {
                "status": "not_found",
                "message": "Company not found in CSV",
                "query": query
            }

        # From here onward, enrichment is allowed (default true) unless disabled via env
        allow_enrichment = os.getenv("ALLOW_FURTHER_TOOLS_ON_HIT", "true").lower() == "true"
        if not allow_enrichment:
            logger.info("CSV hit found; enrichment disabled by configuration")
            return {
                "status": "completed",
                "verdict": "Facts retrieved from CSV",
                "tool_results": tool_results,
                "plan_used": plan
            }

        # Step 2: Execute enrichment tools (scraper coordinated with CSV URLs if available)
        logger.info("Executing enrichment tools...")
        website_urls = csv_data.get("website_urls", [])
        logger.info(f"🌐 Found {len(website_urls)} website URLs from CSV: {website_urls}")

        # Filter out empty/invalid URLs
        valid_urls = [url for url in website_urls if url and url.strip() and url.startswith("http")]
        logger.info(f"🔍 Valid URLs after filtering: {valid_urls}")

        if valid_urls:
            scraper_params = params.get("scraper", {}).copy()
            scraper_params["csv_urls"] = valid_urls

            # Determine query intent from the original query
            query_lower = query.lower()
            if any(word in query_lower for word in ["financial", "revenue", "profit", "earnings"]):
                scraper_params["query_intent"] = "financial"
            elif any(word in query_lower for word in ["about", "company", "mission", "history"]):
                scraper_params["query_intent"] = "about"
            elif any(word in query_lower for word in ["team", "leadership", "management", "founder"]):
                scraper_params["query_intent"] = "team"
            elif any(word in query_lower for word in ["news", "press", "announcement"]):
                scraper_params["query_intent"] = "news"
            elif any(word in query_lower for word in ["product", "service", "solution"]):
                scraper_params["query_intent"] = "products"
            else:
                scraper_params["query_intent"] = "general"

            logger.info(f"Calling scraper with enhanced params: {scraper_params}")
            scraper_result = await call_scraper_directly(scraper_params, session_id)
            logger.info(f"Scraper result: {scraper_result}")
            tool_results.append(scraper_result)
        else:
            logger.warning(f"❌ No valid website URLs found; skipping scraper")
            logger.warning(f"   Raw URLs from CSV: {website_urls}")
            logger.warning(f"   Valid URLs after filtering: {valid_urls if 'valid_urls' in locals() else 'Not calculated'}")

        # Step 3: Get RAG result and add to tool results
        logger.info("Getting RAG result...")
        try:
            rag_result = query_faiss_and_rag(query)
            # Add RAG result as a tool result for aggregation
            rag_tool_result = {
                "tool": "faiss_rag",
                "data": {
                    "rag_answer": rag_result,
                    "query": query,
                    "source": "faiss_rag"
                },
                "status": "success"
            }
            tool_results.append(rag_tool_result)
            logger.info(f"RAG result added to tool results: {rag_result[:100]}...")
        except Exception as e:
            logger.error(f"RAG error: {e}")
            # Add error result so aggregator can handle it
            rag_tool_result = {
                "tool": "faiss_rag",
                "data": {
                    "error": str(e),
                    "query": query,
                    "source": "faiss_rag"
                },
                "status": "error"
            }
            tool_results.append(rag_tool_result)

        # Step 4: Aggregate results (now includes RAG)
        logger.info("Aggregating results...")
        logger.info(f"Tool results before aggregation: {len(tool_results)} results")
        for i, result in enumerate(tool_results):
            logger.info(f"Tool result {i+1}: {result.get('tool', 'unknown')} - Status: {result.get('status', 'unknown')}")
            if result.get('tool') == 'fact_csv':
                data = result.get('data', {})
                logger.info(f"Fact CSV data: total_results={data.get('total_results', 0)}, results={len(data.get('results', []))}")
                for j, company in enumerate(data.get('results', [])[:3]):  # Log first 3 companies
                    logger.info(f"Company {j+1}: {company.get('Company Name', 'Unknown')} - Industry: {company.get('Industry ', 'Unknown')}")

        aggregated_context = await aggregator.aggregate_results(tool_results)
        logger.info(f"Aggregated context: {len(aggregated_context)} items")

        # Log aggregated context details
        for i, context_item in enumerate(aggregated_context[:5]):  # Log first 5 context items
            logger.info(f"Context item {i+1}: source={context_item.get('source', 'unknown')}, type={context_item.get('type', 'unknown')}")
            logger.info(f"Context text preview: {context_item.get('text', '')[:200]}...")

        # Step 5: Build prompt
        logger.info("Building prompt...")
        prompt = await prompt_builder.build_prompt(
            query=query,
            context_results=aggregated_context,
            intent=plan.get("intent", "search")
        )
        logger.info(f"Built prompt length: {len(prompt)} characters")
        logger.info(f"Prompt preview: {prompt[:500]}...")

        # Step 6: Get LLM response (always use the prompt with tool results)
        logger.info("Getting LLM response...")
        async with deepseek_client:
            # IMPORTANT: Always use the prompt that includes tool results (CSV data, etc.)
            # The context-aware routing has already been handled in the planning phase
            llm_response = await deepseek_client.generate_response(prompt)

            # If context is enabled, store the interaction in session
            if use_context and session_id and context_manager:
                try:
                    # Add current query as user message to conversation
                    await context_manager.add_user_message(session_id, query)

                    # Store assistant response in context
                    if hasattr(llm_response, 'content'):
                        await context_manager.add_assistant_message(session_id, llm_response.content)

                    logger.info(f"Stored interaction in session {session_id}")

                except Exception as context_error:
                    logger.warning(f"Failed to store interaction in context: {context_error}")
                    # Continue anyway since we have the LLM response

        logger.info(f"LLM Response received - Status: {getattr(llm_response, 'status', 'unknown')}")
        logger.info(f"LLM Response fallback used: {getattr(llm_response, 'fallback_used', 'unknown')}")
        if hasattr(llm_response, 'content'):
            logger.info(f"LLM Response content preview: {llm_response.content[:300]}...")
        else:
            logger.info(f"LLM Response (raw): {str(llm_response)[:300]}...")

        # Step 7: Format final response
        if hasattr(llm_response, 'content'):
            llm_content = llm_response.content
            llm_dict = {
                "content": llm_response.content,
                "status": llm_response.status,
                "usage": llm_response.usage,
                "model": llm_response.model,
                "fallback_used": llm_response.fallback_used,
                "timestamp": llm_response.timestamp.isoformat() if hasattr(llm_response.timestamp, 'isoformat') else str(llm_response.timestamp),
                "execution_time": llm_response.execution_time
            }
        else:
            llm_content = str(llm_response)
            llm_dict = llm_response

        final_response = {
            "comparison_table": [],
            "verdict": llm_content,
            "reasons": ["Data processed successfully"],
            "confidence": {"score": 0.8, "factors": ["Fact data available"]},
            "sources": [f"Tool results: {len(tool_results)} tools executed"],
            "raw_llm_response": llm_dict,
            "context_used": len(aggregated_context),
            "plan_used": plan
        }

        return final_response

    except Exception as e:
        logger.error(f"Error in simplified orchestrator: {str(e)}")
        return {
            "error": str(e),
            "verdict": "Processing failed",
            "reasons": [f"Error: {str(e)}"]
        }

@agentic_backend_bp.route("/testtset/", methods=["GET"])
@login_required
def get_user_drafts_data():
    """Get draft data for specific lead_ids for the current user"""
    logger.info(f'Route hit: /api/leads/drafts_history by user_id={current_user.user_id}, username={current_user.username}')

    try:
        drafts = UserLeadDraft.query.filter_by(user_id=current_user.user_id, is_deleted=False).all()
        # Filter drafts by user_id and lead_ids, excluding deleted ones
       # logger.info(f'drafts-------------------- are {drafts}')
       # logger.info(f'Found {len(drafts)} drafts for user_id={current_user.user_id}')
        #logger.info(f'drafts are {drafts}')

        # Create dictionary with lead_id as key and draft_data as value
        result = {}
        for draft in drafts:
            result[str(draft.lead_id)] = draft.draft_data
        logger.info(f'results are {result}')

        return jsonify(result)

    except Exception as e:
        logger.error(f'Error in get_user_drafts: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500
# You must register this blueprint in your Flask app:
# from routes.agentic_backend_routes import agentic_backend_bp
# app.register_blueprint(agentic_backend_bp)