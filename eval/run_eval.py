"""
eval/run_eval.py

Day 7: Quantitative Evaluation — Baseline (Dense-Only) vs Full Pipeline (Hybrid + Rerank).

Metrics:
    - context_precision  : % retrieved chunks that are truly relevant
    - context_recall     : % of required info covered by retrieved chunks
    - answer_relevancy   : Does the generated answer actually address the question?

Usage:
    python eval/run_eval.py --testset eval/testset.json --output eval/results.json
"""

import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from fastembed import TextEmbedding

from src.config import settings
from src.auth.jwt_handler import UserContext, generate_token
from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.reranker import CohereReranker
from src.retrieval.rbac_filter import build_qdrant_rbac_filter
from src.generation.generator import OpenAIGenerator

load_dotenv()

logging.basicConfig(
    level=logging.WARNING,  # Suppress verbose info logs during eval
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("eval_runner")


# ── Dept → JWT mapping ────────────────────────────────────────────────────────

DEPT_TOKEN_MAP: dict[str, str] = {}
_DENSE_MODEL: TextEmbedding | None = None  # Cached to avoid reloading per call


def get_or_create_token(department: str) -> str:
    """Return a cached JWT for the given department (manager role)."""
    if department not in DEPT_TOKEN_MAP:
        DEPT_TOKEN_MAP[department] = generate_token(
            user_id=f"eval_user_{department.lower()}",
            role="manager",
            department=department
        )
    return DEPT_TOKEN_MAP[department]


# ── Dense-only search (Baseline) ──────────────────────────────────────────────

def dense_only_search(query_text: str, user: UserContext, limit: int = 5) -> list[dict]:
    """
    Baseline: dense vector search only — no sparse, no RRF fusion.
    Mirrors HybridSearchEngine but uses client.search() with dense vector only.
    """
    global _DENSE_MODEL
    if _DENSE_MODEL is None:
        _DENSE_MODEL = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    dense_vector = list(_DENSE_MODEL.embed([query_text]))[0].tolist()


    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    rbac_filter = build_qdrant_rbac_filter(user)

    response = client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=dense_vector,
        using="dense",
        query_filter=rbac_filter,
        limit=limit,
        with_payload=True
    )

    return [
        {
            "chunk_id": p.payload.get("chunk_id"),
            "text": p.payload.get("text"),
            "source": p.payload.get("source"),
            "department": p.payload.get("department"),
            "role": p.payload.get("role"),
            "page": p.payload.get("page"),
            "score": p.score
        }
        for p in response.points
    ]


# ── Scoring helpers ───────────────────────────────────────────────────────────

def score_context_precision(retrieved_chunks: list[dict], source_chunk_ids: list[str]) -> float:
    """
    context_precision = (# retrieved chunks that are relevant) / (# retrieved chunks)
    Relevant = chunk_id is in source_chunk_ids (ground truth sources for this question).

    Note: For questions with multiple valid chunks, this is a soft upper bound.
    We use exact chunk_id matching as proxy for relevance.
    """
    if not retrieved_chunks:
        return 0.0

    relevant_count = sum(
        1 for c in retrieved_chunks
        if c.get("chunk_id") in source_chunk_ids
    )
    return relevant_count / len(retrieved_chunks)


def score_context_recall(retrieved_chunks: list[dict], source_chunk_ids: list[str]) -> float:
    """
    context_recall = (# ground truth chunks present in retrieved set) / (# ground truth chunks)
    """
    if not source_chunk_ids:
        return 1.0  # Nothing required = perfect recall

    retrieved_ids = {c.get("chunk_id") for c in retrieved_chunks}
    found = sum(1 for sid in source_chunk_ids if sid in retrieved_ids)
    return found / len(source_chunk_ids)


def score_answer_relevancy(answer: str, question: str) -> float:
    """
    Lightweight answer relevancy:
    - 0.0 if answer is an "I cannot answer" refusal
    - 1.0 if answer contains keywords from the question
    - 0.5 if answer has some content but no keyword overlap
    """
    refusal_phrases = [
        "cannot answer", "insufficient", "lack of permission",
        "no relevant context", "access denied"
    ]
    lower_answer = answer.lower()
    for phrase in refusal_phrases:
        if phrase in lower_answer:
            return 0.0

    question_keywords = {
        w.lower() for w in question.split()
        if len(w) > 4  # Skip short stopwords
    }
    answer_words = set(lower_answer.split())
    overlap = question_keywords & answer_words

    if overlap:
        return min(1.0, len(overlap) / max(len(question_keywords), 1))
    return 0.5


# ── Single test item evaluation ───────────────────────────────────────────────

def evaluate_item(item: dict, mode: str, search_engine=None, reranker=None, generator=None) -> dict:
    """
    Run one testset item through the pipeline in the given mode.

    Args:
        mode: "baseline" (dense-only, no rerank) or "full" (hybrid + rerank)
    """
    question = item["question"]
    ground_truth = item["ground_truth"]
    department = item["department"]
    source_chunk_ids = item.get("source_chunk_ids", [])

    user = UserContext(
        user_id=f"eval_{department.lower()}",
        role="manager",
        department=department
    )

    # Step 1: Retrieve
    if mode == "baseline":
        retrieved = dense_only_search(query_text=question, user=user, limit=5)
    else:
        retrieved = search_engine.search(query_text=question, user=user, limit=20)
        retrieved = reranker.rerank(query=question, documents=retrieved, top_n=5)

    # Step 2: Generate
    answer = generator.generate(query=question, documents=retrieved)

    # Step 3: Score
    precision = score_context_precision(retrieved, source_chunk_ids)
    recall = score_context_recall(retrieved, source_chunk_ids)
    relevancy = score_answer_relevancy(answer, question)

    return {
        "question": question,
        "department": department,
        "mode": mode,
        "context_precision": round(precision, 4),
        "context_recall": round(recall, 4),
        "answer_relevancy": round(relevancy, 4),
        "retrieved_chunk_ids": [c.get("chunk_id") for c in retrieved],
        "answer_preview": answer[:200]
    }


# ── Main eval runner ──────────────────────────────────────────────────────────

def run_eval(testset_path: str, output_path: str):
    testset = json.loads(Path(testset_path).read_text())
    total = len(testset)
    print(f"\n🧪 Eval Runner — {total} questions | Modes: baseline vs full")
    print("=" * 70)

    # Initialize shared components for full pipeline (reused across questions)
    print("🔧 Initializing full pipeline components (HybridSearch, Reranker, Generator)...")
    search_engine = HybridSearchEngine()
    reranker = CohereReranker()
    generator = OpenAIGenerator()
    print("✅ Components ready.\n")

    baseline_results = []
    full_results = []

    for i, item in enumerate(testset, 1):
        q_short = item["question"][:55] + ("..." if len(item["question"]) > 55 else "")
        print(f"[{i:02d}/{total}] {q_short}")

        # Baseline
        try:
            b = evaluate_item(item, "baseline", generator=generator)
            baseline_results.append(b)
            print(f"       baseline → precision={b['context_precision']:.2f}  recall={b['context_recall']:.2f}  relevancy={b['answer_relevancy']:.2f}")
        except Exception as e:
            logger.error(f"Baseline eval failed for question {i}: {e}")
            baseline_results.append({"question": item["question"], "error": str(e)})

        # Full pipeline
        try:
            f = evaluate_item(item, "full", search_engine=search_engine, reranker=reranker, generator=generator)
            full_results.append(f)
            print(f"       full     → precision={f['context_precision']:.2f}  recall={f['context_recall']:.2f}  relevancy={f['answer_relevancy']:.2f}")
        except Exception as e:
            logger.error(f"Full eval failed for question {i}: {e}")
            full_results.append({"question": item["question"], "error": str(e)})

        # Respect Cohere Trial rate limit: 10 req/min → wait 7s between items
        if i < total:
            time.sleep(7)

    # Aggregate
    def avg(results: list[dict], key: str) -> float:
        values = [r[key] for r in results if key in r]
        return round(sum(values) / len(values), 4) if values else 0.0

    summary = {
        "eval_date": datetime.now(timezone.utc).isoformat(),
        "testset": testset_path,
        "total_questions": total,
        "baseline": {
            "mode": "dense_only_no_rerank",
            "avg_context_precision": avg(baseline_results, "context_precision"),
            "avg_context_recall": avg(baseline_results, "context_recall"),
            "avg_answer_relevancy": avg(baseline_results, "answer_relevancy"),
        },
        "full_pipeline": {
            "mode": "hybrid_search_plus_cohere_rerank",
            "avg_context_precision": avg(full_results, "context_precision"),
            "avg_context_recall": avg(full_results, "context_recall"),
            "avg_answer_relevancy": avg(full_results, "answer_relevancy"),
        },
        "delta": {},
        "details": {
            "baseline": baseline_results,
            "full": full_results
        }
    }

    # Compute delta
    for metric in ["avg_context_precision", "avg_context_recall", "avg_answer_relevancy"]:
        b_val = summary["baseline"][metric]
        f_val = summary["full_pipeline"][metric]
        delta = round(f_val - b_val, 4)
        pct = round((delta / b_val * 100), 1) if b_val > 0 else 0.0
        summary["delta"][metric] = {"absolute": delta, "percent": pct}

    # Write output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    # Print summary table
    print("\n" + "=" * 70)
    print("📊 EVAL RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Metric':<30} {'Baseline':>10} {'Full':>10} {'Delta':>10} {'%':>8}")
    print("-" * 70)
    for metric in ["avg_context_precision", "avg_context_recall", "avg_answer_relevancy"]:
        label = metric.replace("avg_", "").replace("_", " ").title()
        b_val = summary["baseline"][metric]
        f_val = summary["full_pipeline"][metric]
        d = summary["delta"][metric]
        sign = "+" if d["absolute"] >= 0 else ""
        print(f"{label:<30} {b_val:>10.4f} {f_val:>10.4f} {sign}{d['absolute']:>9.4f} {sign}{d['percent']:>6.1f}%")

    print("=" * 70)
    print(f"\n✅ Results written to: {output_path}")
    print("   → Update README.md with these numbers!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Quantitative Evaluation — Baseline vs Full Pipeline")
    parser.add_argument("--testset", type=str, default="eval/testset.json", help="Path to curated testset JSON")
    parser.add_argument("--output", type=str, default="eval/results.json", help="Path to write eval results JSON")
    args = parser.parse_args()

    run_eval(testset_path=args.testset, output_path=args.output)
