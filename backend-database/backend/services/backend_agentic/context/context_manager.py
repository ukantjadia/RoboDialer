"""Context manager for handling conversation sessions and message flow."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

from .models import ConversationSession, ContextConfig, Message
from .session_store import SessionStore
from .error_handler import ContextErrorHandler

# Import agentic logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentic_logging import get_agentic_logger

logger = get_agentic_logger('context.manager')


class ContextManager:
    """Central component for managing conversation context and session lifecycle."""
    
    def __init__(
        self, 
        session_store: SessionStore, 
        config: ContextConfig,
        error_handler: Optional[ContextErrorHandler] = None
    ):
        """Initialize the context manager.
        
        Args:
            session_store: Storage backend for sessions
            config: Configuration for context management
            error_handler: Optional error handler for fallback mechanisms
        """
        self.session_store = session_store
        self.config = config
        self.error_handler = error_handler or ContextErrorHandler(session_store, config)
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("ContextManager initialized with error handling")
    
    async def start_background_cleanup(self) -> None:
        """Start background task for automatic session cleanup."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._background_cleanup_loop())
            logger.info("Started background cleanup task")
    
    async def stop_background_cleanup(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped background cleanup task")
    
    async def get_or_create_session(
        self, 
        user_id: str, 
        session_id: Optional[str] = None
    ) -> ConversationSession:
        """Get existing session or create a new one with user isolation and error handling.
        
        Args:
            user_id: ID of the user requesting the session
            session_id: Optional specific session ID to retrieve/create
            
        Returns:
            ConversationSession: The retrieved or created session
            
        Raises:
            ValueError: If session exists but belongs to different user
        """
        try:
            # If session_id is provided, try to retrieve it
            if session_id:
                existing_session = await self.session_store.get_session(session_id)
                if existing_session:
                    # Verify user isolation
                    if existing_session.user_id != user_id:
                        raise ValueError(f"Session {session_id} belongs to different user")
                    logger.debug(f"Retrieved existing session {session_id} for user {user_id}")
                    return existing_session
                else:
                    # Session ID provided but doesn't exist - create with that ID
                    logger.info(f"Creating new session with ID {session_id} for user {user_id}")
                    return await self._create_new_session(user_id, session_id)
            
            # No session_id provided - create a new session
            logger.info(f"Creating new session for user {user_id}")
            return await self._create_new_session(user_id)
            
        except Exception as e:
            # Use error handler for session recovery
            logger.warning(f"Session retrieval/creation failed: {e}, attempting recovery")
            recovery_result = await self.error_handler.handle_session_error(e, user_id, session_id)
            
            if recovery_result.success and recovery_result.session:
                logger.info(f"Session recovered using {recovery_result.fallback_method}")
                return recovery_result.session
            else:
                logger.error(f"Session recovery failed: {recovery_result.error_message}")
                raise e
    
    async def add_user_message(
        self, 
        session_id: str, 
        message: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a user message to the conversation session with error handling.
        
        Args:
            session_id: ID of the session to add message to
            message: The user's message content
            metadata: Optional metadata for the message
            
        Raises:
            ValueError: If session doesn't exist and cannot be recovered
        """
        try:
            session = await self.session_store.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Check token limits before adding
            estimated_tokens = session.get_token_estimate() + len(message) // 4
            if estimated_tokens > self.config.max_tokens_per_session:
                recovery_result = await self.error_handler.handle_token_limit_exceeded(
                    session, self.config.max_tokens_per_session
                )
                if recovery_result.success and recovery_result.session:
                    session = recovery_result.session
                    logger.info(f"Applied token management: {recovery_result.fallback_method}")
                else:
                    logger.warning(f"Token limit handling failed: {recovery_result.error_message}")
            
            # Check message limits before adding
            if session.get_message_count() >= self.config.max_messages_per_session:
                await self._apply_truncation_strategy(session)
            
            session.add_message("user", message, metadata)
            await self.session_store.update_session(session_id, session)
            
            logger.debug(f"Added user message to session {session_id}, total messages: {session.get_message_count()}")
            
        except Exception as e:
            # Try to recover the session
            logger.warning(f"Failed to add user message: {e}, attempting recovery")
            recovery_result = await self.error_handler.handle_session_error(e, "", session_id)
            
            if recovery_result.success and recovery_result.session:
                # Retry with recovered session
                session = recovery_result.session
                session.add_message("user", message, metadata)
                await self.session_store.update_session(session_id, session)
                logger.info(f"Message added after session recovery using {recovery_result.fallback_method}")
            else:
                logger.error(f"Session recovery failed: {recovery_result.error_message}")
                raise e
    
    async def add_assistant_message(
        self, 
        session_id: str, 
        message: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an assistant message to the conversation session with error handling.
        
        Args:
            session_id: ID of the session to add message to
            message: The assistant's message content
            metadata: Optional metadata for the message
            
        Raises:
            ValueError: If session doesn't exist and cannot be recovered
        """
        try:
            session = await self.session_store.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Check token limits before adding
            estimated_tokens = session.get_token_estimate() + len(message) // 4
            if estimated_tokens > self.config.max_tokens_per_session:
                recovery_result = await self.error_handler.handle_token_limit_exceeded(
                    session, self.config.max_tokens_per_session
                )
                if recovery_result.success and recovery_result.session:
                    session = recovery_result.session
                    logger.info(f"Applied token management: {recovery_result.fallback_method}")
                else:
                    logger.warning(f"Token limit handling failed: {recovery_result.error_message}")
            
            # Check message limits before adding
            if session.get_message_count() >= self.config.max_messages_per_session:
                await self._apply_truncation_strategy(session)
            
            session.add_message("assistant", message, metadata)
            await self.session_store.update_session(session_id, session)
            
            logger.debug(f"Added assistant message to session {session_id}, total messages: {session.get_message_count()}")
            
        except Exception as e:
            # Try to recover the session
            logger.warning(f"Failed to add assistant message: {e}, attempting recovery")
            recovery_result = await self.error_handler.handle_session_error(e, "", session_id)
            
            if recovery_result.success and recovery_result.session:
                # Retry with recovered session
                session = recovery_result.session
                session.add_message("assistant", message, metadata)
                await self.session_store.update_session(session_id, session)
                logger.info(f"Message added after session recovery using {recovery_result.fallback_method}")
            else:
                logger.error(f"Session recovery failed: {recovery_result.error_message}")
                raise e
    
    async def get_conversation_array(self, session_id: str) -> List[Dict[str, str]]:
        """Generate conversation array for DeepSeek API format.
        
        Args:
            session_id: ID of the session to get conversation for
            
        Returns:
            List of message dictionaries in DeepSeek API format
            
        Raises:
            ValueError: If session doesn't exist
        """
        session = await self.session_store.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Get conversation messages (includes system message if it was added during session creation)
        messages = session.get_messages_as_dict_list()
        
        # If no system message exists and we have a system prompt configured, add it at the beginning
        if self.config.system_prompt and (not messages or messages[0].get("role") != "system"):
            messages.insert(0, {
                "role": "system",
                "content": self.config.system_prompt
            })
        
        # Apply token management if enabled
        if self.config.enable_token_management:
            messages = await self._manage_token_limits(messages, session)
        
        logger.debug(f"Generated conversation array for session {session_id} with {len(messages)} messages")
        return messages
    
    async def clear_session(self, session_id: str) -> None:
        """Clear all messages from a session while keeping the session active.
        
        Args:
            session_id: ID of the session to clear
            
        Raises:
            ValueError: If session doesn't exist
        """
        session = await self.session_store.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        session.clear_messages()
        await self.session_store.update_session(session_id, session)
        
        logger.info(f"Cleared messages from session {session_id}")
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session completely.
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            bool: True if session was deleted, False if not found
        """
        result = await self.session_store.delete_session(session_id)
        if result:
            logger.info(f"Deleted session {session_id}")
        return result
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions based on timeout configuration.
        
        Returns:
            int: Number of sessions cleaned up
        """
        cleanup_count = await self.session_store.cleanup_expired(self.config.session_timeout_minutes)
        
        # Also cleanup excess sessions per user
        user_cleanup_count = 0
        stats = await self.session_store.get_memory_stats()
        if stats["total_users"] > 0:
            # Get all users and cleanup their excess sessions
            # Note: This is a simplified approach - in production you might want to track this differently
            for user_id in await self._get_all_user_ids():
                user_cleanup_count += await self.session_store.cleanup_user_sessions(
                    user_id, self.config.max_sessions_per_user
                )
        
        total_cleanup = cleanup_count + user_cleanup_count
        if total_cleanup > 0:
            logger.info(f"Cleanup completed: {cleanup_count} expired, {user_cleanup_count} excess sessions")
        
        return total_cleanup
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Dict with session information or None if not found
        """
        session = await self.session_store.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "message_count": session.get_message_count(),
            "user_messages": session.get_user_messages_count(),
            "assistant_messages": session.get_assistant_messages_count(),
            "token_estimate": session.get_token_estimate(),
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "is_expired": session.is_expired(self.config.session_timeout_minutes),
            "metadata": session.metadata
        }
    
    async def get_user_sessions_info(self, user_id: str) -> List[Dict[str, Any]]:
        """Get information about all sessions for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of session information dictionaries
        """
        sessions = await self.session_store.get_user_sessions(user_id)
        return [
            {
                "session_id": session.session_id,
                "message_count": session.get_message_count(),
                "token_estimate": session.get_token_estimate(),
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "is_expired": session.is_expired(self.config.session_timeout_minutes)
            }
            for session in sessions
        ]
    
    async def handle_api_error_with_fallback(
        self,
        error: Exception,
        fallback_prompt: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Any:
        """Handle API errors with fallback to stateless processing.
        
        Args:
            error: The API error that occurred
            fallback_prompt: Prompt to use for stateless fallback
            user_id: ID of the user
            session_id: Optional session ID
            
        Returns:
            APIResponse from fallback processing
        """
        logger.warning(f"API error occurred for user {user_id}: {error}")
        
        # Check if user is rate limited
        if await self.error_handler.is_rate_limited(user_id):
            rate_info = await self.error_handler.get_rate_limit_info(user_id)
            logger.info(f"User {user_id} is rate limited, remaining: {rate_info['remaining_seconds']}s")
            
            # Return rate limit response
            try:
                from llm.deepseek_client import APIResponse
            except ImportError:
                # Create a mock APIResponse for testing
                APIResponse = type('APIResponse', (), {})
            
            return APIResponse(
                content=f"Rate limited. Please wait {rate_info['remaining_seconds']:.0f} seconds before retrying.",
                status="rate_limited",
                usage={},
                model="rate_limit",
                validation_result={"is_valid": False, "errors": ["Rate limited"]},
                fallback_used=True,
                timestamp=datetime.now(),
                execution_time=0.0
            )
        
        # Handle the API error with fallback
        recovery_result = await self.error_handler.handle_api_error(
            error, fallback_prompt, user_id, session_id
        )
        
        if recovery_result.success and recovery_result.response:
            logger.info(f"API error handled with fallback: {recovery_result.fallback_method}")
            return recovery_result.response
        else:
            logger.error(f"API error handling failed: {recovery_result.error_message}")
            return recovery_result.response  # Will be an error response
    
    async def handle_rate_limit_with_backoff(
        self,
        error: Exception,
        user_id: str,
        retry_count: int = 0
    ) -> bool:
        """Handle rate limiting with exponential backoff.
        
        Args:
            error: The rate limit error
            user_id: ID of the user
            retry_count: Current retry attempt
            
        Returns:
            bool: True if backoff was applied successfully
        """
        recovery_result = await self.error_handler.handle_rate_limit_error(
            error, user_id, retry_count
        )
        
        if recovery_result.success:
            logger.info(f"Rate limit backoff applied for user {user_id}: {recovery_result.fallback_method}")
            return True
        else:
            logger.error(f"Rate limit handling failed: {recovery_result.error_message}")
            return False
    
    async def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics.
        
        Returns:
            Dict with error statistics
        """
        return await self.error_handler.get_error_statistics()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on context management system.
        
        Returns:
            Dict with health check results
        """
        store_health = await self.session_store.health_check()
        error_stats = await self.error_handler.get_error_statistics()
        
        # Add context manager specific checks
        context_issues = []
        if self._cleanup_task and self._cleanup_task.done():
            context_issues.append("Background cleanup task stopped")
        
        # Check error rates
        total_errors = error_stats.get("total_errors", 0)
        if total_errors > 100:  # Arbitrary threshold
            context_issues.append(f"High error count: {total_errors}")
        
        return {
            "context_manager": {
                "status": "healthy" if not context_issues else "warning",
                "issues": context_issues,
                "cleanup_task_running": self._cleanup_task and not self._cleanup_task.done(),
                "config": {
                    "max_messages_per_session": self.config.max_messages_per_session,
                    "session_timeout_minutes": self.config.session_timeout_minutes,
                    "max_sessions_per_user": self.config.max_sessions_per_user,
                    "enable_token_management": self.config.enable_token_management
                }
            },
            "session_store": store_health,
            "error_handler": error_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _create_new_session(
        self, 
        user_id: str, 
        session_id: Optional[str] = None
    ) -> ConversationSession:
        """Internal method to create a new session with proper initialization.
        
        Args:
            user_id: ID of the user
            session_id: Optional specific session ID
            
        Returns:
            ConversationSession: The created session
        """
        # Check user session limits
        user_session_count = await self.session_store.get_user_session_count(user_id)
        if user_session_count >= self.config.max_sessions_per_user:
            # Cleanup oldest sessions for this user
            await self.session_store.cleanup_user_sessions(user_id, self.config.max_sessions_per_user - 1)
        
        # Create the session
        session = await self.session_store.create_session(user_id, session_id)
        
        # Add system message if configured
        if self.config.system_prompt:
            session.add_message("system", self.config.system_prompt)
            await self.session_store.update_session(session.session_id, session)
        
        return session
    
    async def _apply_truncation_strategy(self, session: ConversationSession) -> None:
        """Apply message truncation strategy when limits are reached.
        
        Args:
            session: The session to apply truncation to
        """
        if self.config.truncation_strategy == "oldest_first":
            await self._truncate_oldest_first(session)
        elif self.config.truncation_strategy == "sliding_window":
            await self._truncate_sliding_window(session)
        else:
            # Default to oldest_first
            await self._truncate_oldest_first(session)
    
    async def _truncate_oldest_first(self, session: ConversationSession) -> None:
        """Truncate oldest messages first, preserving system messages.
        
        Args:
            session: The session to truncate
        """
        target_count = int(self.config.max_messages_per_session * 0.8)  # Keep 80% of max
        current_count = session.get_message_count()
        
        if current_count <= target_count:
            return
        
        messages_to_remove = current_count - target_count
        
        # Separate system messages from others
        system_messages = [msg for msg in session.messages if msg.role == "system"]
        other_messages = [msg for msg in session.messages if msg.role != "system"]
        
        # Remove oldest non-system messages
        if len(other_messages) > messages_to_remove:
            other_messages = other_messages[messages_to_remove:]
        else:
            other_messages = []
        
        # Reconstruct message list
        session.messages = system_messages + other_messages
        
        logger.info(f"Truncated {messages_to_remove} messages from session {session.session_id}")
    
    async def _truncate_sliding_window(self, session: ConversationSession) -> None:
        """Keep recent messages in a sliding window, preserving system messages.
        
        Args:
            session: The session to truncate
        """
        target_count = int(self.config.max_messages_per_session * 0.8)  # Keep 80% of max
        
        # Separate system messages from others
        system_messages = [msg for msg in session.messages if msg.role == "system"]
        other_messages = [msg for msg in session.messages if msg.role != "system"]
        
        # Keep most recent messages
        if len(other_messages) > target_count - len(system_messages):
            keep_count = target_count - len(system_messages)
            other_messages = other_messages[-keep_count:] if keep_count > 0 else []
        
        # Reconstruct message list
        session.messages = system_messages + other_messages
        
        logger.info(f"Applied sliding window truncation to session {session.session_id}")
    
    async def _manage_token_limits(
        self, 
        messages: List[Dict[str, str]], 
        session: ConversationSession
    ) -> List[Dict[str, str]]:
        """Manage token limits for message arrays.
        
        Args:
            messages: List of message dictionaries
            session: The conversation session
            
        Returns:
            List of message dictionaries within token limits
        """
        estimated_tokens = session.get_token_estimate()
        
        if estimated_tokens <= self.config.max_tokens_per_session:
            return messages
        
        # Simple truncation - remove oldest non-system messages
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        other_messages = [msg for msg in messages if msg.get("role") != "system"]
        
        # Estimate tokens per message and remove until under limit
        while estimated_tokens > self.config.max_tokens_per_session and other_messages:
            removed_msg = other_messages.pop(0)  # Remove oldest
            # Rough token estimation
            estimated_tokens -= len(removed_msg.get("content", "")) // 4
        
        result_messages = system_messages + other_messages
        logger.info(f"Token management applied: {len(messages)} -> {len(result_messages)} messages")
        
        return result_messages
    
    async def _get_all_user_ids(self) -> List[str]:
        """Get all user IDs that have sessions.
        
        Returns:
            List of user IDs
        """
        # This is a simplified implementation
        # In a real system, you might want to track this more efficiently
        stats = await self.session_store.get_memory_stats()
        if stats["total_sessions"] == 0:
            return []
        
        # For now, we'll need to iterate through sessions to get unique user IDs
        # This could be optimized by maintaining a separate user index
        user_ids = set()
        for session in self.session_store.sessions.values():
            user_ids.add(session.user_id)
        
        return list(user_ids)
    
    async def _background_cleanup_loop(self) -> None:
        """Background task loop for automatic cleanup."""
        try:
            while True:
                await asyncio.sleep(self.config.cleanup_interval_minutes * 60)  # Convert to seconds
                try:
                    await self.cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Error during background cleanup: {e}")
        except asyncio.CancelledError:
            logger.info("Background cleanup task cancelled")
            raise