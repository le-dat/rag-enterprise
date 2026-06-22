import logging
from typing import List, Dict, Any
from llama_index.core.schema import TextNode
from fastembed import TextEmbedding, SparseTextEmbedding
from src.config import settings

logger = logging.getLogger(__name__)

class DocumentEmbedder:
    def __init__(
        self, 
        dense_model_name: str = "BAAI/bge-small-en-v1.5",
        sparse_model_name: str = "prithivida/Splade_PP_en_v1"
    ):
        logger.info(f"Initializing dense model: {dense_model_name}")
        self.dense_model = TextEmbedding(model_name=dense_model_name, threads=settings.EMBEDDING_THREADS)
        
        logger.info(f"Initializing sparse model: {sparse_model_name}")
        self.sparse_model = SparseTextEmbedding(model_name=sparse_model_name, threads=settings.EMBEDDING_THREADS)

    def embed_nodes(self, nodes: List[TextNode]) -> List[Dict[str, Any]]:
        """
        Embeds a list of TextNodes, generating dense and sparse representation for each.
        Returns a list of dictionaries containing the node, its dense list, and its sparse model representation.
        """
        if not nodes:
            return []
            
        texts = [node.text for node in nodes]
        
        logger.info(f"Generating dense embeddings for {len(texts)} chunks...")
        dense_embeddings = list(self.dense_model.embed(texts))
        
        logger.info(f"Generating sparse embeddings for {len(texts)} chunks...")
        sparse_embeddings = list(self.sparse_model.embed(texts))
        
        embedded_data = []
        for node, dense_vec, sparse_vec in zip(nodes, dense_embeddings, sparse_embeddings):
            embedded_data.append({
                "node": node,
                "dense": dense_vec.tolist(),
                "sparse": {
                    "indices": sparse_vec.indices.tolist(),
                    "values": sparse_vec.values.tolist()
                }
            })
            
        logger.info("Embedding generation completed.")
        return embedded_data
