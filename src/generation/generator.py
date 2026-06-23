import logging
from typing import List, Dict, Any
from src.core.llm_factory import get_openai_client
from src.core.config import settings

logger = logging.getLogger(__name__)

class OpenAIGenerator:
    def __init__(self):
        self.client = get_openai_client()
        self.model = self.client.model if self.client else settings.OPENAI_MODEL

    def generate(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """
        Generates an answer based on retrieved documents, enforcing strict citation of [chunk_id].
        
        Args:
            query: The user's query.
            documents: List of dicts, containing 'chunk_id', 'text', 'source', 'page'.
            
        Returns:
            The generated response with citations.
        """
        if not self.client:
            return "Generation is currently disabled (OPENAI_API_KEY missing)."

        if not documents:
            return "No relevant context was found to answer this query. Access denied or no matching documents."

        # 1. Format Context
        context_blocks = []
        for doc in documents:
            chunk_id = doc.get("chunk_id", "unknown")
            text = doc.get("text", "")
            source = doc.get("source", "unknown")
            page = doc.get("page", "N/A")
            
            context_blocks.append(
                f"--- START CHUNK [{chunk_id}] ---\n"
                f"Source: {source} (Page: {page})\n"
                f"Content: {text}\n"
                f"--- END CHUNK [{chunk_id}] ---"
            )
            
        context_str = "\n\n".join(context_blocks)

        # 2. System and User Prompts
        system_prompt = (
            "You are a highly secure Enterprise RAG Assistant. Your job is to answer user queries using only the provided context chunks.\n"
            "Strict Guidelines:\n"
            "1. Answer the query based ONLY on the provided context chunks. Do not assume, extrapolate, or use outside knowledge.\n"
            "2. For EVERY claim, fact, or statement you make in your answer, you MUST cite the source chunk using its ID in brackets (e.g. [chunk_id]) at the end of the sentence. Never combine citations or omit them.\n"
            "3. If the provided context does not contain enough information to answer the query, state clearly: "
            "'I cannot answer this query based on the retrieved context. Insufficient information or lack of permissions.'\n"
            "4. Match the language of the query. If the query is in Vietnamese, respond in Vietnamese. If in English, respond in English."
        )

        user_prompt = (
            f"Here is the retrieved context:\n\n{context_str}\n\n"
            f"User Query: {query}\n\n"
            f"Generate your cited answer below:"
        )

        try:
            logger.info(f"Generating LLM response using model: {self.model} for query: '{query}'")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0  # Lowest temperature to reduce hallucinations
            )
            
            answer = response.choices[0].message.content
            logger.info("LLM generation completed successfully.")
            return answer

        except Exception as e:
            logger.error(f"Error during OpenAI Generation: {e}", exc_info=True)
            return f"An error occurred while generating the answer: {str(e)}"
