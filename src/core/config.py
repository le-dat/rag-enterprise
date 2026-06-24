from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Enable automatic loading from .env file at project root
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )
    PROJECT_NAME: str = "Enterprise RAG"
    API_V1_STR: str = "/api/v1"

    # ── LLM APIs ──────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    COHERE_API_KEY: str = ""
    COHERE_MODEL: str = "rerank-v3.5"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ── MiniMax Config ────────────────────────────────────────
    MINIMAX_API_KEY: str = ""
    MINIMAX_API_BASE: str = "https://api.minimax.io/v1"
    MINIMAX_MODEL: str = "MiniMax-M3"

    # ── Fallback Configuration ────────────────────────────────
    LLM_FALLBACK_ORDER: str = "openai,minimax"

    # ── Parsing ───────────────────────────────────────────────
    LLAMAPARSE_API_KEY: str = ""
    USE_LLAMAPARSE: bool = True

    # ── Vector DB ─────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "rag_enterprise"

    # ── Retrieval Rail ────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "meta-llama/llama-prompt-guard-2-86m"

    # ── Auth (JWT) ────────────────────────────────────────────
    JWT_SECRET: str = "super-secret-dev-key-change-prod"
    JWT_ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # ── Threading/Resource limits ─────────────────────────────────────────────
    EMBEDDING_THREADS: int = 1

    # ── Concurrency & Rate Limiting ───────────────────────────────────────────
    # Max concurrent RAG pipeline executions (across all users on one worker).
    PIPELINE_MAX_CONCURRENT: int = 50
    # Max chat requests per user per minute (slowapi rate limiter).
    RATE_LIMIT_PER_MINUTE: int = 10
    # Hard timeout for a single tool execution in seconds.
    TOOL_TIMEOUT_SECONDS: int = 30


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore


settings = get_settings()
