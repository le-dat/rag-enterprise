import logging
from typing import List, Dict, Any
import cohere
from src.config import settings

logger = logging.getLogger(__name__)

class CohereReranker:
    def __init__(self):
        self.api_key = settings.COHERE_API_KEY
        self.model = settings.COHERE_MODEL
        
        if not self.api_key:
            logger.warning("COHERE_API_KEY is not configured in settings. Reranking will be disabled.")
            self.client = None
        else:
            self.client = cohere.Client(api_key=self.api_key)

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Reranks a list of documents using Cohere Rerank API.
        
        Args:
            query: The search query.
            documents: List of dicts, where each dict must have a 'text' key.
            top_n: Number of top documents to return.
            
        Returns:
            List of reranked documents with updated scores.
        """
        if not self.client or not documents:
            logger.info("Reranking skipped (no Cohere client or empty documents).")
            return documents[:top_n]

        try:
            # Extract texts for reranking
            texts = [doc["text"] for doc in documents if "text" in doc]
            if not texts:
                logger.warning("No text found in documents to rerank.")
                return documents[:top_n]

            logger.info(f"Sending {len(texts)} documents to Cohere Rerank (model: {self.model})")
            
            response = self.client.rerank(
                model=self.model,
                query=query,
                documents=texts,
                top_n=top_n
            )
            
            reranked_docs = []
            for result in response.results:
                orig_idx = result.index
                orig_doc = documents[orig_idx]
                
                # Create a copy and update the score with Cohere's relevance score
                new_doc = orig_doc.copy()
                new_doc["score"] = float(result.relevance_score)
                reranked_docs.append(new_doc)
                
            logger.info(f"Reranking complete. Returned {len(reranked_docs)} documents.")
            return reranked_docs

        except Exception as e:
            logger.error(f"Error during Cohere Reranking: {e}", exc_info=True)
            # Fallback to top_n original documents if API call fails
            return documents[:top_n]
