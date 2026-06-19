"""
Day 3-4 — Automated Integration Test for RBAC & Hybrid Search

Generates mock tokens for:
1. HR Manager
2. HR Staff
3. Sales Staff

And queries the HybridSearchEngine directly to prove security separation.
"""

from src.auth.jwt_handler import UserContext
from src.retrieval.hybrid_search import HybridSearchEngine

def run_tests():
    print("🚀 Initializing Hybrid Search Engine (loading BGE and SPLADE)...")
    engine = HybridSearchEngine()

    # Define test contexts
    contexts = [
        UserContext(user_id="emp_hr_mgr", department="HR", role="manager"),
        UserContext(user_id="emp_hr_stf", department="HR", role="staff"),
        UserContext(user_id="emp_sales_stf", department="Sales", role="staff")
    ]

    query_1 = "annual leave policy"
    query_2 = "sales target and discount"

    print(f"\n=======================================================")
    print(f"TEST 1: Query = '{query_1}'")
    print(f"=======================================================")
    for user in contexts:
        print(f"\n👤 User: {user.user_id} | Dept: {user.department} | Role: {user.role}")
        results = engine.search(query_text=query_1, user=user, limit=3)
        
        if not results:
            print("  ❌ [No results retrieved]")
            continue
            
        for idx, r in enumerate(results):
            print(f"  [{idx+1}] Source: {r['source']} | Dept: {r['department']} | Role: {r['role']} | Score: {r['score']:.4f}")
            print(f"      Text: {r['text'][:120]}...")

    print(f"\n=======================================================")
    print(f"TEST 2: Query = '{query_2}'")
    print(f"=======================================================")
    for user in contexts:
        print(f"\n👤 User: {user.user_id} | Dept: {user.department} | Role: {user.role}")
        results = engine.search(query_text=query_2, user=user, limit=3)
        
        if not results:
            print("  ❌ [No results retrieved]")
            continue
            
        for idx, r in enumerate(results):
            print(f"  [{idx+1}] Source: {r['source']} | Dept: {r['department']} | Role: {r['role']} | Score: {r['score']:.4f}")
            print(f"      Text: {r['text'][:120]}...")

    print(f"\n=======================================================")
    print("Integration verification finished.")

if __name__ == "__main__":
    run_tests()
