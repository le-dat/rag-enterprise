import logging
import re
from groq import Groq
from src.core.config import settings

logger = logging.getLogger(__name__)

# Raised when a query is blocked by the Input Rail
class QueryBlockedError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Query blocked by Input Rail: {reason}")


class InputRail:
    """
    Input Rail: filters malicious, jailbreak, or prompt-injection queries
    before they reach the retrieval pipeline.

    Two-layer defence:
    1. Regex heuristics — zero-latency pre-filter for obvious patterns.
    2. Llama Prompt Guard 2 via Groq — probabilistic scoring for subtle attacks.
    """

    # Patterns that are clearly malicious regardless of context
    _HEURISTIC_PATTERNS = [
        r"ignore\s+(?:previous|above|all|every|prior)\s+(?:instructions?|prompts?|directives?|rules?)",
        r"forget\s+(?:previous|above|all|every|prior)\s+(?:instructions?|prompts?|directives?|rules?)",
        r"you\s+are\s+now\s+(?:a|an|the)",
        r"act\s+as\s+(?:a|an|the)\s+(?:dan|jailbreak|evil|unrestricted)",
        r"disregard\s+(?:your|all|the)\s+(?:instructions?|guidelines?|rules?|training)",
        r"override\s+(?:your|the|all)\s+(?:instructions?|directives?|safety)",
        r"new\s+(?:system\s+)?(?:instruction|directive|prompt|rule)",
        r"system\s*:\s*\S",                    # bare "system:" injection
        r"<\s*system\s*>",                      # XML-style system tag
        r"\[\s*system\s*\]",                    # bracket-style system tag
        r"reveal\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?)",
        r"print\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?)",
    ]

    def __init__(self):
        api_key = settings.GROQ_API_KEY
        self._model = settings.GROQ_MODEL

        if not api_key:
            logger.warning(
                "GROQ_API_KEY not set — Input Rail running in heuristic-only mode."
            )
            self._client = None
        else:
            self._client = Groq(api_key=api_key)

        self._compiled = [re.compile(p, re.IGNORECASE) for p in self._HEURISTIC_PATTERNS]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_query(self, query: str) -> None:
        """
        Validates a user query. Raises QueryBlockedError if the query is
        deemed unsafe. Returns None silently when the query is safe.

        Args:
            query: The raw user query string.

        Raises:
            QueryBlockedError: If the query contains jailbreak / injection content.
        """
        if not query or not query.strip():
            return

        # Layer 1 — heuristic regex (no network call)
        if self._matches_heuristic(query):
            logger.warning(f"🚨 INPUT RAIL [heuristic]: blocked query → {query[:120]!r}")
            raise QueryBlockedError("Query contains a known prompt-injection pattern.")

        # Layer 2 — Llama Prompt Guard 2 (only if GROQ configured)
        if self._client:
            self._validate_with_llm(query)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _matches_heuristic(self, query: str) -> bool:
        query_lower = query.lower()
        return any(p.search(query_lower) for p in self._compiled)

    def _validate_with_llm(self, query: str) -> None:
        """Calls Llama Prompt Guard 2 via Groq. Raises QueryBlockedError if unsafe."""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": query}],
                temperature=0.0,
            )
            verdict = response.choices[0].message.content.strip()
            logger.info(f"Input Rail LLM verdict: {verdict!r} for query: {query[:80]!r}")

            is_unsafe = self._parse_verdict(verdict)
            if is_unsafe:
                logger.warning(f"🚨 INPUT RAIL [LLM]: blocked query → {query[:120]!r}")
                raise QueryBlockedError(
                    "Query was flagged as unsafe by the language model guard."
                )

        except QueryBlockedError:
            raise
        except Exception as exc:
            # Guard failure → fail open (let query through, log for review)
            logger.error(f"Input Rail LLM check failed — failing open: {exc}", exc_info=True)

    @staticmethod
    def _parse_verdict(verdict: str) -> bool:
        """Returns True if the verdict indicates an unsafe query."""
        try:
            score = float(verdict)
            return score > 0.5
        except ValueError:
            low = verdict.lower()
            return low.startswith("unsafe") or "malicious" in low or "injection" in low
