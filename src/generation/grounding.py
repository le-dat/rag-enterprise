import logging
import json
from typing import List, Dict, Any
from src.core.llm_factory import get_openai_client
from src.core.config import settings

logger = logging.getLogger(__name__)

class GroundingChecker:
    def __init__(self):
        self.client = get_openai_client()
        self.model = self.client.model if self.client else settings.OPENAI_MODEL

    def check_grounding(self, documents: List[Dict[str, Any]], answer: str) -> Dict[str, Any]:
        """
        Validates if the generated answer is fully grounded in the retrieved documents.
        Uses GPT-4o-mini in JSON mode.
        
        Args:
            documents: List of retrieved/reranked document dicts containing 'text' and 'chunk_id'.
            answer: The generated answer to verify.
            
        Returns:
            Dict containing 'grounded' (bool) and 'reason' (str).
        """
        if not self.client:
            return {
                "grounded": False,
                "reason": "Grounding checker is disabled (OPENAI_API_KEY missing)."
            }

        # If answer is indicating insufficient context, it is grounded (since it correctly refused to answer)
        insufficient_markers = [
            "insufficient information",
            "lack of permissions",
            "cannot answer",
        ]
        if any(marker in answer.lower() for marker in insufficient_markers):
            return {
                "grounded": True,
                "reason": "Answer correctly states that retrieved context is insufficient or missing."
            }

        # 1. Format Context
        context_text = ""
        for i, doc in enumerate(documents):
            chunk_id = doc.get("chunk_id", f"chunk_{i}")
            text = doc.get("text", "")
            context_text += f"[{chunk_id}]: {text}\n\n"

        # 2. System and User Prompts
        system_prompt = (
            "You are an independent RAG Quality Auditor.\n"
            "Your job is to examine if the provided Answer is strictly grounded in the Context. "
            "Every claim, fact, and detail in the Answer MUST be directly supported by the Context.\n"
            "If the Answer contains any assumptions, outside facts, or claims NOT found in the Context, "
            "then the Answer is NOT grounded.\n\n"
            "You must respond in JSON format ONLY, matching this schema:\n"
            "{\n"
            "  \"grounded\": true | false,\n"
            "  \"reason\": \"Detailed explanation. If grounded is true, confirm all claims are supported. If false, point out the exact claims that are unsupported.\"\n"
            "}"
        )

        user_prompt = (
            f"--- START CONTEXT ---\n{context_text}--- END CONTEXT ---\n\n"
            f"--- START ANSWER ---\n{answer}\n--- END ANSWER ---\n\n"
            "Examine the answer and verify grounding. Provide JSON output:"
        )

        try:
            logger.info("Executing grounding check...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            result_content = response.choices[0].message.content
            logger.info(f"Grounding check raw response: {result_content}")
            
            result = json.loads(result_content)
            
            # Simple validation on output keys
            if "grounded" not in result or "reason" not in result:
                raise ValueError("Response JSON is missing required fields.")
                
            return {
                "grounded": bool(result["grounded"]),
                "reason": str(result["reason"])
            }

        except Exception as e:
            logger.error(f"Error during Grounding Check: {e}", exc_info=True)
            return {
                "grounded": False,
                "reason": f"Grounding check failed to execute or parse: {str(e)}"
            }
