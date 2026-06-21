"""GET /search — secure hybrid search endpoint."""
import logging

from fastapi import APIRouter, Query, HTTPException

from src.api.dependencies import (
    CurrentUser,
    SearchEngineDep,
    InputRailDep,
)
from src.guardrails.input_rail import QueryBlockedError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search", summary="Hybrid search with RBAC filtering")
def search(
    q: str = Query(..., description="Query string to search"),
    limit: int = Query(5, ge=1, le=50, description="Max results to return"),
    current_user: CurrentUser = None,
    engine: SearchEngineDep = None,
    i_rail: InputRailDep = None,
):
    """
    Secure search endpoint protected by JWT Bearer token.

    Pipeline:
    - Input Rail: blocks jailbreak / injection queries
    - RBAC filter: restricts results to user's department + role
    - Hybrid Search: Dense + SPLADE + RRF Fusion on Qdrant
    """
    logger.info(f"/search by {current_user.user_id!r} | q={q[:80]!r}")

    try:
        i_rail.validate_query(q)
    except QueryBlockedError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Query blocked by security policy: {exc.reason}",
        )

    results = engine.search(query_text=q, user=current_user, limit=limit)

    return {
        "query": q,
        "user": {
            "id": current_user.user_id,
            "department": current_user.department,
            "role": current_user.role,
        },
        "results": results,
    }
