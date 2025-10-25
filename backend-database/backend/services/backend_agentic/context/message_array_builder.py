"""Message array builder for DeepSeek API integration."""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .models import Message, ConversationSession, ContextConfig

logger = logging.getLogger(__name__)


class TruncationStrategy(Enum):
    """Available truncation strategies for message arrays."""
    OLDEST_FIRST = "oldest_first"
    SLIDING_WINDOW = "sliding_window"
    IMPORTANCE_BASED = "importance_based"


@dataclass
class TokenEstimate:
    """Token estimation result."""
    total_tokens: int
    message_tokens: List[int]
    system_tokens: int
    user_tokens: int
    assistant_tokens: int


class MessageArrayBuilder:
    """Builds and manages message arrays for DeepSeek API calls."""
    
    def __init__(self, config: ContextConfig):
        """Initialize the message array builder.
        
        Args:
            config: Context configuration containing system prompt and limits
        """
        self.config = config
        self.system_prompt = config.system_prompt
        
    def build_messages(
        self, 
        conversation_history: List[Message], 
        current_query: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build a properly formatted message array for DeepSeek API.
        
        Args:
            conversation_history: List of messages from conversation session
            current_query: Optional current user query to append
            
        Returns:
            List of message dictionaries formatted for DeepSeek API
        """
        messages = []
        
        # Always start with system prompt if configured
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # Add conversation history
        for message in conversation_history:
            messages.append(message.to_dict())
        
        # Add current query if provided
        if current_query:
            messages.append({
                "role": "user", 
                "content": current_query
            })
        
        # Apply token management if enabled
        if self.config.enable_token_management:
            messages = self.truncate_if_needed(messages, self.config.max_tokens_per_session)
        
        logger.debug(f"Built message array with {len(messages)} messages")
        return messages
    
    def build_from_session(
        self, 
        session: ConversationSession, 
        current_query: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build message array from a conversation session.
        
        Args:
            session: Conversation session containing message history
            current_query: Optional current user query to append
            
        Returns:
            List of message dictionaries formatted for DeepSeek API
        """
        return self.build_messages(session.messages, current_query)
    
    def estimate_tokens(self, messages: List[Dict[str, str]]) -> TokenEstimate:
        """Estimate token count for a message array.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            TokenEstimate object with detailed token breakdown
        """
        message_tokens = []
        system_tokens = 0
        user_tokens = 0
        assistant_tokens = 0
        
        for message in messages:
            content = message.get("content", "")
            role = message.get("role", "")
            
            # Rough estimation: 1 token ≈ 4 characters for English text
            # Add some overhead for role and formatting
            token_count = len(content) // 4 + 10  # +10 for role and formatting overhead
            message_tokens.append(token_count)
            
            if role == "system":
                system_tokens += token_count
            elif role == "user":
                user_tokens += token_count
            elif role == "assistant":
                assistant_tokens += token_count
        
        total_tokens = sum(message_tokens)
        
        return TokenEstimate(
            total_tokens=total_tokens,
            message_tokens=message_tokens,
            system_tokens=system_tokens,
            user_tokens=user_tokens,
            assistant_tokens=assistant_tokens
        )
    
    def truncate_if_needed(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int
    ) -> List[Dict[str, str]]:
        """Truncate message array if it exceeds token limits.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum allowed tokens
            
        Returns:
            Truncated message array
        """
        token_estimate = self.estimate_tokens(messages)
        
        if token_estimate.total_tokens <= max_tokens:
            return messages
        
        logger.info(f"Message array exceeds token limit ({token_estimate.total_tokens} > {max_tokens}), applying truncation")
        
        strategy = TruncationStrategy(self.config.truncation_strategy)
        
        if strategy == TruncationStrategy.OLDEST_FIRST:
            return self._truncate_oldest_first(messages, max_tokens)
        elif strategy == TruncationStrategy.SLIDING_WINDOW:
            return self._truncate_sliding_window(messages, max_tokens)
        elif strategy == TruncationStrategy.IMPORTANCE_BASED:
            return self._truncate_importance_based(messages, max_tokens)
        else:
            # Fallback to oldest first
            return self._truncate_oldest_first(messages, max_tokens)
    
    def _truncate_oldest_first(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int
    ) -> List[Dict[str, str]]:
        """Truncate messages by removing oldest messages first.
        
        Preserves system messages and recent conversation context.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum allowed tokens
            
        Returns:
            Truncated message array
        """
        if not messages:
            return messages
        
        # Always preserve system messages
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        non_system_messages = [msg for msg in messages if msg.get("role") != "system"]
        
        # Calculate tokens for system messages
        system_tokens = self.estimate_tokens(system_messages).total_tokens
        available_tokens = max_tokens - system_tokens
        
        if available_tokens <= 0:
            logger.warning("System messages exceed token limit, returning system messages only")
            # If even system messages exceed limit, we still need to return something
            # Return system messages as they are essential
            return system_messages
        
        # Add non-system messages from newest to oldest until we hit the limit
        truncated_messages = []
        current_tokens = 0
        
        for message in reversed(non_system_messages):
            message_tokens = self.estimate_tokens([message]).total_tokens
            
            if current_tokens + message_tokens <= available_tokens:
                truncated_messages.insert(0, message)  # Insert at beginning to maintain order
                current_tokens += message_tokens
            else:
                break
        
        result = system_messages + truncated_messages
        final_tokens = self.estimate_tokens(result).total_tokens
        
        logger.info(f"Truncated from {len(messages)} to {len(result)} messages ({final_tokens} tokens)")
        return result
    
    def _truncate_sliding_window(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int
    ) -> List[Dict[str, str]]:
        """Truncate using sliding window approach.
        
        Keeps system messages, recent messages, and some older context.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum allowed tokens
            
        Returns:
            Truncated message array
        """
        if not messages:
            return messages
        
        # Always preserve system messages
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        non_system_messages = [msg for msg in messages if msg.get("role") != "system"]
        
        # Calculate tokens for system messages
        system_tokens = self.estimate_tokens(system_messages).total_tokens
        available_tokens = max_tokens - system_tokens
        
        if available_tokens <= 0:
            return system_messages
        
        # Reserve 70% of tokens for recent messages, 30% for older context
        recent_token_budget = int(available_tokens * 0.7)
        context_token_budget = available_tokens - recent_token_budget
        
        # Get recent messages (from end)
        recent_messages = []
        recent_tokens = 0
        
        for message in reversed(non_system_messages):
            message_tokens = self.estimate_tokens([message]).total_tokens
            
            if recent_tokens + message_tokens <= recent_token_budget:
                recent_messages.insert(0, message)
                recent_tokens += message_tokens
            else:
                break
        
        # Get older context messages (from beginning, excluding recent ones)
        remaining_messages = non_system_messages[:-len(recent_messages)] if recent_messages else non_system_messages
        context_messages = []
        context_tokens = 0
        
        for message in remaining_messages:
            message_tokens = self.estimate_tokens([message]).total_tokens
            
            if context_tokens + message_tokens <= context_token_budget:
                context_messages.append(message)
                context_tokens += message_tokens
            else:
                break
        
        result = system_messages + context_messages + recent_messages
        final_tokens = self.estimate_tokens(result).total_tokens
        
        logger.info(f"Sliding window truncated from {len(messages)} to {len(result)} messages ({final_tokens} tokens)")
        return result
    
    def _truncate_importance_based(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int
    ) -> List[Dict[str, str]]:
        """Truncate based on message importance scoring.
        
        Prioritizes system messages, recent messages, and messages with questions/answers.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum allowed tokens
            
        Returns:
            Truncated message array
        """
        if not messages:
            return messages
        
        # Score messages by importance
        scored_messages = []
        
        for i, message in enumerate(messages):
            role = message.get("role", "")
            content = message.get("content", "")
            
            # Base importance scores
            if role == "system":
                importance = 1000  # Always keep system messages
            elif role == "user":
                importance = 100
            elif role == "assistant":
                importance = 90
            else:
                importance = 50
            
            # Boost recent messages
            recency_boost = max(0, len(messages) - i) * 2
            importance += recency_boost
            
            # Boost messages with questions or important keywords
            if "?" in content:
                importance += 20
            if any(keyword in content.lower() for keyword in ["error", "problem", "help", "important"]):
                importance += 15
            
            scored_messages.append((importance, i, message))
        
        # Sort by importance (descending)
        scored_messages.sort(key=lambda x: x[0], reverse=True)
        
        # Select messages within token limit
        selected_messages = []
        current_tokens = 0
        
        for importance, original_index, message in scored_messages:
            message_tokens = self.estimate_tokens([message]).total_tokens
            
            if current_tokens + message_tokens <= max_tokens:
                selected_messages.append((original_index, message))
                current_tokens += message_tokens
        
        # Sort selected messages by original order
        selected_messages.sort(key=lambda x: x[0])
        result = [msg for _, msg in selected_messages]
        
        final_tokens = self.estimate_tokens(result).total_tokens
        logger.info(f"Importance-based truncated from {len(messages)} to {len(result)} messages ({final_tokens} tokens)")
        
        return result
    
    def get_message_stats(self, messages: List[Dict[str, str]]) -> Dict[str, int]:
        """Get statistics about a message array.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Dictionary with message statistics
        """
        token_estimate = self.estimate_tokens(messages)
        
        role_counts = {}
        for message in messages:
            role = message.get("role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1
        
        return {
            "total_messages": len(messages),
            "total_tokens": token_estimate.total_tokens,
            "system_messages": role_counts.get("system", 0),
            "user_messages": role_counts.get("user", 0),
            "assistant_messages": role_counts.get("assistant", 0),
            "system_tokens": token_estimate.system_tokens,
            "user_tokens": token_estimate.user_tokens,
            "assistant_tokens": token_estimate.assistant_tokens,
        }
    
    def validate_message_array(self, messages: List[Dict[str, str]]) -> Tuple[bool, List[str]]:
        """Validate a message array for DeepSeek API compatibility.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not messages:
            errors.append("Message array cannot be empty")
            return False, errors
        
        valid_roles = {"system", "user", "assistant"}
        
        for i, message in enumerate(messages):
            if not isinstance(message, dict):
                errors.append(f"Message {i} is not a dictionary")
                continue
            
            if "role" not in message:
                errors.append(f"Message {i} missing 'role' field")
            elif message["role"] not in valid_roles:
                errors.append(f"Message {i} has invalid role: {message['role']}")
            
            if "content" not in message:
                errors.append(f"Message {i} missing 'content' field")
            elif not isinstance(message["content"], str):
                errors.append(f"Message {i} content is not a string")
            elif not message["content"].strip():
                errors.append(f"Message {i} has empty content")
        
        # Check for proper conversation flow
        if len(messages) > 1:
            # Should not have consecutive messages from the same role (except system)
            for i in range(1, len(messages)):
                current_role = messages[i].get("role")
                previous_role = messages[i-1].get("role")
                
                if current_role == previous_role and current_role != "system":
                    errors.append(f"Messages {i-1} and {i} have consecutive {current_role} roles")
        
        return len(errors) == 0, errors