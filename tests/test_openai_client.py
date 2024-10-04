import pytest
from services.openai_client import get_model_answer

def test_get_model_answer():
    question = "What is the capital of France?"
    answer = get_model_answer(question)
    assert isinstance(answer, str)
    assert len(answer) > 0