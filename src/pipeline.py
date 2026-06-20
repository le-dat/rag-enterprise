import argparse
import sys
import logging
from src.auth.jwt_handler import verify_token
from src.retrieval.hybrid_search import HybridSearchEngine
from src.retrieval.reranker import CohereReranker
from src.generation.generator import OpenAIGenerator
from src.generation.grounding import GroundingChecker

# Setup logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("pipeline_cli")

def run_pipeline(query: str, token: str):
    print("\n" + "="*80)
    print(" STARTING ENTERPRISE RAG E2E PIPELINE ")
    print("="*80)

    # 1. Authenticate / Verify Token
    print("\n[Step 1] Authenticating using Bearer Token...")
    user = verify_token(token)
    if not user:
        print("❌ ERROR: Invalid or expired token. Authentication failed.")
        sys.exit(1)
    print(f"✅ Success: Authenticated as user '{user.user_id}' (Dept: {user.department}, Role: {user.role})")

    # 2. Retrieval with Hybrid Search
    print("\n[Step 2] Executing Hybrid Search (Qdrant with RBAC)...")
    search_engine = HybridSearchEngine()
    # We retrieve 20 chunks initially for reranking pool
    raw_results = search_engine.search(query_text=query, user=user, limit=20)
    print(f"✅ Found {len(raw_results)} documents matching criteria (RBAC applied).")
    for i, doc in enumerate(raw_results[:3]):
        print(f"   [{i+1}] chunk_id: {doc['chunk_id']} | Source: {doc['source']} (Page: {doc['page']}) | RRF Score: {doc['score']:.4f}")
    if len(raw_results) > 3:
        print(f"   ... and {len(raw_results) - 3} more.")

    # 3. Cohere Reranking
    print("\n[Step 3] Reranking using Cohere (top 5)...")
    reranker = CohereReranker()
    reranked_results = reranker.rerank(query=query, documents=raw_results, top_n=5)
    print(f"✅ Selected top {len(reranked_results)} documents after reranking:")
    for i, doc in enumerate(reranked_results):
        print(f"   [{i+1}] chunk_id: {doc['chunk_id']} | Source: {doc['source']} (Page: {doc['page']}) | Rerank Score: {doc['score']:.4f}")

    # 4. OpenAI Generation
    print("\n[Step 4] Generating cited response from OpenAI...")
    generator = OpenAIGenerator()
    answer = generator.generate(query=query, documents=reranked_results)
    print("\n--- LLM GENERATED ANSWER ---")
    print(answer)
    print("----------------------------")

    # 5. Grounding Check
    print("\n[Step 5] Performing Grounding Check on generated answer...")
    checker = GroundingChecker()
    grounding_res = checker.check_grounding(documents=reranked_results, answer=answer)
    print(f"✅ Grounding Check Status: {'GROUNDED' if grounding_res['grounded'] else 'NOT GROUNDED'}")
    print(f"   Reason: {grounding_res['reason']}")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run End-to-End Enterprise RAG Ingestion & Query Pipeline")
    parser.add_argument("--query", type=str, required=True, help="Query string to search and answer")
    parser.add_argument("--token", type=str, required=True, help="JWT auth token containing RBAC claims")
    args = parser.parse_args()

    run_pipeline(query=args.query, token=args.token)
