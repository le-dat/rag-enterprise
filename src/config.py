from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Enable automatic loading from .env file at project root
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[1] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ── LLM APIs ──────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    COHERE_API_KEY: str = ""
    COHERE_MODEL: str = "rerank-v3.5"
    LLM_MODEL: str = "gpt-4o-mini"

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

    # ── Demo / Simulation Mode ────────────────────────────────
    DEMO_MODE: bool = False

# Singleton settings instance
settings = Settings()
