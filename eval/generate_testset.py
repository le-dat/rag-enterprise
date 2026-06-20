"""
eval/generate_testset.py

Utility to inspect sample documents and help generate/review testset items.
The actual curated testset is in eval/testset.json (20 questions).

Usage:
    # Inspect what documents exist in data/samples/
    python eval/generate_testset.py --docs data/samples/ --output eval/testset_raw.json

    # Preview testset stats
    python eval/generate_testset.py --stats
"""

import argparse
import json
from pathlib import Path


def load_documents(docs_dir: str) -> list[dict]:
    """Load text content from all supported files in docs_dir."""
    docs = []
    supported = {".txt", ".pdf", ".xlsx"}
    for path in Path(docs_dir).iterdir():
        if path.suffix.lower() not in supported:
            continue
        if path.suffix.lower() == ".txt":
            content = path.read_text(encoding="utf-8")
            docs.append({"source": path.name, "text": content})
        else:
            docs.append({"source": path.name, "text": f"[Binary: {path.name} — use ingestion pipeline to parse]"})
    return docs


def print_stats(testset_path: str = "eval/testset.json"):
    """Print summary stats for the curated testset."""
    path = Path(testset_path)
    if not path.exists():
        print(f"❌ Testset not found at {testset_path}")
        return

    testset = json.loads(path.read_text())
    total = len(testset)
    dept_counts: dict[str, int] = {}
    for item in testset:
        dept = item.get("department", "Unknown")
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    print(f"\n📊 Testset Stats: {testset_path}")
    print(f"   Total questions : {total}")
    for dept, count in sorted(dept_counts.items()):
        print(f"   {dept:12s}: {count} questions")
    print()


def generate_raw_testset(docs_dir: str, output: str):
    """
    Inspect docs and generate a raw testset scaffold.
    Note: For actual AI-powered testset generation, see ragas docs:
          https://docs.ragas.io/en/stable/getstarted/testset_generation.html
    """
    docs = load_documents(docs_dir)
    print(f"\n📂 Found {len(docs)} documents in '{docs_dir}':")
    for doc in docs:
        preview = doc["text"][:120].replace("\n", " ")
        print(f"   [{doc['source']}] {preview}...")

    scaffold = []
    for doc in docs:
        scaffold.append({
            "question": "TODO: Write question based on this document",
            "ground_truth": "TODO: Write expected answer",
            "department": "TODO: HR or Sales",
            "source": doc["source"],
            "source_chunk_ids": ["TODO"]
        })

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(scaffold, indent=2, ensure_ascii=False))
    print(f"\n✅ Raw scaffold written to {output}")
    print("   → Edit the TODOs, then copy best items to eval/testset.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testset generation utilities for RAG eval")
    parser.add_argument("--docs", type=str, help="Directory of sample documents to inspect")
    parser.add_argument("--output", type=str, default="eval/testset_raw.json", help="Output path for raw scaffold")
    parser.add_argument("--stats", action="store_true", help="Print stats for eval/testset.json")
    args = parser.parse_args()

    if args.stats:
        print_stats()
    elif args.docs:
        generate_raw_testset(args.docs, args.output)
    else:
        parser.print_help()
