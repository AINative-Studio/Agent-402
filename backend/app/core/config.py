"""
Application configuration using Pydantic Settings.
Loads from environment variables and .env file.
"""
import os
from typing import Dict
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ZeroDB Configuration
    # Use defaults for testing, override with environment variables in production
    zerodb_api_key: str = Field(
        default="test_zerodb_key_change_in_production",
        description="ZeroDB API key"
    )
    zerodb_project_id: str = Field(
        default="proj_test_change_in_production",
        description="ZeroDB project ID"
    )
    zerodb_base_url: str = Field(
        default="https://api.ainative.studio/v1/public",
        description="ZeroDB API base URL"
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")

    # Demo API Keys (hardcoded for deterministic demo per PRD §9)
    demo_api_key_1: str = Field(
        default="demo_key_user1_abc123",
        description="Demo API key for user 1"
    )
    demo_api_key_2: str = Field(
        default="demo_key_user2_xyz789",
        description="Demo API key for user 2"
    )

    # JWT Configuration (Epic 2 Story 4)
    jwt_secret_key: str = Field(
        default="your-secret-key-min-32-chars-change-in-production",
        description="Secret key for JWT token signing (min 32 chars)"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    jwt_expiration_seconds: int = Field(
        default=3600,
        description="JWT token expiration time in seconds (default: 1 hour)"
    )

    # Embedding Configuration (Issue #79 - DX Contract Section 5)
    # Default model must be BAAI/bge-small-en-v1.5 with 384 dimensions
    default_embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Default embedding model (384 dimensions)"
    )
    default_embedding_dimensions: int = Field(
        default=384,
        description="Default embedding dimensions for BAAI/bge-small-en-v1.5"
    )

    # Circle API Configuration (Issue #114)
    circle_api_key: str = Field(
        default="test_circle_api_key_change_in_production",
        description="Circle API key for USDC wallet operations"
    )
    circle_base_url: str = Field(
        default="https://api.circle.com",
        description="Circle API base URL (production)"
    )
    circle_entity_secret: str = Field(
        default="",
        description="Circle entity secret (32-byte hex string). Auto-generated if not provided."
    )
    circle_wallet_set_id: str = Field(
        default="",
        description="Circle wallet set ID for agent wallets. If empty, a new one will be created."
    )

    @field_validator('circle_entity_secret', mode='before')
    @classmethod
    def generate_entity_secret_if_empty(cls, v: str) -> str:
        """Generate a random entity secret if not provided."""
        if not v or v == "":
            return os.urandom(32).hex()
        return v

    # Gemini AI Configuration (Issue #115)
    gemini_api_key: str = Field(
        default="test_gemini_api_key_change_in_production",
        description="Google Gemini API key"
    )
    gemini_pro_model: str = Field(
        default="gemini-pro",
        description="Gemini Pro model for deep analysis"
    )
    gemini_flash_model: str = Field(
        default="gemini-1.5-flash",
        description="Gemini Flash model for fast execution"
    )
    llm_provider: str = Field(
        default="gemini",
        description="LLM provider to use (gemini, openai, anthropic)"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra env vars without validation errors

    @property
    def valid_api_keys(self) -> Dict[str, str]:
        """
        Return mapping of API key to user ID.
        In production, this would query a database.
        For MVP demo, we use deterministic hardcoded keys per PRD §9.
        """
        return {
            self.demo_api_key_1: "user_1",
            self.demo_api_key_2: "user_2",
        }

    def get_user_id_from_api_key(self, api_key: str) -> str | None:
        """Get user ID from API key, or None if invalid."""
        return self.valid_api_keys.get(api_key)


# Embedding Model Constants (Issue #79)
# Centralized configuration for supported models and dimensions
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDING_DIMENSIONS = 384

# Supported models with their dimensions
SUPPORTED_MODELS = {
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-large-en-v1.5": 1024,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-MiniLM-L12-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
    "sentence-transformers/all-distilroberta-v1": 768,
    "sentence-transformers/msmarco-distilbert-base-v4": 768,
    "text-embedding-ada-002": 1536,
}

# Global settings instance
settings = Settings()
