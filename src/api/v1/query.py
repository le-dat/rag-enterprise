"""POST /query — full RAG pipeline endpoint."""
import logging

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from src.api.dependencies import (
    CurrentUser,
    SearchEngineDep,
    RerankerDep,
    GeneratorDep,
    GroundingDep,
    RetrievalRailDep,
    InputRailDep,
)
from src.core.orchestrator import run_rag_pipeline
from src.guardrails.input_rail import QueryBlockedError

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    q: str = Field(..., description="Natural-language question to answer")


@router.post("", summary="Full RAG pipeline (search → rerank → generate)")
def query_pipeline(
    body: QueryRequest = Body(...),
    current_user: CurrentUser = None,
    engine: SearchEngineDep = None,
    reranker: RerankerDep = None,
    generator: GeneratorDep = None,
    grounding: GroundingDep = None,
    retrieval_rail: RetrievalRailDep = None,
    i_rail: InputRailDep = None,
):
    """
    Secure full RAG pipeline endpoint:

    0. Input Rail — jailbreak / prompt-injection filter
    1. Hybrid Search — Dense + SPLADE + RRF Fusion (top 20, RBAC applied)
    2. Cohere Rerank v3.5 — top 20 → top 5
    3. Retrieval Rail — query-time chunk safety check
    4. OpenAI GPT-4o-mini — generate cited answer
    5. Grounding Checker — verify answer is supported by context
    """
    logger.info(f"/query by {current_user.user_id!r} | q={body.q[:80]!r}")

    # Step 0 — Input Rail (before any retrieval)
    try:
        i_rail.validate_query(body.q)
    except QueryBlockedError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Query blocked by security policy: {exc.reason}",
        )

    # Steps 1-5 — delegated to shared orchestrator
    pipeline_result = run_rag_pipeline(
        query=body.q,
        user=current_user,
        engine=engine,
        reranker=reranker,
        generator=generator,
        grounding_checker=grounding,
        retrieval_rail=retrieval_rail,
    )

    return {
        "query": body.q,
        **pipeline_result,
        "user": {
            "id": current_user.user_id,
            "department": current_user.department,
            "role": current_user.role,
        },
    }
