import logging
from typing import Any, List, Optional
from openai import OpenAI, APIStatusError, APIConnectionError, APITimeoutError
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from src.config import settings

logger = logging.getLogger(__name__)


from enum import Enum

class LLMProviderName(str, Enum):
    OPENAI = "openai"
    MINIMAX = "minimax"


# ── 1. LLM Provider Configuration Object ─────────────────────────────────────

class LLMProvider:
    """
    Represents configuration data for an LLM provider.
    """
    def __init__(self, name: LLMProviderName, api_key: str, model: str, base_url: Optional[str] = None):
        self.name = name
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


def get_configured_providers() -> List[LLMProvider]:
    """
    Retrieves all currently configured LLM providers in priority order.
    Determined by the LLM_FALLBACK_ORDER setting.
    """
    fallback_order = [p.strip().lower() for p in settings.LLM_FALLBACK_ORDER.split(",") if p.strip()]
    providers = []

    for name in fallback_order:
        try:
            provider_enum = LLMProviderName(name)
        except ValueError:
            logger.warning(f"Unknown LLM provider name in fallback order: {name}")
            continue

        if provider_enum == LLMProviderName.OPENAI and settings.OPENAI_API_KEY:
            providers.append(LLMProvider(
                name=provider_enum,
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL
            ))
        elif provider_enum == LLMProviderName.MINIMAX and settings.MINIMAX_API_KEY:
            providers.append(LLMProvider(
                name=provider_enum,
                api_key=settings.MINIMAX_API_KEY,
                model=settings.MINIMAX_MODEL,
                base_url=settings.MINIMAX_API_BASE
            ))

    return providers


# ── 2. Transparent Fallback Wrapper for OpenAI Client SDK ──────────────────────

class FallbackCompletions:
    def __init__(self, clients: List[OpenAI], models: List[str]):
        self.clients = clients
        self.models = models

    def create(self, *args, **kwargs):
        if not self.clients:
            raise ValueError("No LLM clients are configured. Please verify your API keys.")

        last_error = None
        for i, client in enumerate(self.clients):
            provider_name = "Primary" if i == 0 else f"Backup {i}"
            try:
                call_kwargs = kwargs.copy()
                if i < len(self.models):
                    call_kwargs["model"] = self.models[i]
                return client.chat.completions.create(*args, **call_kwargs)
            except APIStatusError as e:
                # Fail fast on client errors (400, 401, 403, 404, 422) but fallback on rate limits/server errors
                if e.status_code not in (429, 500, 502, 503, 504):
                    logger.error(f"Client error from {provider_name} LLM client (status {e.status_code}): {e}. Failing fast.")
                    raise e
                logger.warning(f"{provider_name} LLM client failed with status {e.status_code}: {e}. Trying next fallback...")
                last_error = e
            except (APIConnectionError, APITimeoutError) as e:
                logger.warning(f"{provider_name} LLM client connection/timeout failed: {e}. Trying next fallback...")
                last_error = e
            except Exception as e:
                logger.error(f"Unexpected error in {provider_name} execution: {e}. Failing fast.")
                raise e

        if last_error:
            raise last_error
        raise ValueError("Failed to generate completion from all configured LLM providers.")


class FallbackChat:
    def __init__(self, clients: List[OpenAI], models: List[str]):
        self.clients = clients
        self.models = models

    @property
    def completions(self):
        return FallbackCompletions(self.clients, self.models)


class FallbackOpenAIClient:
    """
    A drop-in replacement wrapper for the OpenAI client that intercepts completions
    calls and redirects them sequentially through a list of fallback clients in case of failure.
    """
    def __init__(self, clients: List[OpenAI], models: List[str]):
        self.clients = clients
        self.models = models

    @property
    def chat(self):
        return FallbackChat(self.clients, self.models)

    @property
    def model(self) -> str:
        return self.models[0] if self.models else ""


# ── 3. Centralized Factory Functions ──────────────────────────────────────────

def create_chat_model(provider: LLMProvider) -> ChatOpenAI:
    """
    Creates a ChatOpenAI model instance for the given provider configuration.
    """
    kwargs = {
        "model": provider.model,
        "api_key": provider.api_key,
        "temperature": 0.0,
        "streaming": True
    }
    if provider.base_url:
        kwargs["base_url"] = provider.base_url

    return ChatOpenAI(**kwargs)


def get_chat_model() -> BaseChatModel:
    """
    Returns a LangChain chat model with automatic fallback handling across all configured providers.
    """
    providers = get_configured_providers()
    if not providers:
        raise ValueError("No LLM providers are configured. Please verify your API keys.")

    models = [create_chat_model(p) for p in providers]

    if len(models) > 1:
        primary_model = models[0]
        backup_models = models[1:]
        logger.info(
            f"LLM initialized with primary ({providers[0].name}: {providers[0].model}) "
            f"and fallbacks ({', '.join(f'{p.name}: {p.model}' for p in providers[1:])})"
        )
        return primary_model.with_fallbacks(backup_models)
    else:
        logger.info(f"LLM initialized with primary ({providers[0].name}: {providers[0].model}) only")
        return models[0]


def get_openai_client() -> Optional[FallbackOpenAIClient]:
    """
    Returns a transparent client wrapper that falls back sequentially across configured clients.
    """
    providers = get_configured_providers()
    if not providers:
        return None

    clients = []
    models = []
    for p in providers:
        kwargs = {"api_key": p.api_key}
        if p.base_url:
            kwargs["base_url"] = p.base_url
        clients.append(OpenAI(**kwargs))
        models.append(p.model)

    return FallbackOpenAIClient(clients, models)
