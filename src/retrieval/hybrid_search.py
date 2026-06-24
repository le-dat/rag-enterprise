import logging
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from fastembed import TextEmbedding, SparseTextEmbedding

from src.core.config import settings
from src.auth.jwt_handler import UserContext
from src.retrieval.rbac_filter import build_qdrant_rbac_filter

logger = logging.getLogger(__name__)

class HybridSearchEngine:
    def __init__(
        self,
        dense_model_name: str = "BAAI/bge-small-en-v1.5",
        sparse_model_name: str = "prithivida/Splade_PP_en_v1"
    ):
        self.url = settings.QDRANT_URL
        self.api_key = settings.QDRANT_API_KEY
        self.collection_name = settings.QDRANT_COLLECTION
        
        if not self.url:
            raise ValueError("QDRANT_URL is not configured in settings.")
            
        self.client = QdrantClient(url=self.url, api_key=self.api_key, check_compatibility=False)
        
        logger.info(f"Loading search embedding models: dense={dense_model_name}, sparse={sparse_model_name}")
        self.dense_model = TextEmbedding(model_name=dense_model_name, threads=settings.EMBEDDING_THREADS)
        self.sparse_model = SparseTextEmbedding(model_name=sparse_model_name, threads=settings.EMBEDDING_THREADS)

    def search(self, query_text: str, user: UserContext, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Executes hybrid search (dense + sparse) on Qdrant,
        applying RBAC filters at vector DB level, fused using Reciprocal Rank Fusion (RRF).
        """
        logger.info(f"Executing search for: '{query_text}' by user: {user.user_id} ({user.department}/{user.role})")
        
        # 1. Generate Query Embeddings
        dense_vector = list(self.dense_model.embed([query_text]))[0].tolist()
        sparse_vector_res = list(self.sparse_model.embed([query_text]))[0]
        
        sparse_vector = rest.SparseVector(
            indices=sparse_vector_res.indices.tolist(),
            values=sparse_vector_res.values.tolist()
        )
        
        # 2. Build RBAC Filter
        rbac_filter = build_qdrant_rbac_filter(user)
        
        # 3. Create Prefetch Configurations
        # Native hybrid RRF in Qdrant requires prefetching dense and sparse query channels
        dense_prefetch = rest.Prefetch(
            query=dense_vector,
            using="dense",
            filter=rbac_filter,
            limit=limit * 2  # Over-retrieve to improve fusion pool diversity
        )
        
        sparse_prefetch = rest.Prefetch(
            query=sparse_vector,
            using="sparse",
            filter=rbac_filter,
            limit=limit * 2
        )
        
        # 4. Execute Native Fusion Query
        response = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[dense_prefetch, sparse_prefetch],
            query=rest.FusionQuery(fusion=rest.Fusion.RRF),
            limit=limit,
            with_payload=True
        )
        
        # 5. Format results cleanly
        results = []
        for point in response.points:
            payload = point.payload or {}
            results.append({
                "chunk_id": payload.get("chunk_id"),
                "text": payload.get("text"),
                "source": payload.get("source"),
                "department": payload.get("department"),
                "role": payload.get("role"),
                "page": payload.get("page"),
                "score": point.score  # Fused RRF score
            })
            
        logger.info(f"Search completed. Found {len(results)} matches after RBAC filter.")
        return results
