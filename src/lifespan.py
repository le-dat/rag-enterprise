import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.reranker import CohereReranker
from src.generation.generator import OpenAIGenerator
from src.generation.grounding import GroundingChecker
from src.guardrails.retrieval_rail import RetrievalRail
from src.guardrails.input_rail import InputRail


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise heavy services once at startup; clean up on shutdown."""
    logger.info("🚀 Starting up Enterprise RAG services...")

    app.state.search_engine     = HybridSearchEngine()
    app.state.reranker          = CohereReranker()
    app.state.generator         = OpenAIGenerator()
    app.state.grounding_checker = GroundingChecker()
    app.state.retrieval_rail    = RetrievalRail()
    app.state.input_rail        = InputRail()

    from src.agent.graph import agent_graph
    app.state.agent_graph      = agent_graph

    logger.info("✅ All services initialised.")
    yield
    logger.info("🛑 Shutting down Enterprise RAG services.")
