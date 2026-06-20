from unittest.mock import MagicMock, patch
from src.retrieval.reranker import CohereReranker
from src.generation.generator import OpenAIGenerator
from src.generation.grounding import GroundingChecker

# ───────────────────────────────────────────────────────────
# 1. CohereReranker Tests
# ───────────────────────────────────────────────────────────

def test_reranker_success(mocker):
    # Mock Cohere Client
    mock_cohere_client = mocker.patch("cohere.Client")
    mock_instance = mock_cohere_client.return_value
    
    # Mock Cohere response
    mock_result_1 = MagicMock()
    mock_result_1.index = 1
    mock_result_1.relevance_score = 0.95
    
    mock_result_2 = MagicMock()
    mock_result_2.index = 0
    mock_result_2.relevance_score = 0.45
    
    mock_instance.rerank.return_value.results = [mock_result_1, mock_result_2]

    # Initialize Reranker with fake key to ensure client is created
    with patch("src.config.settings.COHERE_API_KEY", "fake_key"):
        reranker = CohereReranker()
        
    docs = [
        {"chunk_id": "doc_A", "text": "This is doc A text"},
        {"chunk_id": "doc_B", "text": "This is doc B text"}
    ]
    
    results = reranker.rerank(query="test query", documents=docs, top_n=2)
    
    assert len(results) == 2
    # Verify index mapping: first item should be original index 1 (doc_B)
    assert results[0]["chunk_id"] == "doc_B"
    assert results[0]["score"] == 0.95
    # Second item should be original index 0 (doc_A)
    assert results[1]["chunk_id"] == "doc_A"
    assert results[1]["score"] == 0.45

def test_reranker_missing_key_fallback():
    # When api key is missing, should return slice of documents directly
    with patch("src.config.settings.COHERE_API_KEY", ""):
        reranker = CohereReranker()
        
    docs = [
        {"chunk_id": "doc_A", "text": "This is doc A text"},
        {"chunk_id": "doc_B", "text": "This is doc B text"}
    ]
    
    results = reranker.rerank(query="test query", documents=docs, top_n=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "doc_A"

# ───────────────────────────────────────────────────────────
# 2. OpenAIGenerator Tests
# ───────────────────────────────────────────────────────────

def test_generator_success(mocker):
    mock_openai_client = mocker.patch("src.generation.generator.OpenAI")
    mock_instance = mock_openai_client.return_value
    
    # Mock LLM completion response
    mock_choice = MagicMock()
    mock_choice.message.content = "This is a mocked answer [doc_A]."
    mock_instance.chat.completions.create.return_value.choices = [mock_choice]
    
    with patch("src.config.settings.OPENAI_API_KEY", "fake_key"):
        generator = OpenAIGenerator()
        
    docs = [
        {"chunk_id": "doc_A", "text": "This is doc A text", "source": "A.pdf", "page": 1}
    ]
    
    answer = generator.generate(query="what is A?", documents=docs)
    assert "mocked answer" in answer
    assert "[doc_A]" in answer

def test_generator_empty_context():
    with patch("src.config.settings.OPENAI_API_KEY", "fake_key"):
        generator = OpenAIGenerator()
        
    answer = generator.generate(query="what is A?", documents=[])
    assert "No relevant context was found" in answer

# ───────────────────────────────────────────────────────────
# 3. GroundingChecker Tests
# ───────────────────────────────────────────────────────────

def test_grounding_checker_success(mocker):
    mock_openai_client = mocker.patch("src.generation.grounding.OpenAI")
    mock_instance = mock_openai_client.return_value
    
    # Mock json response from auditor
    mock_choice = MagicMock()
    mock_choice.message.content = '{"grounded": true, "reason": "All facts match context."}'
    mock_instance.chat.completions.create.return_value.choices = [mock_choice]
    
    with patch("src.config.settings.OPENAI_API_KEY", "fake_key"):
        checker = GroundingChecker()
        
    docs = [
        {"chunk_id": "doc_A", "text": "This is doc A text"}
    ]
    
    res = checker.check_grounding(documents=docs, answer="This is doc A text")
    assert res["grounded"] is True
    assert "All facts match" in res["reason"]

def test_grounding_checker_insufficient_context_refusal():
    # If the answer is an explicit refusal, it is grounded by default
    with patch("src.config.settings.OPENAI_API_KEY", "fake_key"):
        checker = GroundingChecker()
        
    res = checker.check_grounding(documents=[], answer="I cannot answer this query based on the retrieved context.")
    assert res["grounded"] is True
    assert "insufficient" in res["reason"].lower() or "missing" in res["reason"].lower()
