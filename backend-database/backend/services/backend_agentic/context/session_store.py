"""Session storage implementation for context management."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from threading import Lock
import uuid

from .models import ConversationSession, ContextConfig

# Import agentic logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentic_logging import get_agentic_logger

logger = get_agentic_logger('context.session_store')


class SessionStore:
    """In-memory storage for conversation sessions with automatic cleanup."""
    
    def __init__(self, max_sessions: int = 1000):
        """Initialize the session store.
        
        Args:
            max_sessions: Maximum number of sessions to store in memory
        """
        self.sessions: Dict[str, ConversationSession] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> set of session_ids
        self.max_sessions = max_sessions
        self._lock = Lock()  # Thread safety for concurrent access
        
        logger.info(f"SessionStore initialized with max_sessions={max_sessions}")
    
    async def create_session(self, user_id: str, session_id: Optional[str] = None) -> ConversationSession:
        """Create a new conversation session.
        
        Args:
            user_id: ID of the user creating the session
            session_id: Optional specific session ID, generates UUID if None
            
        Returns:
            ConversationSession: The created session
            
        Raises:
            ValueError: If session_id already exists
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        with self._lock:
            if session_id in self.sessions:
                raise ValueError(f"Session {session_id} already exists")
            
            # Check if we need to cleanup old sessions to make room
            if len(self.sessions) >= self.max_sessions:
                await self._cleanup_oldest_sessions(1)
            
            # Create new session
            session = ConversationSession.create_new(user_id=user_id, session_id=session_id)
            self.sessions[session_id] = session
            
            # Track user sessions
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session
    
    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Retrieve a session by ID.
        
        Args:
            session_id: ID of the session to retrieve
            
        Returns:
            ConversationSession or None if not found
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                # Update last activity when accessed
                session.last_activity = datetime.now()
                logger.debug(f"Retrieved session {session_id}")
            else:
                logger.debug(f"Session {session_id} not found")
            return session
    
    async def update_session(self, session_id: str, session: ConversationSession) -> None:
        """Update an existing session.
        
        Args:
            session_id: ID of the session to update
            session: Updated session object
            
        Raises:
            ValueError: If session doesn't exist
        """
        with self._lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} does not exist")
            
            # Ensure session_id matches
            session.session_id = session_id
            # Don't automatically update last_activity - preserve the session's current state
            
            self.sessions[session_id] = session
            logger.debug(f"Updated session {session_id}")
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            bool: True if session was deleted, False if not found
        """
        with self._lock:
            session = self.sessions.pop(session_id, None)
            if session:
                # Remove from user sessions tracking
                user_id = session.user_id
                if user_id in self.user_sessions:
                    self.user_sessions[user_id].discard(session_id)
                    # Clean up empty user session sets
                    if not self.user_sessions[user_id]:
                        del self.user_sessions[user_id]
                
                logger.info(f"Deleted session {session_id} for user {user_id}")
                return True
            else:
                logger.debug(f"Session {session_id} not found for deletion")
                return False
    
    async def get_user_sessions(self, user_id: str) -> List[ConversationSession]:
        """Get all sessions for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of ConversationSession objects for the user
        """
        with self._lock:
            user_session_ids = self.user_sessions.get(user_id, set())
            sessions = []
            for session_id in user_session_ids:
                session = self.sessions.get(session_id)
                if session:
                    sessions.append(session)
            
            logger.debug(f"Retrieved {len(sessions)} sessions for user {user_id}")
            return sessions
    
    async def cleanup_expired(self, timeout_minutes: int) -> int:
        """Clean up expired sessions based on timeout.
        
        Args:
            timeout_minutes: Session timeout in minutes
            
        Returns:
            int: Number of sessions cleaned up
        """
        expired_sessions = []
        current_time = datetime.now()
        timeout_delta = timedelta(minutes=timeout_minutes)
        
        with self._lock:
            for session_id, session in self.sessions.items():
                if current_time - session.last_activity > timeout_delta:
                    expired_sessions.append(session_id)
        
        # Delete expired sessions (outside the lock to avoid deadlock)
        cleanup_count = 0
        for session_id in expired_sessions:
            if await self.delete_session(session_id):
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} expired sessions")
        
        return cleanup_count
    
    async def cleanup_user_sessions(self, user_id: str, max_sessions_per_user: int) -> int:
        """Clean up oldest sessions for a user if they exceed the limit.
        
        Args:
            user_id: ID of the user
            max_sessions_per_user: Maximum sessions allowed per user
            
        Returns:
            int: Number of sessions cleaned up
        """
        user_sessions = await self.get_user_sessions(user_id)
        
        if len(user_sessions) <= max_sessions_per_user:
            return 0
        
        # Sort by last activity (oldest first)
        user_sessions.sort(key=lambda s: s.last_activity)
        
        # Delete oldest sessions
        sessions_to_delete = len(user_sessions) - max_sessions_per_user
        cleanup_count = 0
        
        for i in range(sessions_to_delete):
            session = user_sessions[i]
            if await self.delete_session(session.session_id):
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} excess sessions for user {user_id}")
        
        return cleanup_count
    
    async def get_session_count(self) -> int:
        """Get total number of active sessions.
        
        Returns:
            int: Number of active sessions
        """
        with self._lock:
            return len(self.sessions)
    
    async def get_user_session_count(self, user_id: str) -> int:
        """Get number of sessions for a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            int: Number of sessions for the user
        """
        with self._lock:
            return len(self.user_sessions.get(user_id, set()))
    
    async def get_memory_stats(self) -> Dict[str, int]:
        """Get memory usage statistics.
        
        Returns:
            Dict with memory statistics
        """
        with self._lock:
            total_sessions = len(self.sessions)
            total_users = len(self.user_sessions)
            total_messages = sum(session.get_message_count() for session in self.sessions.values())
            
            return {
                "total_sessions": total_sessions,
                "total_users": total_users,
                "total_messages": total_messages,
                "max_sessions": self.max_sessions,
                "memory_usage_percent": (total_sessions / self.max_sessions) * 100 if self.max_sessions > 0 else 0
            }
    
    async def clear_all_sessions(self) -> int:
        """Clear all sessions from storage.
        
        Returns:
            int: Number of sessions cleared
        """
        with self._lock:
            count = len(self.sessions)
            self.sessions.clear()
            self.user_sessions.clear()
            
            logger.info(f"Cleared all {count} sessions from storage")
            return count
    
    async def _cleanup_oldest_sessions(self, count: int) -> int:
        """Internal method to cleanup oldest sessions.
        
        Args:
            count: Number of sessions to cleanup
            
        Returns:
            int: Number of sessions actually cleaned up
        """
        if not self.sessions:
            return 0
        
        # Get sessions sorted by last activity (oldest first)
        sessions_by_activity = sorted(
            self.sessions.items(),
            key=lambda item: item[1].last_activity
        )
        
        cleanup_count = 0
        for i in range(min(count, len(sessions_by_activity))):
            session_id, _ = sessions_by_activity[i]
            if await self.delete_session(session_id):
                cleanup_count += 1
        
        return cleanup_count
    
    async def health_check(self) -> Dict[str, any]:
        """Perform health check on the session store.
        
        Returns:
            Dict with health check results
        """
        stats = await self.get_memory_stats()
        
        # Check for potential issues
        issues = []
        if stats["memory_usage_percent"] > 90:
            issues.append("High memory usage")
        
        if stats["total_sessions"] == 0 and stats["total_users"] > 0:
            issues.append("Inconsistent user tracking")
        
        return {
            "status": "healthy" if not issues else "warning",
            "issues": issues,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }