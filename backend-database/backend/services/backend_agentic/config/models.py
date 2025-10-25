"""Configuration data models with validation."""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, SecretStr, ConfigDict
from pathlib import Path


class DeepSeekConfig(BaseModel):
    """DeepSeek API configuration."""
    api_key: SecretStr = Field(..., description="DeepSeek API key")
    base_url: str = Field(default="https://api.deepseek.com", description="API base URL")
    model: str = Field(default="deepseek-chat", description="Model name")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    enable_mock_fallback: bool = Field(default=True, description="Enable fallback to mock responses")

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key format."""
        if v and not str(v.get_secret_value()).startswith(('sk-', 'test-')):
            raise ValueError("API key must start with 'sk-' or 'test-'")
        return v


class DataConfig(BaseModel):
    """Data management configuration."""
    csv_path: str = Field(default="data/test3.csv", description="Path to CSV data file")
    enable_hot_reload: bool = Field(default=True, description="Enable hot reload of data")
    validation_enabled: bool = Field(default=True, description="Enable data validation")

    @field_validator('csv_path')
    @classmethod
    def validate_csv_path(cls, v):
        """Validate CSV file path."""
        if not v.endswith('.csv'):
            raise ValueError("CSV path must end with .csv")
        return v


class ScraperConfig(BaseModel):
    """Web scraper configuration."""
    timeout: int = Field(default=30, ge=1, le=300, description="Scraping timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    user_agent: str = Field(default="AgenticBackend/1.0", description="User agent string")
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt")
    delay_between_requests: float = Field(default=1.0, ge=0.0, description="Delay between requests")


class QdrantConfig(BaseModel):
    """Qdrant document store configuration."""
    host: str = Field(default="localhost", description="Qdrant host")
    port: int = Field(default=6333, ge=1, le=65535, description="Qdrant port")
    collection_name: str = Field(default="company_documents", description="Collection name")
    vector_size: int = Field(default=384, ge=1, description="Vector dimension size")
    distance: Literal["Cosine", "Euclid", "Dot"] = Field(default="Cosine", description="Distance metric")


class FaissConfig(BaseModel):
    """FAISS document store configuration."""
    index_path: str = Field(default="./data/faiss_index", description="FAISS index file path")
    index_type: str = Field(default="IndexFlatIP", description="FAISS index type")


class InMemoryConfig(BaseModel):
    """In-memory document store configuration."""
    embedding_dim: int = Field(default=384, ge=1, description="Embedding dimension")


class HaystackConfig(BaseModel):
    """Haystack RAG system configuration."""
    document_store: Literal["qdrant", "faiss", "inmemory"] = Field(
        default="inmemory", description="Document store type"
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        description="Embedding model name"
    )
    top_k: int = Field(default=5, ge=1, le=100, description="Number of top results to retrieve")
    index_name: str = Field(default="company_knowledge_base", description="Index name")
    
    # Document store specific configs
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    faiss: FaissConfig = Field(default_factory=FaissConfig)
    inmemory: InMemoryConfig = Field(default_factory=InMemoryConfig)


class LangGraphConfig(BaseModel):
    """LangGraph workflow configuration."""
    recursion_limit: int = Field(default=50, ge=1, le=1000, description="Maximum recursion depth")
    checkpoint_enabled: bool = Field(default=True, description="Enable workflow checkpoints")
    debug_mode: bool = Field(default=False, description="Enable debug mode")


class SystemConfig(BaseModel):
    """System-wide configuration."""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    max_concurrent_tools: int = Field(default=3, ge=1, le=20, description="Maximum concurrent tool executions")
    environment: Literal["development", "production", "testing"] = Field(
        default="development", description="Environment name"
    )


class AppConfig(BaseModel):
    """Main application configuration."""
    deepseek: DeepSeekConfig
    data: DataConfig
    scraper: ScraperConfig
    haystack: HaystackConfig
    langgraph: LangGraphConfig
    system: SystemConfig

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    def get_document_store_config(self) -> Dict[str, Any]:
        """Get the active document store configuration."""
        store_type = self.haystack.document_store
        if store_type == "qdrant":
            return self.haystack.qdrant.model_dump()
        elif store_type == "faiss":
            return self.haystack.faiss.model_dump()
        elif store_type == "inmemory":
            return self.haystack.inmemory.model_dump()
        else:
            raise ValueError(f"Unknown document store type: {store_type}")

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.system.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.system.environment == "development"

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.system.environment == "testing"