import logging
import re
from typing import List, Dict, Any
from groq import Groq
from src.core.config import settings

logger = logging.getLogger(__name__)

class RetrievalRail:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        
        if not self.api_key:
            logger.warning("GROQ_API_KEY is not configured in settings. Retrieval Rail is disabled.")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)

    def validate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validates retrieved chunks using Llama Guard via Groq API.
        Removes any chunks flagged as unsafe (prompt injection, etc.).
        
        Args:
            chunks: List of retrieved/reranked document dicts containing 'text' and 'chunk_id'.
            
        Returns:
            Filtered list of chunks containing only safe content.
        """
        if not self.client or not chunks:
            return chunks

        # Heuristic patterns for common prompt injection triggers
        suspicious_patterns = [
            r"ignore\s+(?:previous|above|everything|instructions|directive|prompt)",
            r"forget\s+(?:previous|above|everything|instructions|directive|prompt)",
            r"system\s*:",
            r"system\s+(?:instruction|directive|prompt)",
            r"you\s+are\s+now",
            r"new\s+(?:instruction|directive|prompt)",
            r"override\s+(?:instruction|directive|prompt)"
        ]

        safe_chunks = []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "unknown")
            text = chunk.get("text", "")
            
            if not text:
                safe_chunks.append(chunk)
                continue

            # Heuristic pre-filter to skip API calls for obviously safe chunks
            is_suspicious = False
            text_lower = text.lower()
            for pattern in suspicious_patterns:
                if re.search(pattern, text_lower):
                    is_suspicious = True
                    break

            if not is_suspicious:
                safe_chunks.append(chunk)
                continue

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": text}
                    ],
                    temperature=0.0
                )
                
                verdict = response.choices[0].message.content.strip()
                logger.info(f"Retrieval Rail verdict for '{chunk_id}': {verdict}")
                
                # Check if verdict is a float score (Llama Prompt Guard format) or text (Llama Guard format)
                is_unsafe = False
                try:
                    score = float(verdict)
                    if score > 0.5:
                        is_unsafe = True
                except ValueError:
                    if verdict.lower().startswith("unsafe") or "malicious" in verdict.lower():
                        is_unsafe = True

                if is_unsafe:
                    logger.warning(f"🚨 SECURITY ALERT: Chunk '{chunk_id}' was flagged as UNSAFE and BLOCKED.")
                else:
                    safe_chunks.append(chunk)
                    
            except Exception as e:
                logger.error(f"Error validating safety for chunk '{chunk_id}': {e}", exc_info=True)
                # Fallback: keep the chunk if safety checker fails (so system remains functional)
                safe_chunks.append(chunk)
                
        return safe_chunks
