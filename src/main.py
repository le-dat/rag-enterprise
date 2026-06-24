import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.core.logging import configure_logging
from src.core.config import get_settings
from src.core.rate_limit import limiter
from src.lifespan import lifespan
from src.api.v1 import search, query, agent, auth


configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Secure knowledge retrieval system with vector-level RBAC, "
        "hybrid search, and multi-layer guardrails."
    ),
    version="1.0.0",
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api/v1/search", tags=["Retrieval"])
app.include_router(query.router, prefix="/api/v1/query", tags=["RAG Pipeline"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agentic Pipeline"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])


@app.get("/health", tags=["public"])
def health():
    return {"status": "healthy"}
