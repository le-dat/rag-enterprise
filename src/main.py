import logging
from fastapi import FastAPI, Depends, Query
from pydantic import Field
from src.auth.middleware import get_current_user, UserContext
from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.reranker import CohereReranker
from src.generation.generator import OpenAIGenerator
from src.generation.grounding import GroundingChecker
from src.guardrails.retrieval_rail import RetrievalRail

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

search_engine = None
reranker = None
generator = None
grounding_checker = None

def get_search_engine() -> HybridSearchEngine:
    global search_engine
    if search_engine is None:
        search_engine = HybridSearchEngine()
    return search_engine

def get_reranker() -> CohereReranker:
    global reranker
    if reranker is None:
        reranker = CohereReranker()
    return reranker

def get_generator() -> OpenAIGenerator:
    global generator
    if generator is None:
        generator = OpenAIGenerator()
    return generator

def get_grounding_checker() -> GroundingChecker:
    global grounding_checker
    if grounding_checker is None:
        grounding_checker = GroundingChecker()
    return grounding_checker

retrieval_rail = None

def get_retrieval_rail() -> RetrievalRail:
    global retrieval_rail
    if retrieval_rail is None:
        retrieval_rail = RetrievalRail()
    return retrieval_rail

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

@app.post("/query")
def query_pipeline(
    q: str = Field(..., description="Query string to search and answer"),
    current_user: UserContext = Depends(get_current_user),
    engine: HybridSearchEngine = Depends(get_search_engine),
    cohere_rerank: CohereReranker = Depends(get_reranker),
    llm_gen: OpenAIGenerator = Depends(get_generator),
    grounding: GroundingChecker = Depends(get_grounding_checker),
    rail: RetrievalRail = Depends(get_retrieval_rail)
):
    """
    Secure endpoint running the full RAG pipeline:
    1. Retrieval (Hybrid Search with RBAC filter) -> Returns top 20
    2. Reranking (Cohere Reranker) -> Selects top 5
    3. Retrieval Rail (Llama Guard via Groq) -> Blocks unsafe chunks
    4. Generation (OpenAI GPT-4o-mini with citations)
    5. Grounding Check (Verify answer against retrieved sources)
    """
    logger.info(f"RAG query request by user {current_user.user_id} on route /query")
    
    # 1. Search (retrieve up to 20 candidates for reranker pool)
    raw_results = engine.search(
        query_text=q,
        user=current_user,
        limit=20
    )
    
    # 2. Rerank (keep top 5)
    reranked_results = cohere_rerank.rerank(
        query=q,
        documents=raw_results,
        top_n=5
    )
    
    # 3. Retrieval Rail (Prompt Injection Safety Filter)
    safe_results = rail.validate_chunks(reranked_results)
    
    # 4. Generate Answer
    answer = llm_gen.generate(
        query=q,
        documents=safe_results
    )
    
    # 5. Grounding Check
    grounding_res = grounding.check_grounding(
        documents=safe_results,
        answer=answer
    )
    
    return {
        "query": q,
        "answer": answer,
        "grounding": grounding_res,
        "results": safe_results,
        "user": {
            "id": current_user.user_id,
            "department": current_user.department,
            "role": current_user.role
        }
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
