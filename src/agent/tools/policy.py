"""
Policy lookup tool — searches the company knowledge base via the RAG pipeline.
Accessible by any authenticated user (no department restriction).
"""
import asyncio
import logging

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.agent.middleware import rbac_guard
from src.agent.schemas import tool_ok, tool_fail
from src.core.concurrency import pipeline_semaphore
from src.core.config import settings
from src.core.orchestrator import run_rag_pipeline

logger = logging.getLogger(__name__)


class PolicyLookupInput(BaseModel):
    query: str = Field(..., description="The query to search in the policy database.")


@tool("policy_lookup_tool", args_schema=PolicyLookupInput)
@rbac_guard(allowed_departments=["*"])
async def policy_lookup_tool(query: str, config: RunnableConfig) -> str:
    """
    Search the company policies database (HR guidelines, leave policies,
    sales commissions, targets, etc.).
    Always use this tool when the user asks questions about corporate
    policies, regulations, or rules.
    """
    logger.info("policy_lookup_tool called with query=%r", query)
    configurable = config.get("configurable", {})

    engine = configurable.get("search_engine")
    reranker = configurable.get("reranker")
    generator = configurable.get("generator")
    grounding_checker = configurable.get("grounding_checker")
    retrieval_rail = configurable.get("retrieval_rail")

    # Lazy fallbacks — used when services are not pre-injected via config
    if not engine:
        from src.retrieval.hybrid_search import HybridSearchEngine
        engine = HybridSearchEngine()
    if not reranker:
        from src.retrieval.reranker import CohereReranker
        reranker = CohereReranker()
    if not generator:
        from src.generation.generator import OpenAIGenerator
        generator = OpenAIGenerator()
    if not grounding_checker:
        from src.generation.grounding import GroundingChecker
        grounding_checker = GroundingChecker()
    if not retrieval_rail:
        from src.guardrails.retrieval_rail import RetrievalRail
        retrieval_rail = RetrievalRail()

    # Semaphore: suspend (not block) the event loop if the pipeline is saturated.
    # This keeps the server responsive while preventing OOM and API rate bursts.
    async with pipeline_semaphore:
        try:
            res = await asyncio.wait_for(
                asyncio.to_thread(
                    run_rag_pipeline,
                    query=query,
                    user=configurable["user"],
                    engine=engine,
                    reranker=reranker,
                    generator=generator,
                    grounding_checker=grounding_checker,
                    retrieval_rail=retrieval_rail,
                ),
                timeout=settings.TOOL_TIMEOUT_SECONDS,
            )
            grounding_val = res["grounding"].get("grounded")
            return tool_ok({
                "answer": res["answer"],
                "grounding": grounding_val,
                "grounding_reason": res["grounding"].get("reason", ""),
            })
        except asyncio.TimeoutError:
            logger.error(
                "policy_lookup_tool timed out after %ds for query=%r",
                settings.TOOL_TIMEOUT_SECONDS, query,
            )
            return tool_fail(
                code="TIMEOUT",
                detail=f"Pipeline exceeded the {settings.TOOL_TIMEOUT_SECONDS}s limit. Try a simpler query.",
            )
        except Exception as exc:
            logger.error("Error in policy_lookup_tool: %s", exc)
            return tool_fail(
                code="PIPELINE_ERROR",
                detail=f"Error retrieving policy details: {exc}",
            )
