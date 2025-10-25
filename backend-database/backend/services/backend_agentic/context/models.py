"""Data models for context management."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, field_validator
import uuid


@dataclass
class Message:
    """Represents a single message in a conversation."""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, str]:
        """Convert message to dictionary format for DeepSeek API."""
        return {"role": self.role, "content": self.content}
    
    def __post_init__(self):
        """Validate message after initialization."""
        if self.role not in ["system", "user", "assistant"]:
            raise ValueError(f"Invalid role: {self.role}. Must be 'system', 'user', or 'assistant'")
        if not self.content.strip():
            raise ValueError("Message content cannot be empty")


@dataclass
class ConversationSession:
    """Represents a conversation session with message history."""
    session_id: str
    user_id: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a message to the conversation."""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_activity = datetime.now()
    
    def get_message_count(self) -> int:
        """Get the total number of messages in the session."""
        return len(self.messages)
    
    def get_token_estimate(self) -> int:
        """Estimate token count for all messages (rough approximation)."""
        total_chars = sum(len(msg.content) for msg in self.messages)
        # Rough estimate: 1 token ≈ 4 characters for English text
        return total_chars // 4
    
    def is_expired(self, timeout_minutes: int) -> bool:
        """Check if the session has expired based on last activity."""
        timeout_delta = timedelta(minutes=timeout_minutes)
        return datetime.now() - self.last_activity > timeout_delta
    
    def get_messages_as_dict_list(self) -> List[Dict[str, str]]:
        """Get all messages as a list of dictionaries for API calls."""
        return [msg.to_dict() for msg in self.messages]
    
    def clear_messages(self) -> None:
        """Clear all messages from the session."""
        self.messages.clear()
        self.last_activity = datetime.now()
    
    def get_user_messages_count(self) -> int:
        """Get count of user messages only."""
        return sum(1 for msg in self.messages if msg.role == "user")
    
    def get_assistant_messages_count(self) -> int:
        """Get count of assistant messages only."""
        return sum(1 for msg in self.messages if msg.role == "assistant")
    
    @classmethod
    def create_new(cls, user_id: str, session_id: Optional[str] = None) -> "ConversationSession":
        """Create a new conversation session."""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        return cls(
            session_id=session_id,
            user_id=user_id
        )


class ContextConfig(BaseModel):
    """Configuration for context management system."""
    max_messages_per_session: int = Field(
        default=50, 
        ge=1, 
        le=1000, 
        description="Maximum messages per session"
    )
    max_tokens_per_session: int = Field(
        default=20000, 
        ge=100, 
        le=100000, 
        description="Maximum tokens per session"
    )
    session_timeout_minutes: int = Field(
        default=30, 
        ge=1, 
        le=1440, 
        description="Session timeout in minutes"
    )
    cleanup_interval_minutes: int = Field(
        default=5, 
        ge=1, 
        le=60, 
        description="Cleanup interval in minutes"
    )
    system_prompt: str = Field(
        default="You are a helpful AI assistant for lead generation and business analysis.",
        description="Default system prompt for conversations"
    )
    enable_token_management: bool = Field(
        default=True, 
        description="Enable token counting and management"
    )
    truncation_strategy: str = Field(
        default="oldest_first", 
        description="Strategy for message truncation"
    )
    max_sessions_per_user: int = Field(
        default=10, 
        ge=1, 
        le=100, 
        description="Maximum concurrent sessions per user"
    )
    
    @field_validator('truncation_strategy')
    @classmethod
    def validate_truncation_strategy(cls, v):
        """Validate truncation strategy."""
        valid_strategies = ["oldest_first", "sliding_window", "importance_based"]
        if v not in valid_strategies:
            raise ValueError(f"Invalid truncation strategy: {v}. Must be one of {valid_strategies}")
        return v