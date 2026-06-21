import argparse
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
from src.core.logging import configure_logging
from src.ingestion.router import IngestionRouter
from src.ingestion.chunker import DocumentChunker
from src.ingestion.embedder import DocumentEmbedder
from src.ingestion.indexer import QdrantIndexer

from src.guardrails.retrieval_rail import RetrievalRail

# Config logging
configure_logging()
logger = logging.getLogger("ingestion_pipeline")

load_dotenv()

def run_pipeline(file_path: str, department: str, role: str) -> None:
    path = Path(file_path)
    if not path.exists():
        logger.error(f"Input file not found at: {file_path}")
        sys.exit(1)

    logger.info(f"🚀 Starting ingestion pipeline for file: {path.name}")
    logger.info(f"RBAC Policy -> Department: {department} | Role: {role}")

    # Step 1: Parse
    router = IngestionRouter()
    documents = router.parse_file(path)
    if not documents:
        logger.warning("No documents were parsed. Exiting.")
        return

    # Step 2: Chunk & Attach RBAC Metadata
    chunker = DocumentChunker()
    chunks = chunker.chunk_documents(
        documents=documents,
        department=department,
        role=role
    )
    if not chunks:
        logger.warning("No chunks were generated. Exiting.")
        return

    # Step 2.5: Ingestion-Time Safety Scan (RetrievalRail)
    logger.info("Applying Ingestion-Time Safety Scan on chunks...")
    rail = RetrievalRail()
    rail_chunks = [{"chunk_id": node.id_, "text": node.text} for node in chunks]
    safe_rail_chunks = rail.validate_chunks(rail_chunks)
    safe_chunk_ids = {c["chunk_id"] for c in safe_rail_chunks}
    
    filtered_chunks = [node for node in chunks if node.id_ in safe_chunk_ids]
    blocked_chunks = [node for node in chunks if node.id_ not in safe_chunk_ids]
    blocked_count = len(blocked_chunks)
    if blocked_count > 0:
        logger.error(
            f"🚨 SECURITY ALERT: Blocked {blocked_count} poisoned chunk(s) during ingestion of file '{path.name}'.\n"
            f"Blocked Chunk IDs: {[node.id_ for node in blocked_chunks]}\n"
            f"Sample blocked content: {[node.text[:100] + '...' for node in blocked_chunks]}"
        )
    
    chunks = filtered_chunks
    if not chunks:
        logger.warning(f"No safe chunks left after security scanning for file '{path.name}'. Ingestion aborted.")
        return

    # Step 3: Embed
    embedder = DocumentEmbedder()
    embedded_data = embedder.embed_nodes(chunks)

    # Step 4: Index into Qdrant
    indexer = QdrantIndexer()
    indexed_count = indexer.index_embedded_data(embedded_data)

    logger.info(f"🎉 Successfully ingested and indexed {indexed_count} chunks into Qdrant!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enterprise RAG Ingestion Pipeline")
    parser.add_argument("--file", required=True, help="Path to the source file (PDF, XLSX, TXT)")
    parser.add_argument("--department", required=True, help="RBAC department metadata (e.g. HR, Sales)")
    parser.add_argument("--role", required=True, help="RBAC role level metadata (e.g. manager, staff)")
    
    args = parser.parse_args()
    
    run_pipeline(
        file_path=args.file,
        department=args.department,
        role=args.role
    )
