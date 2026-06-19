import logging
from fastapi import FastAPI, Depends, Query
from src.config import settings
from src.auth.middleware import get_current_user, UserContext
from src.retrieval.hybrid_search import HybridSearchEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api_server")

app = FastAPI(
    title="Enterprise RAG — API Server",
    description="Secure search engine featuring native hybrid retrieval and vector-level RBAC",
    version="1.0.0"
)

# Initialize engine lazily/globally
search_engine = None

def get_search_engine() -> HybridSearchEngine:
    global search_engine
    if search_engine is None:
        search_engine = HybridSearchEngine()
    return search_engine

@app.get("/search")
def search(
    q: str = Query(..., description="Query string to search"),
    limit: int = Query(5, ge=1, le=50, description="Max results to return"),
    current_user: UserContext = Depends(get_current_user),
    engine: HybridSearchEngine = Depends(get_search_engine)
):
    """
    Secure search endpoint protected by JWT Bearer token.
    Applies RBAC filtering before scoring points.
    """
    logger.info(f"API Request by {current_user.user_id} on route /search?q={q}")
    results = engine.search(
        query_text=q,
        user=current_user,
        limit=limit
    )
    return {
        "query": q,
        "user": {
            "id": current_user.user_id,
            "department": current_user.department,
            "role": current_user.role
        },
        "results": results
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
