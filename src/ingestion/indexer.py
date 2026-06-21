import logging
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from src.config import settings

logger = logging.getLogger(__name__)

class QdrantIndexer:
    def __init__(self):
        self.url = settings.QDRANT_URL
        self.api_key = settings.QDRANT_API_KEY
        self.collection_name = settings.QDRANT_COLLECTION
        
        if not self.url:
            raise ValueError("QDRANT_URL is not configured in settings.")
            
        self.client = QdrantClient(url=self.url, api_key=self.api_key)

    def index_embedded_data(self, embedded_data: List[Dict[str, Any]]) -> int:
        """
        Upsert a list of embedded chunks into the Qdrant collection.
        Returns the number of successfully indexed points.
        """
        if not embedded_data:
            logger.info("No data to index.")
            return 0
            
        points = []
        for idx, item in enumerate(embedded_data):
            node = item["node"]
            dense_vector = item["dense"]
            sparse_data = item["sparse"]
            
            # Map standard payload matching verify tests
            payload = {
                "text": node.text,
                **node.metadata
            }
            
            # Form Qdrant point structure
            points.append(
                rest.PointStruct(
                    # We can use a hash of chunk_id or index-based ID for simplicity.
                    # Since PointStruct ID can be UUID string or int, we generate a deterministic int or use UUID.
                    # Qdrant client accepts string UUIDs. Let's use a string UUID based on chunk_id to keep it unique but idempotent.
                    id=self._generate_uuid_id(node.id_),
                    vector={
                        "dense": dense_vector,
                        "sparse": rest.SparseVector(
                            indices=sparse_data["indices"],
                            values=sparse_data["values"]
                        )
                    },
                    payload=payload
                )
            )
            
        logger.info(f"Upserting {len(points)} points into Qdrant collection '{self.collection_name}'...")
        
        # Batch upsert to Qdrant
        response = self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Index operation finished. Status: {response.status}")
        return len(points)

    def _generate_uuid_id(self, chunk_id: str) -> str:
        """Generate a deterministic UUID from a chunk_id for idempotency."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))
