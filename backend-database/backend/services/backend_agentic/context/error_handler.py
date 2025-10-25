"""Error handling and fallback mechanisms for context management."""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from .models import ConversationSession, ContextConfig, Message
from .session_store import SessionStore

# Import with try/except to handle circular imports and testing
try:
    from llm.deepseek_client import DeepSeekClient, APIResponse
except ImportError:
    # For testing or when running from different contexts
    DeepSeekClient = None
    APIResponse = None

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of context-related errors."""
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_CORRUPTED = "session_corrupted"
    TOKEN_LIMIT_EXCEEDED = "token_limit_exceeded"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    API_ERROR = "api_error"
    MEMORY_PRESSURE = "memory_pressure"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    error_type: ErrorType
    original_error: Exception
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    retry_count: int = 0
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FallbackResult:
    """Result of fallback processing."""
    success: bool
    response: Optional[APIResponse] = None
    session: Optional[ConversationSession] = None
    fallback_method: str = ""
    error_message: str = ""
    recovery_actions: List[str] = None
    
    def __post_init__(self):
        if self.recovery_actions is None:
            self.recovery_actions = []


class ContextErrorHandler:
    """Handles context-related errors and provides fallback mechanisms."""
    
    def __init__(
        self, 
        session_store: SessionStore, 
        config: ContextConfig,
        deepseek_client: Optional[DeepSeekClient] = None
    ):
        """Initialize the error handler.
        
        Args:
            session_store: Session storage backend
            config: Context configuration
            deepseek_client: Optional DeepSeek client for fallback processing
        """
        self.session_store = session_store
        self.config = config
        self.deepseek_client = deepseek_client
        
        # Rate limiting tracking
        self._rate_limit_backoff: Dict[str, datetime] = {}
        self._rate_limit_attempts: Dict[str, int] = {}
        
        # Error statistics
        self._error_stats: Dict[ErrorType, int] = {error_type: 0 for error_type in ErrorType}
        self._recovery_stats: Dict[str, int] = {}
        
        logger.info("ContextErrorHandler initialized")
    
    async def handle_session_error(
        self, 
        error: Exception, 
        user_id: str, 
        session_id: Optional[str] = None
    ) -> FallbackResult:
        """Handle session-related errors with recovery mechanisms.
        
        Args:
            error: The original error
            user_id: ID of the user
            session_id: Optional session ID that caused the error
            
        Returns:
            FallbackResult with recovery information
        """
        error_context = ErrorContext(
            error_type=self._classify_session_error(error),
            original_error=error,
            session_id=session_id,
            user_id=user_id
        )
        
        self._record_error(error_context.error_type)
        
        logger.warning(f"Handling session error: {error_context.error_type.value} for user {user_id}")
        
        try:
            if error_context.error_type == ErrorType.SESSION_NOT_FOUND:
                return await self._recover_missing_session(error_context)
            
            elif error_context.error_type == ErrorType.SESSION_CORRUPTED:
                return await self._recover_corrupted_session(error_context)
            
            elif error_context.error_type == ErrorType.MEMORY_PRESSURE:
                return await self._handle_memory_pressure(error_context)
            
            else:
                # Generic session recovery
                return await self._generic_session_recovery(error_context)
                
        except Exception as recovery_error:
            logger.error(f"Session recovery failed: {recovery_error}")
            return FallbackResult(
                success=False,
                error_message=f"Session recovery failed: {str(recovery_error)}",
                fallback_method="none"
            )
    
    async def handle_token_limit_exceeded(
        self, 
        session: ConversationSession, 
        max_tokens: int
    ) -> FallbackResult:
        """Handle token limit exceeded with automatic truncation.
        
        Args:
            session: The session that exceeded token limits
            max_tokens: Maximum allowed tokens
            
        Returns:
            FallbackResult with truncated session
        """
        error_context = ErrorContext(
            error_type=ErrorType.TOKEN_LIMIT_EXCEEDED,
            original_error=Exception(f"Token limit exceeded: {session.get_token_estimate()} > {max_tokens}"),
            session_id=session.session_id,
            user_id=session.user_id
        )
        
        self._record_error(ErrorType.TOKEN_LIMIT_EXCEEDED)
        
        logger.info(f"Handling token limit exceeded for session {session.session_id}")
        
        try:
            # Apply truncation strategy
            truncated_session = await self._apply_token_truncation(session, max_tokens)
            
            # Update session in store
            await self.session_store.update_session(session.session_id, truncated_session)
            
            recovery_actions = [
                f"Applied {self.config.truncation_strategy} truncation",
                f"Reduced from {session.get_message_count()} to {truncated_session.get_message_count()} messages",
                f"Token estimate: {truncated_session.get_token_estimate()}"
            ]
            
            self._record_recovery("token_truncation")
            
            return FallbackResult(
                success=True,
                session=truncated_session,
                fallback_method="token_truncation",
                recovery_actions=recovery_actions
            )
            
        except Exception as truncation_error:
            logger.error(f"Token truncation failed: {truncation_error}")
            
            # Fallback to clearing session
            try:
                session.clear_messages()
                if self.config.system_prompt:
                    session.add_message("system", self.config.system_prompt)
                
                await self.session_store.update_session(session.session_id, session)
                
                return FallbackResult(
                    success=True,
                    session=session,
                    fallback_method="session_reset",
                    recovery_actions=["Cleared all messages", "Reset to system prompt only"]
                )
                
            except Exception as reset_error:
                return FallbackResult(
                    success=False,
                    error_message=f"Token limit recovery failed: {str(reset_error)}",
                    fallback_method="none"
                )
    
    async def handle_rate_limit_error(
        self, 
        error: Exception, 
        user_id: str,
        retry_count: int = 0
    ) -> FallbackResult:
        """Handle rate limiting with exponential backoff.
        
        Args:
            error: The rate limit error
            user_id: ID of the user
            retry_count: Current retry attempt
            
        Returns:
            FallbackResult with backoff information
        """
        error_context = ErrorContext(
            error_type=ErrorType.RATE_LIMIT_EXCEEDED,
            original_error=error,
            user_id=user_id,
            retry_count=retry_count
        )
        
        self._record_error(ErrorType.RATE_LIMIT_EXCEEDED)
        
        # Calculate backoff time
        base_delay = 2 ** min(retry_count, 6)  # Cap at 64 seconds
        jitter = random.uniform(0.1, 0.3) * base_delay  # Add jitter
        backoff_seconds = base_delay + jitter
        
        # Track rate limit for this user
        backoff_until = datetime.now() + timedelta(seconds=backoff_seconds)
        self._rate_limit_backoff[user_id] = backoff_until
        self._rate_limit_attempts[user_id] = retry_count + 1
        
        logger.warning(f"Rate limit hit for user {user_id}, backing off for {backoff_seconds:.1f}s")
        
        # Wait for backoff period
        await asyncio.sleep(backoff_seconds)
        
        # Clear backoff tracking
        self._rate_limit_backoff.pop(user_id, None)
        
        recovery_actions = [
            f"Applied exponential backoff: {backoff_seconds:.1f}s",
            f"Retry attempt: {retry_count + 1}",
            "Rate limit backoff completed"
        ]
        
        self._record_recovery("rate_limit_backoff")
        
        return FallbackResult(
            success=True,
            fallback_method="exponential_backoff",
            recovery_actions=recovery_actions
        )
    
    async def handle_api_error(
        self, 
        error: Exception, 
        fallback_prompt: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> FallbackResult:
        """Handle API errors with fallback to stateless processing.
        
        Args:
            error: The API error
            fallback_prompt: Prompt to use for stateless fallback
            user_id: ID of the user
            session_id: Optional session ID
            
        Returns:
            FallbackResult with stateless response
        """
        error_context = ErrorContext(
            error_type=self._classify_api_error(error),
            original_error=error,
            user_id=user_id,
            session_id=session_id
        )
        
        self._record_error(error_context.error_type)
        
        logger.warning(f"Handling API error: {error_context.error_type.value} for user {user_id}")
        
        try:
            # Attempt stateless fallback if DeepSeek client is available
            if self.deepseek_client:
                logger.info("Attempting stateless fallback processing")
                
                # Use basic generate_response method (stateless)
                response = await self.deepseek_client.generate_response(
                    fallback_prompt,
                    system_message=self.config.system_prompt
                )
                
                # Mark as fallback response
                response.fallback_used = True
                
                recovery_actions = [
                    "Switched to stateless processing",
                    "Context history not available in response",
                    f"Fallback response status: {response.status}"
                ]
                
                self._record_recovery("stateless_fallback")
                
                return FallbackResult(
                    success=True,
                    response=response,
                    fallback_method="stateless_processing",
                    recovery_actions=recovery_actions
                )
            
            else:
                # No client available, return error response
                if APIResponse:
                    error_response = APIResponse(
                        content=f"Service temporarily unavailable: {str(error)}",
                        status="error",
                        usage={},
                        model="fallback",
                        validation_result={"is_valid": False, "errors": [str(error)]},
                        fallback_used=True,
                        timestamp=datetime.now(),
                        execution_time=0.0
                    )
                else:
                    # Fallback response structure for testing
                    error_response = type('APIResponse', (), {
                        'content': f"Service temporarily unavailable: {str(error)}",
                        'status': "error",
                        'usage': {},
                        'model': "fallback",
                        'validation_result': {"is_valid": False, "errors": [str(error)]},
                        'fallback_used': True,
                        'timestamp': datetime.now(),
                        'execution_time': 0.0
                    })()
                
                return FallbackResult(
                    success=False,
                    response=error_response,
                    fallback_method="error_response",
                    error_message=str(error)
                )
                
        except Exception as fallback_error:
            logger.error(f"Stateless fallback failed: {fallback_error}")
            
            # Return error response
            if APIResponse:
                error_response = APIResponse(
                    content=f"Service error: {str(fallback_error)}",
                    status="error",
                    usage={},
                    model="fallback",
                    validation_result={"is_valid": False, "errors": [str(fallback_error)]},
                    fallback_used=True,
                    timestamp=datetime.now(),
                    execution_time=0.0
                )
            else:
                # Fallback response structure for testing
                error_response = type('APIResponse', (), {
                    'content': f"Service error: {str(fallback_error)}",
                    'status': "error",
                    'usage': {},
                    'model': "fallback",
                    'validation_result': {"is_valid": False, "errors": [str(fallback_error)]},
                    'fallback_used': True,
                    'timestamp': datetime.now(),
                    'execution_time': 0.0
                })()
            
            return FallbackResult(
                success=False,
                response=error_response,
                fallback_method="error_response",
                error_message=str(fallback_error)
            )
    
    async def is_rate_limited(self, user_id: str) -> bool:
        """Check if user is currently rate limited.
        
        Args:
            user_id: ID of the user to check
            
        Returns:
            bool: True if user is rate limited
        """
        if user_id not in self._rate_limit_backoff:
            return False
        
        backoff_until = self._rate_limit_backoff[user_id]
        if datetime.now() >= backoff_until:
            # Backoff period expired
            self._rate_limit_backoff.pop(user_id, None)
            self._rate_limit_attempts.pop(user_id, None)
            return False
        
        return True
    
    async def get_rate_limit_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get rate limit information for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dict with rate limit info or None if not rate limited
        """
        if not await self.is_rate_limited(user_id):
            return None
        
        backoff_until = self._rate_limit_backoff[user_id]
        remaining_seconds = (backoff_until - datetime.now()).total_seconds()
        
        return {
            "is_rate_limited": True,
            "backoff_until": backoff_until.isoformat(),
            "remaining_seconds": max(0, remaining_seconds),
            "retry_count": self._rate_limit_attempts.get(user_id, 0)
        }
    
    async def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics.
        
        Returns:
            Dict with error and recovery statistics
        """
        return {
            "error_counts": {error_type.value: count for error_type, count in self._error_stats.items()},
            "recovery_counts": dict(self._recovery_stats),
            "active_rate_limits": len(self._rate_limit_backoff),
            "total_errors": sum(self._error_stats.values()),
            "total_recoveries": sum(self._recovery_stats.values())
        }
    
    async def reset_statistics(self) -> None:
        """Reset error handling statistics."""
        self._error_stats = {error_type: 0 for error_type in ErrorType}
        self._recovery_stats.clear()
        logger.info("Error handling statistics reset")
    
    def _classify_session_error(self, error: Exception) -> ErrorType:
        """Classify session-related errors.
        
        Args:
            error: The error to classify
            
        Returns:
            ErrorType: The classified error type
        """
        error_str = str(error).lower()
        
        if "not found" in error_str or "does not exist" in error_str:
            return ErrorType.SESSION_NOT_FOUND
        elif "corrupted" in error_str or "invalid" in error_str:
            return ErrorType.SESSION_CORRUPTED
        elif "memory" in error_str or "limit" in error_str:
            return ErrorType.MEMORY_PRESSURE
        else:
            return ErrorType.VALIDATION_ERROR
    
    def _classify_api_error(self, error: Exception) -> ErrorType:
        """Classify API-related errors.
        
        Args:
            error: The error to classify
            
        Returns:
            ErrorType: The classified error type
        """
        error_str = str(error).lower()
        
        if "rate limit" in error_str or "429" in error_str:
            return ErrorType.RATE_LIMIT_EXCEEDED
        elif "timeout" in error_str:
            return ErrorType.TIMEOUT_ERROR
        elif "network" in error_str or "connection" in error_str:
            return ErrorType.NETWORK_ERROR
        else:
            return ErrorType.API_ERROR
    
    def _record_error(self, error_type: ErrorType) -> None:
        """Record error occurrence for statistics.
        
        Args:
            error_type: The type of error that occurred
        """
        self._error_stats[error_type] += 1
    
    def _record_recovery(self, recovery_method: str) -> None:
        """Record successful recovery for statistics.
        
        Args:
            recovery_method: The recovery method that was used
        """
        self._recovery_stats[recovery_method] = self._recovery_stats.get(recovery_method, 0) + 1
    
    async def _recover_missing_session(self, error_context: ErrorContext) -> FallbackResult:
        """Recover from missing session by creating a new one.
        
        Args:
            error_context: Context information about the error
            
        Returns:
            FallbackResult with new session
        """
        try:
            # Create new session for the user
            new_session = await self.session_store.create_session(
                error_context.user_id, 
                error_context.session_id
            )
            
            # Add system message if configured
            if self.config.system_prompt:
                new_session.add_message("system", self.config.system_prompt)
                await self.session_store.update_session(new_session.session_id, new_session)
            
            recovery_actions = [
                f"Created new session: {new_session.session_id}",
                "Added system prompt",
                "Session ready for use"
            ]
            
            self._record_recovery("session_creation")
            
            return FallbackResult(
                success=True,
                session=new_session,
                fallback_method="create_new_session",
                recovery_actions=recovery_actions
            )
            
        except Exception as recovery_error:
            return FallbackResult(
                success=False,
                error_message=f"Failed to create new session: {str(recovery_error)}",
                fallback_method="none"
            )
    
    async def _recover_corrupted_session(self, error_context: ErrorContext) -> FallbackResult:
        """Recover from corrupted session by resetting it.
        
        Args:
            error_context: Context information about the error
            
        Returns:
            FallbackResult with recovered session
        """
        try:
            if error_context.session_id:
                # Try to get the session and reset it
                session = await self.session_store.get_session(error_context.session_id)
                if session:
                    # Clear corrupted data
                    session.clear_messages()
                    session.metadata.clear()
                    
                    # Re-initialize with system prompt
                    if self.config.system_prompt:
                        session.add_message("system", self.config.system_prompt)
                    
                    await self.session_store.update_session(session.session_id, session)
                    
                    recovery_actions = [
                        "Cleared corrupted session data",
                        "Reset to system prompt only",
                        "Session recovered and ready"
                    ]
                    
                    self._record_recovery("session_reset")
                    
                    return FallbackResult(
                        success=True,
                        session=session,
                        fallback_method="session_reset",
                        recovery_actions=recovery_actions
                    )
            
            # If session doesn't exist or session_id is None, create new one
            return await self._recover_missing_session(error_context)
            
        except Exception as recovery_error:
            return FallbackResult(
                success=False,
                error_message=f"Failed to recover corrupted session: {str(recovery_error)}",
                fallback_method="none"
            )
    
    async def _handle_memory_pressure(self, error_context: ErrorContext) -> FallbackResult:
        """Handle memory pressure by cleaning up sessions.
        
        Args:
            error_context: Context information about the error
            
        Returns:
            FallbackResult with cleanup information
        """
        try:
            # Perform aggressive cleanup
            expired_count = await self.session_store.cleanup_expired(
                self.config.session_timeout_minutes // 2  # More aggressive timeout
            )
            
            # Also cleanup excess user sessions
            user_cleanup_count = 0
            if error_context.user_id:
                user_cleanup_count = await self.session_store.cleanup_user_sessions(
                    error_context.user_id, 
                    self.config.max_sessions_per_user // 2  # Keep fewer sessions
                )
            
            # Try to create/recover the needed session
            recovery_result = await self._recover_missing_session(error_context)
            
            recovery_actions = [
                f"Cleaned up {expired_count} expired sessions",
                f"Cleaned up {user_cleanup_count} excess user sessions",
                "Memory pressure reduced"
            ]
            
            if recovery_result.success:
                recovery_actions.extend(recovery_result.recovery_actions)
            
            self._record_recovery("memory_cleanup")
            
            return FallbackResult(
                success=recovery_result.success,
                session=recovery_result.session,
                fallback_method="memory_cleanup",
                recovery_actions=recovery_actions,
                error_message=recovery_result.error_message
            )
            
        except Exception as cleanup_error:
            return FallbackResult(
                success=False,
                error_message=f"Memory cleanup failed: {str(cleanup_error)}",
                fallback_method="none"
            )
    
    async def _generic_session_recovery(self, error_context: ErrorContext) -> FallbackResult:
        """Generic session recovery for unclassified errors.
        
        Args:
            error_context: Context information about the error
            
        Returns:
            FallbackResult with recovery attempt
        """
        try:
            # Try to create a new session as fallback
            recovery_result = await self._recover_missing_session(error_context)
            
            recovery_actions = [
                f"Generic recovery for {error_context.error_type.value}",
                "Attempted session recreation"
            ]
            
            if recovery_result.success:
                recovery_actions.extend(recovery_result.recovery_actions)
            
            self._record_recovery("generic_recovery")
            
            return FallbackResult(
                success=recovery_result.success,
                session=recovery_result.session,
                fallback_method="generic_recovery",
                recovery_actions=recovery_actions,
                error_message=recovery_result.error_message
            )
            
        except Exception as recovery_error:
            return FallbackResult(
                success=False,
                error_message=f"Generic recovery failed: {str(recovery_error)}",
                fallback_method="none"
            )
    
    async def _apply_token_truncation(
        self, 
        session: ConversationSession, 
        max_tokens: int
    ) -> ConversationSession:
        """Apply token truncation to a session.
        
        Args:
            session: The session to truncate
            max_tokens: Maximum allowed tokens
            
        Returns:
            ConversationSession: The truncated session
        """
        if session.get_token_estimate() <= max_tokens:
            return session
        
        # Create a copy to avoid modifying the original
        truncated_session = ConversationSession(
            session_id=session.session_id,
            user_id=session.user_id,
            messages=session.messages.copy(),
            created_at=session.created_at,
            last_activity=session.last_activity,
            metadata=session.metadata.copy()
        )
        
        if self.config.truncation_strategy == "oldest_first":
            await self._truncate_oldest_first(truncated_session, max_tokens)
        elif self.config.truncation_strategy == "sliding_window":
            await self._truncate_sliding_window(truncated_session, max_tokens)
        else:
            # Default to oldest_first
            await self._truncate_oldest_first(truncated_session, max_tokens)
        
        return truncated_session
    
    async def _truncate_oldest_first(
        self, 
        session: ConversationSession, 
        max_tokens: int
    ) -> None:
        """Truncate oldest messages first, preserving system messages.
        
        Args:
            session: The session to truncate
            max_tokens: Maximum allowed tokens
        """
        # Separate system messages from others
        system_messages = [msg for msg in session.messages if msg.role == "system"]
        other_messages = [msg for msg in session.messages if msg.role != "system"]
        
        # Calculate tokens for system messages
        system_tokens = sum(len(msg.content) // 4 for msg in system_messages)
        available_tokens = max_tokens - system_tokens
        
        # Remove oldest messages until under limit
        current_tokens = sum(len(msg.content) // 4 for msg in other_messages)
        
        while current_tokens > available_tokens and other_messages:
            removed_msg = other_messages.pop(0)
            current_tokens -= len(removed_msg.content) // 4
        
        # Reconstruct message list
        session.messages = system_messages + other_messages
    
    async def _truncate_sliding_window(
        self, 
        session: ConversationSession, 
        max_tokens: int
    ) -> None:
        """Keep recent messages in a sliding window, preserving system messages.
        
        Args:
            session: The session to truncate
            max_tokens: Maximum allowed tokens
        """
        # Separate system messages from others
        system_messages = [msg for msg in session.messages if msg.role == "system"]
        other_messages = [msg for msg in session.messages if msg.role != "system"]
        
        # Calculate tokens for system messages
        system_tokens = sum(len(msg.content) // 4 for msg in system_messages)
        available_tokens = max_tokens - system_tokens
        
        # Keep most recent messages that fit in available tokens
        kept_messages = []
        current_tokens = 0
        
        for msg in reversed(other_messages):
            msg_tokens = len(msg.content) // 4
            if current_tokens + msg_tokens <= available_tokens:
                kept_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        # Reconstruct message list
        session.messages = system_messages + kept_messages