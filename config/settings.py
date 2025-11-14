"""
Application configuration using pydantic-settings.
Loads configuration from environment variables, .env file, or Google Secret Manager.

Priority for API keys:
1. Google Secret Manager (if GCP_PROJECT_ID is set)
2. Environment variables
3. .env file
"""
import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Google Cloud Configuration
    gcp_project_id: Optional[str] = Field(
        default=None,
        description="GCP project ID for Secret Manager (auto-detected in Cloud Run)"
    )
    use_secret_manager: bool = Field(
        default=True,
        description="Use Google Secret Manager for API keys (falls back to env vars)"
    )

    # LLM Configuration
    llm_provider: str = Field(default="gemini", description="LLM provider (gemini, openai, anthropic)")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-2.0-flash-exp", description="Gemini model name")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo", description="OpenAI model name")
    openai_org_id: Optional[str] = Field(default=None, description="OpenAI organization ID")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(default="claude-3-opus-20240229", description="Anthropic model name")

    # Vector Database Configuration
    vector_db: str = Field(default="chromadb", description="Vector DB (chromadb, pinecone)")
    chroma_persist_dir: str = Field(default="./data/chroma_db", description="ChromaDB persist directory")
    chroma_collection_name: str = Field(default="author_library", description="ChromaDB collection name")
    pinecone_api_key: Optional[str] = Field(default=None, description="Pinecone API key")
    pinecone_environment: str = Field(default="us-west1-gcp", description="Pinecone environment")
    pinecone_index_name: str = Field(default="virtual-debate-panel", description="Pinecone index name")

    # Embedding Configuration
    embedding_model: str = Field(default="models/text-embedding-004", description="Embedding model name")
    embedding_dimension: int = Field(default=768, description="Embedding vector dimension")

    # Semantic Router Configuration
    # Threshold adjusted to 0.60 based on empirical similarity score distribution
    # Test data showed Marx: 0.63-0.70, Whitman: 0.56-0.64, Baudelaire: 0.48-0.49
    # 0.60 captures most relevant queries while maintaining semantic filtering
    relevance_threshold: float = Field(default=0.60, ge=0.0, le=1.0, description="Author selection threshold")
    min_authors: int = Field(default=2, ge=1, le=10, description="Minimum number of authors")
    max_authors: int = Field(default=5, ge=1, le=10, description="Maximum number of authors")
    fallback_to_top_authors: bool = Field(default=True, description="Fallback to top authors if threshold not met")
    fallback_author_count: int = Field(default=3, ge=1, le=10, description="Number of authors for fallback")

    # RAG Pipeline Configuration
    top_k_chunks: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    chunk_size: int = Field(default=500, ge=100, le=2000, description="Text chunk size in tokens")
    chunk_overlap: int = Field(default=50, ge=0, le=500, description="Overlap between chunks")
    max_response_tokens: int = Field(default=300, ge=50, le=1000, description="Max tokens in response")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")

    # API Server Configuration
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API server port")
    api_workers: int = Field(default=4, ge=1, le=32, description="Number of API workers")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated CORS origins"
    )
    rate_limit_per_minute: int = Field(default=30, ge=1, le=1000, description="Rate limit per minute")
    enable_auth: bool = Field(default=False, description="Enable API authentication")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    log_format: str = Field(default="json", description="Log format (json, text)")
    log_file: str = Field(default="./logs/app.log", description="Log file path")
    debug: bool = Field(default=False, description="Enable debug mode")

    # Data Paths
    data_raw_dir: str = Field(default="./data/raw", description="Raw data directory")
    data_processed_dir: str = Field(default="./data/processed", description="Processed data directory")
    data_embeddings_dir: str = Field(default="./data/embeddings", description="Embeddings directory")

    # Cache Configuration
    enable_cache: bool = Field(default=True, description="Enable caching")
    cache_ttl_seconds: int = Field(default=3600, ge=0, le=86400, description="Cache TTL in seconds")

    # Performance Tuning
    llm_timeout: int = Field(default=30, ge=1, le=300, description="LLM API timeout in seconds")
    max_concurrent_authors: int = Field(default=5, ge=1, le=10, description="Max concurrent author queries")
    max_retries: int = Field(default=3, ge=0, le=10, description="Max API retry attempts")
    retry_delay_seconds: int = Field(default=2, ge=1, le=60, description="Delay between retries")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def _get_api_key(self, key_name: str, env_value: Optional[str]) -> Optional[str]:
        """
        Get API key from Secret Manager or environment variable.

        Args:
            key_name: Name of the secret in Secret Manager
            env_value: Value from environment variable/pydantic field

        Returns:
            API key value
        """
        # If use_secret_manager is enabled and we have a project ID
        if self.use_secret_manager and (self.gcp_project_id or os.getenv("GOOGLE_CLOUD_PROJECT")):
            try:
                from src.utils.secrets import get_secret
                project_id = self.gcp_project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
                secret_value = get_secret(key_name, project_id=project_id)
                if secret_value:
                    return secret_value
            except Exception as e:
                logger.debug(f"Secret Manager lookup failed for {key_name}, using env var: {e}")

        # Fall back to environment variable
        return env_value

    def get_llm_config(self) -> dict:
        """Get LLM configuration based on provider."""
        if self.llm_provider == "gemini":
            api_key = self._get_api_key("GEMINI_API_KEY", self.gemini_api_key)
            return {
                "provider": "gemini",
                "api_key": api_key,
                "model": self.gemini_model
            }
        elif self.llm_provider == "openai":
            api_key = self._get_api_key("OPENAI_API_KEY", self.openai_api_key)
            return {
                "provider": "openai",
                "api_key": api_key,
                "model": self.openai_model
            }
        elif self.llm_provider == "anthropic":
            api_key = self._get_api_key("ANTHROPIC_API_KEY", self.anthropic_api_key)
            return {
                "provider": "anthropic",
                "api_key": api_key,
                "model": self.anthropic_model
            }
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")

    def get_vector_db_config(self) -> dict:
        """Get vector database configuration."""
        if self.vector_db == "chromadb":
            return {
                "db_type": "chromadb",
                "persist_directory": self.chroma_persist_dir
            }
        elif self.vector_db == "pinecone":
            api_key = self._get_api_key("PINECONE_API_KEY", self.pinecone_api_key)
            return {
                "db_type": "pinecone",
                "api_key": api_key,
                "environment": self.pinecone_environment,
                "index_name": self.pinecone_index_name
            }
        else:
            raise ValueError(f"Unknown vector DB: {self.vector_db}")

    def get_embedding_config(self) -> dict:
        """Get embedding configuration based on LLM provider."""
        if self.llm_provider == "gemini":
            api_key = self._get_api_key("GEMINI_API_KEY", self.gemini_api_key)
            return {
                "provider": "gemini",
                "api_key": api_key,
                "model": self.embedding_model
            }
        elif self.llm_provider == "openai":
            api_key = self._get_api_key("OPENAI_API_KEY", self.openai_api_key)
            return {
                "provider": "openai",
                "api_key": api_key,
                "model": self.embedding_model
            }
        else:
            # Fall back to local embeddings
            return {
                "provider": "local",
                "model_name": "all-MiniLM-L6-v2"
            }


# Global settings instance
settings = Settings()
