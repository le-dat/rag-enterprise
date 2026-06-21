import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.logging import configure_logging
from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.reranker import CohereReranker
from src.generation.generator import OpenAIGenerator
from src.generation.grounding import GroundingChecker
from src.guardrails.retrieval_rail import RetrievalRail
from src.guardrails.input_rail import InputRail
from src.api.routes import search, query, agent, auth
from src.config import settings


configure_logging()
logger = logging.getLogger(__name__)




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise heavy services once at startup; clean up on shutdown."""
    logger.info("🚀 Starting up Enterprise RAG services...")

    if settings.DEMO_MODE:
        logger.info("⚡ DEMO MODE is active. Instantiating mock RAG services...")
        from src.core.demo import (
            MockSearchEngine,
            MockReranker,
            MockGenerator,
            MockGroundingChecker,
            MockRetrievalRail,
            MockInputRail,
        )
        app.state.search_engine     = MockSearchEngine()
        app.state.reranker          = MockReranker()
        app.state.generator         = MockGenerator()
        app.state.grounding_checker = MockGroundingChecker()
        app.state.retrieval_rail    = MockRetrievalRail()
        app.state.input_rail        = MockInputRail()
    else:
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


app = FastAPI(
    title="Enterprise RAG — API Server",
    description=(
        "Secure knowledge retrieval system with vector-level RBAC, "
        "hybrid search, and multi-layer guardrails."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(search.router, tags=["Retrieval"])
app.include_router(query.router, tags=["RAG Pipeline"])
app.include_router(agent.router, prefix="/agent", tags=["Agentic Pipeline"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])


@app.get("/health", tags=["System"])
def health():
    return {"status": "healthy"}
