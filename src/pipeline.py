"""
CLI entry point for the Enterprise RAG query pipeline.

Usage:
    python -m src.pipeline --query "..." --token "..."

The heavy pipeline logic is shared with the FastAPI layer via src.core.orchestrator.
This file is responsible only for: argument parsing, auth, and CLI-friendly output.
"""
import argparse
import sys

from src.core.logging import configure_logging
from src.auth.jwt_handler import verify_token
from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.reranker import CohereReranker
from src.generation.generator import OpenAIGenerator
from src.generation.grounding import GroundingChecker
from src.guardrails.retrieval_rail import RetrievalRail
from src.guardrails.input_rail import InputRail, QueryBlockedError
from src.core.orchestrator import run_rag_pipeline

configure_logging()


def run_pipeline(query: str, token: str, skip_rail: bool = False) -> None:
    sep = "=" * 72
    print(f"\n{sep}\n ENTERPRISE RAG — CLI PIPELINE\n{sep}")

    from src.config import settings

    if settings.DEMO_MODE:
        from src.core.demo import (
            MockSearchEngine as HybridSearchEngine,
            MockReranker as CohereReranker,
            MockGenerator as OpenAIGenerator,
            MockGroundingChecker as GroundingChecker,
            MockRetrievalRail as RetrievalRail,
            MockInputRail as InputRail,
        )

    # Step 0 — Input Rail
    print("\n[0] Input Rail (jailbreak / injection filter)...")
    try:
        InputRail().validate_query(query)
        print("    ✅ Query passed — no injection patterns detected.")
    except QueryBlockedError as exc:
        print(f"    ❌ BLOCKED: {exc.reason}")
        sys.exit(1)

    # Step 1 — Auth
    print("\n[1] Authenticating bearer token...")
    user = verify_token(token)
    if not user:
        print("    ❌ Invalid or expired token.")
        sys.exit(1)
    print(f"    ✅ Authenticated: {user.user_id!r} ({user.department}/{user.role})")

    # Steps 2-5 — shared orchestrator
    print("\n[2-5] Running RAG pipeline (search → rerank → guard → generate → ground)...")
    result = run_rag_pipeline(
        query=query,
        user=user,
        engine=HybridSearchEngine(),
        reranker=CohereReranker(),
        generator=OpenAIGenerator(),
        grounding_checker=GroundingChecker(),
        retrieval_rail=RetrievalRail(),
        skip_retrieval_rail=skip_rail,
    )

    # Output
    results = result["results"]
    print(f"\n    Retrieved {len(results)} safe chunks after full pipeline.")
    for i, doc in enumerate(results):
        print(
            f"    [{i+1}] {doc.get('source')} p.{doc.get('page')} "
            f"| score={doc.get('score', 0):.4f}"
        )

    print("\n--- ANSWER ---")
    print(result["answer"])
    print("-" * 14)

    grounding = result["grounding"]
    status = "GROUNDED" if grounding.get("grounded") else "NOT GROUNDED"
    print(f"\n[Grounding] {status} — {grounding.get('reason', '')}")
    print(f"\n{sep}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enterprise RAG CLI — query pipeline"
    )
    parser.add_argument("--query",    required=True, help="Natural-language question")
    parser.add_argument("--token",    required=True, help="JWT bearer token with RBAC claims")
    parser.add_argument("--no-rail",  action="store_true",
                        help="Skip Retrieval Rail (demo/debug only)")
    args = parser.parse_args()

    run_pipeline(query=args.query, token=args.token, skip_rail=args.no_rail)
