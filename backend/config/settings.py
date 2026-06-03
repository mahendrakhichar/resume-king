"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Central configuration for the ResumeForge AI backend."""

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_name: str = "ResumeForge AI"
    app_version: str = "0.1.0"

    # Server
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # Database
    database_url: str = "postgresql+asyncpg://localhost/resumeforge"

    # AI Providers (legacy direct keys — kept as additional fallbacks)
    google_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None

    # OpenRouter (primary unified provider)
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Task-based model tiers (used with OpenRouter)
    # Use :free suffix for models on OpenRouter free tier
    heavy_model: str = "google/gemma-4-31b"
    main_model: str = "groq/llama-3.3-70b-versatile"
    fast_model: str = "groq/llama-3.1-8b-instant"
    fallback_model: str = "minimax/minimax-m2.5:free"

    # Default LLM settings
    default_llm_provider: str = "openrouter"  # openrouter | gemini | groq | openai
    default_llm_model: str = "google/gemma-4-26b-a4b-it:free"
    default_temperature: float = 0.3

    # Timeouts (seconds)
    llm_call_timeout: int = 120       # Per-LLM-call timeout
    agent_execution_timeout: int = 300  # 5 minutes per agent node

    # Clerk Auth
    clerk_secret_key: Optional[str] = None
    clerk_publishable_key: Optional[str] = None
    clerk_jwks_url: Optional[str] = None

    # File Storage
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 10

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton instance
settings = Settings()
