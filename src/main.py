import os
NUM_THREADS = os.getenv("EMBEDDING_THREADS", "1")

os.environ["OMP_NUM_THREADS"] = NUM_THREADS
os.environ["MKL_NUM_THREADS"] = NUM_THREADS
os.environ["OPENBLAS_NUM_THREADS"] = NUM_THREADS
os.environ["VECLIB_MAXIMUM_THREADS"] = NUM_THREADS
os.environ["NUMEXPR_NUM_THREADS"] = NUM_THREADS

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
from src.api.v1 import search, query, agent, auth


configure_logging()
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


app = FastAPI(
    title="Enterprise RAG — API Server",
    description=(
        "Secure knowledge retrieval system with vector-level RBAC, "
        "hybrid search, and multi-layer guardrails."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(search.router, prefix="/api/v1/search", tags=["Retrieval"])
app.include_router(query.router, prefix="/api/v1/query", tags=["RAG Pipeline"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agentic Pipeline"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])


@app.get("/health", tags=["System"])
def health():
    return {"status": "healthy"}
