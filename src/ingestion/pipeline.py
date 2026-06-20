import argparse
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
from src.ingestion.router import IngestionRouter
from src.ingestion.chunker import DocumentChunker
from src.ingestion.embedder import DocumentEmbedder
from src.ingestion.indexer import QdrantIndexer

# Config logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ingestion_pipeline")

# Load environment
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
