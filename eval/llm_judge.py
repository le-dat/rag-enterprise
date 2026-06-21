import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
from src.config import settings

logger = logging.getLogger("llm_judge")

class LLMJudge:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.LLM_MODEL
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY is not configured in settings. LLMJudge will not be functional.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)

    def evaluate_context_precision(self, question: str, retrieved_chunks: List[Dict[str, Any]]) -> float:
        """
        Evaluate Context Precision:
        For each chunk, ask the LLM if it is relevant to the question.
        Compute Average Precision (AP) based on ranking of relevant chunks.
        """
        if not self.client or not retrieved_chunks:
            return 0.0

        relevancy_list = []
        for i, chunk in enumerate(retrieved_chunks):
            chunk_text = chunk.get("text", "")
            system_prompt = (
                "You are an expert AI evaluator. Your job is to check if a specific retrieved text chunk is relevant for answering a user's question.\n"
                "Respond in JSON format with a single key 'relevant' containing a boolean value (true/false) and a brief 'reason' explaining your decision."
            )
            user_prompt = (
                f"Question: {question}\n\n"
                f"Retrieved Chunk Content: {chunk_text}\n\n"
                "Is the chunk relevant to the question? Return JSON: {\"relevant\": true/false, \"reason\": \"string\"}"
            )

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0
                )
                res_data = json.loads(response.choices[0].message.content)
                is_relevant = bool(res_data.get("relevant", False))
                relevancy_list.append(is_relevant)
                logger.debug(f"Chunk {i+1} relevance: {is_relevant}. Reason: {res_data.get('reason')}")
            except Exception as e:
                logger.error(f"Error evaluating chunk relevance: {e}")
                relevancy_list.append(False)  # Fallback

        # Calculate Average Precision (AP)
        # AP = sum(Precision@k * rel(k)) / number of relevant chunks
        relevant_count = 0
        precision_sum = 0.0

        for k, is_relevant in enumerate(relevancy_list, 1):
            if is_relevant:
                relevant_count += 1
                precision_at_k = relevant_count / k
                precision_sum += precision_at_k

        if relevant_count == 0:
            return 0.0

        return precision_sum / len(retrieved_chunks)

    def evaluate_context_recall(self, question: str, retrieved_chunks: List[Dict[str, Any]], ground_truth: str) -> float:
        """
        Evaluate Context Recall:
        Verify if the ground truth statement can be fully deduced from the retrieved context.
        """
        if not self.client or not retrieved_chunks or not ground_truth:
            return 0.0

        context_str = "\n\n".join([
            f"Chunk [{c.get('chunk_id', 'unknown')}]: {c.get('text', '')}"
            for c in retrieved_chunks
        ])

        system_prompt = (
            "You are an expert AI evaluator. Your job is to check if all the key facts/information in the Ground Truth answer can be fully found or deduced from the provided Context chunks.\n"
            "Rate the recall from 0.0 (no overlap) to 1.0 (all facts in Ground Truth are fully supported by the Context).\n"
            "Respond in JSON format with two keys: 'score' (a float between 0.0 and 1.0) and 'reason' (a brief explanation)."
        )
        user_prompt = (
            f"Question: {question}\n\n"
            f"Ground Truth Answer: {ground_truth}\n\n"
            f"Provided Context Chunks:\n{context_str}\n\n"
            "Can the ground truth be fully deduced from the context? Rate from 0.0 to 1.0. Return JSON: {\"score\": float, \"reason\": \"string\"}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            res_data = json.loads(response.choices[0].message.content)
            score = float(res_data.get("score", 0.0))
            logger.debug(f"Recall score: {score}. Reason: {res_data.get('reason')}")
            return min(1.0, max(0.0, score))
        except Exception as e:
            logger.error(f"Error evaluating context recall: {e}")
            return 0.0

    def evaluate_answer_relevancy(self, question: str, answer: str) -> float:
        """
        Evaluate Answer Relevancy:
        Verify if the generated answer directly addresses the question and doesn't contain redundant/irrelevant information.
        """
        if not self.client or not answer or not question:
            return 0.0

        system_prompt = (
            "You are an expert AI evaluator. Your job is to evaluate if a generated answer is relevant, complete, and directly addresses the user's question, without containing redundant or completely irrelevant statements.\n"
            "Rate the relevancy from 0.0 (completely irrelevant or plain refusal) to 1.0 (perfectly relevant and directly answers the question).\n"
            "Respond in JSON format with two keys: 'score' (a float between 0.0 and 1.0) and 'reason' (a brief explanation)."
        )
        user_prompt = (
            f"Question: {question}\n\n"
            f"Generated Answer: {answer}\n\n"
            "Does the answer directly address the question? Rate from 0.0 to 1.0. Return JSON: {\"score\": float, \"reason\": \"string\"}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            res_data = json.loads(response.choices[0].message.content)
            score = float(res_data.get("score", 0.0))
            logger.debug(f"Relevancy score: {score}. Reason: {res_data.get('reason')}")
            return min(1.0, max(0.0, score))
        except Exception as e:
            logger.error(f"Error evaluating answer relevancy: {e}")
            return 0.0
