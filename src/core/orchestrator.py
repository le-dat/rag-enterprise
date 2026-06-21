"""
Shared RAG query orchestrator.

Contains the single source of truth for the full query pipeline steps.
Both the FastAPI route handler and the CLI use this function — no logic duplication.
"""
import logging
from typing import Any

from src.auth.jwt_handler import UserContext
from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.reranker import CohereReranker
from src.generation.generator import OpenAIGenerator
from src.generation.grounding import GroundingChecker
from src.guardrails.retrieval_rail import RetrievalRail

logger = logging.getLogger(__name__)


def run_rag_pipeline(
    query: str,
    user: UserContext,
    engine: HybridSearchEngine,
    reranker: CohereReranker,
    generator: OpenAIGenerator,
    grounding_checker: GroundingChecker,
    retrieval_rail: RetrievalRail,
    retrieval_limit: int = 20,
    rerank_top_n: int = 5,
    skip_retrieval_rail: bool = False,
) -> dict[str, Any]:
    """
    Execute the full RAG pipeline (steps 1-5). Input Rail must be called
    by the caller *before* invoking this function.

    Returns:
        dict with keys: answer, grounding, results
    """
    logger.info(f"Running RAG pipeline for user={user.user_id}, query={query[:80]!r}")

    # Step 1 — Hybrid Search with RBAC
    raw_results = engine.search(query_text=query, user=user, limit=retrieval_limit)
    logger.info(f"Retrieved {len(raw_results)} candidates")

    # Step 2 — Rerank (Top 20 → Top N)
    reranked = reranker.rerank(query=query, documents=raw_results, top_n=rerank_top_n)

    # Step 3 — Retrieval Rail (query-time chunk safety check)
    if skip_retrieval_rail:
        safe_results = reranked
        logger.warning("Retrieval Rail skipped (skip_retrieval_rail=True)")
    else:
        safe_results = retrieval_rail.validate_chunks(reranked)
        logger.info(f"Retrieval Rail: {len(safe_results)}/{len(reranked)} chunks passed")

    # Step 4 — Generate answer
    answer = generator.generate(query=query, documents=safe_results)

    # Step 5 — Grounding check
    grounding = grounding_checker.check_grounding(documents=safe_results, answer=answer)

    return {
        "answer": answer,
        "grounding": grounding,
        "results": safe_results,
    }
