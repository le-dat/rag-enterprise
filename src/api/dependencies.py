"""
FastAPI dependency providers.

All Depends() callables live here. Routes import from this module only —
never instantiate services directly inside route handlers.

Services are stored on app.state (set up in the lifespan) so they are
initialised once at startup and shared across requests.
"""
from typing import Annotated

from fastapi import Depends, Request

from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.reranker import CohereReranker
from src.generation.generator import OpenAIGenerator
from src.generation.grounding import GroundingChecker
from src.guardrails.retrieval_rail import RetrievalRail
from src.guardrails.input_rail import InputRail
from src.auth.middleware import get_current_user
from src.auth.jwt_handler import UserContext


# ── Re-export auth dependency so routes only import from this module ──────────
CurrentUser = Annotated[UserContext, Depends(get_current_user)]


# ── Service providers (read from app.state) ───────────────────────────────────

def get_search_engine(request: Request) -> HybridSearchEngine:
    return request.app.state.search_engine


def get_reranker(request: Request) -> CohereReranker:
    return request.app.state.reranker


def get_generator(request: Request) -> OpenAIGenerator:
    return request.app.state.generator


def get_grounding_checker(request: Request) -> GroundingChecker:
    return request.app.state.grounding_checker


def get_retrieval_rail(request: Request) -> RetrievalRail:
    return request.app.state.retrieval_rail


def get_input_rail(request: Request) -> InputRail:
    return request.app.state.input_rail


# ── Annotated shortcuts for cleaner route signatures ─────────────────────────

SearchEngineDep     = Annotated[HybridSearchEngine, Depends(get_search_engine)]
RerankerDep         = Annotated[CohereReranker,     Depends(get_reranker)]
GeneratorDep        = Annotated[OpenAIGenerator,    Depends(get_generator)]
GroundingDep        = Annotated[GroundingChecker,   Depends(get_grounding_checker)]
RetrievalRailDep    = Annotated[RetrievalRail,      Depends(get_retrieval_rail)]
InputRailDep        = Annotated[InputRail,          Depends(get_input_rail)]
