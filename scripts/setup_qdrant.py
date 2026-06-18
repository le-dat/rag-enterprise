"""
Day 0 — Qdrant Setup Script

Creates the `rag_enterprise` collection with dense (384-dim) + sparse (BM25)
vectors and loads all 20 fixture chunks from fixtures/mock_chunks.json.

Usage:
    python -m scripts.setup_qdrant
    python -m scripts.setup_qdrant --verify-only
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastembed import SparseTextEmbedding, TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

load_dotenv()

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "rag_enterprise")
DENSE_DIM = 384  # BAAI/bge-small-en-v1.5
DENSE_MODEL = "BAAI/bge-small-en-v1.5"
SPARSE_MODEL = "prithivida/Splade_PP_en_v1"


def _get_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    if not url:
        print("❌  QDRANT_URL not set in .env — aborting.")
        sys.exit(1)

    return QdrantClient(url=url, api_key=api_key)


def create_collection(client: QdrantClient) -> None:
    """Create collection with dense + sparse vector config."""
    existing = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME in existing:
        print(f"ℹ️   Collection '{COLLECTION_NAME}' already exists — skipping creation.")
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": rest.VectorParams(
                size=DENSE_DIM,
                distance=rest.Distance.COSINE,
            )
        },
        sparse_vectors_config={
            "sparse": rest.SparseVectorParams(
                index=rest.SparseIndexParams(on_disk=False)
            )
        },
    )
    print(f"✅  Collection '{COLLECTION_NAME}' created (dense={DENSE_DIM}-dim + sparse BM25).")


def create_payload_indexes(client: QdrantClient) -> None:
    """Create keyword indexes on RBAC fields so payload filters work."""
    for field in ("department", "role"):
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=rest.PayloadSchemaType.KEYWORD,
        )
    print("✅  Payload indexes created for 'department' and 'role'.")


def load_fixtures(client: QdrantClient, fixtures_path: Path) -> None:
    """Embed and upsert all fixture chunks into Qdrant."""
    with fixtures_path.open() as f:
        chunks: list[dict] = json.load(f)

    texts = [c["text"] for c in chunks]

    print(f"🔢  Embedding {len(texts)} chunks with {DENSE_MODEL} …")
    dense_model = TextEmbedding(model_name=DENSE_MODEL)
    dense_vectors = list(dense_model.embed(texts))

    print(f"🔢  Sparse-encoding {len(texts)} chunks with {SPARSE_MODEL} …")
    sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL)
    sparse_vectors = list(sparse_model.embed(texts))

    points = []
    for i, (chunk, dv, sv) in enumerate(zip(chunks, dense_vectors, sparse_vectors)):
        payload = {
            "text": chunk["text"],
            "source": chunk["source"],
            "department": chunk["department"],
            "role": chunk["role"],
            "chunk_id": chunk["chunk_id"],
            "page": chunk.get("page"),
        }

        points.append(
            rest.PointStruct(
                id=i,
                vector={
                    "dense": dv.tolist(),
                    "sparse": rest.SparseVector(
                        indices=sv.indices.tolist(),
                        values=sv.values.tolist(),
                    ),
                },
                payload=payload,
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"✅  Upserted {len(points)} fixture chunks into '{COLLECTION_NAME}'.")


def verify(client: QdrantClient) -> bool:
    """Run the Day 0 VERIFY checklist."""
    count = client.count(collection_name=COLLECTION_NAME).count
    print(f"\n─── VERIFY ─────────────────────────────────")
    print(f"  Total chunks : {count}")

    hr_count = client.count(
        collection_name=COLLECTION_NAME,
        count_filter=rest.Filter(
            must=[rest.FieldCondition(key="department", match=rest.MatchValue(value="HR"))]
        ),
    ).count

    sales_count = client.count(
        collection_name=COLLECTION_NAME,
        count_filter=rest.Filter(
            must=[rest.FieldCondition(key="department", match=rest.MatchValue(value="Sales"))]
        ),
    ).count

    ok_count = count == 20
    ok_hr = hr_count >= 1
    ok_sales = sales_count >= 1

    print(f"  HR chunks    : {hr_count}  {'✅' if ok_hr else '❌'}")
    print(f"  Sales chunks : {sales_count}  {'✅' if ok_sales else '❌'}")
    print(f"  Total == 20  : {'✅' if ok_count else f'❌  got {count}'}")
    print(f"─────────────────────────────────────────────\n")

    return ok_count and ok_hr and ok_sales


def main() -> None:
    parser = argparse.ArgumentParser(description="Day 0 — Qdrant setup & fixture load")
    parser.add_argument("--verify-only", action="store_true", help="Skip setup, only run VERIFY")
    parser.add_argument(
        "--fixtures",
        default="fixtures/mock_chunks.json",
        help="Path to fixture JSON (default: fixtures/mock_chunks.json)",
    )
    args = parser.parse_args()

    client = _get_client()

    if not args.verify_only:
        create_collection(client)
        fixtures_path = Path(args.fixtures)
        if not fixtures_path.exists():
            print(f"❌  Fixtures file not found: {fixtures_path}")
            sys.exit(1)
        load_fixtures(client, fixtures_path)

    create_payload_indexes(client)

    success = verify(client)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
