"""
Unit tests for backend/intelligence/summary.py.

All Gemini calls are mocked — see backend/tests/manual_test_summary_live.py
for a real-API smoke test.
"""
import json
from unittest.mock import MagicMock

import pytest

from backend.intelligence.llm_client import LLMError
from backend.intelligence.summary import get_document_summary
from backend.processing.structure import Section


def _mock_client_returning(response_dict: dict) -> MagicMock:
    """Build a mock Gemini client whose models.generate_content(...) returns
    an object with the given dict JSON-encoded in its .text attribute."""
    client = MagicMock()
    response = MagicMock()
    response.text = json.dumps(response_dict)
    client.models.generate_content.return_value = response
    return client


def _sample_sections():
    return [
        Section(title="Introduction", level=1, content="This document is about operating systems."),
        Section(title="Process Management", level=1, content="Processes are managed by the kernel."),
    ]


def test_empty_sections_raises_llm_error_without_calling_llm():
    client = MagicMock()
    with pytest.raises(LLMError):
        get_document_summary([], client=client)
    client.models.generate_content.assert_not_called()


def test_happy_path_parses_summary_and_key_points():
    mock_response = {
        "document_summary": "This document introduces operating systems and process management.",
        "key_points": ["Covers OS fundamentals", "Explains process scheduling"],
    }
    client = _mock_client_returning(mock_response)
    result = get_document_summary(_sample_sections(), client=client)

    assert result.document_summary == mock_response["document_summary"]
    assert result.key_points == mock_response["key_points"]


def test_sends_all_section_content_to_the_llm():
    mock_response = {"document_summary": "S" * 10, "key_points": ["a point"]}
    client = _mock_client_returning(mock_response)
    get_document_summary(_sample_sections(), client=client)

    call_kwargs = client.models.generate_content.call_args.kwargs
    prompt = call_kwargs["contents"]
    assert "operating systems" in prompt.lower()
    assert "Process Management" in prompt


def test_missing_document_summary_key_raises_llm_error():
    client = _mock_client_returning({"key_points": ["a point"]})
    with pytest.raises(LLMError):
        get_document_summary(_sample_sections(), client=client)


def test_empty_document_summary_string_raises_llm_error():
    client = _mock_client_returning({"document_summary": "   ", "key_points": ["a point"]})
    with pytest.raises(LLMError):
        get_document_summary(_sample_sections(), client=client)


def test_non_string_document_summary_raises_llm_error():
    client = _mock_client_returning({"document_summary": 12345, "key_points": ["a point"]})
    with pytest.raises(LLMError):
        get_document_summary(_sample_sections(), client=client)


def test_key_points_not_a_list_raises_llm_error():
    client = _mock_client_returning({"document_summary": "A valid summary.", "key_points": "not a list"})
    with pytest.raises(LLMError):
        get_document_summary(_sample_sections(), client=client)


def test_key_points_with_non_string_items_raises_llm_error():
    client = _mock_client_returning({"document_summary": "A valid summary.", "key_points": ["ok", 42]})
    with pytest.raises(LLMError):
        get_document_summary(_sample_sections(), client=client)


def test_all_blank_key_points_raises_llm_error():
    client = _mock_client_returning({"document_summary": "A valid summary.", "key_points": ["   ", ""]})
    with pytest.raises(LLMError):
        get_document_summary(_sample_sections(), client=client)


def test_blank_key_points_are_filtered_not_fatal_if_others_remain():
    client = _mock_client_returning(
        {"document_summary": "A valid summary.", "key_points": ["  ", "Real point", ""]}
    )
    result = get_document_summary(_sample_sections(), client=client)
    assert result.key_points == ["Real point"]


def test_non_json_response_raises_llm_error():
    client = MagicMock()
    response = MagicMock()
    response.text = "not json"
    client.models.generate_content.return_value = response
    with pytest.raises(LLMError):
        get_document_summary(_sample_sections(), client=client)


def test_api_exception_is_wrapped_as_llm_error():
    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("connection refused")
    with pytest.raises(LLMError):
        get_document_summary(_sample_sections(), client=client)


def test_to_dict_shape():
    mock_response = {"document_summary": "A valid summary.", "key_points": ["Point one", "Point two"]}
    client = _mock_client_returning(mock_response)
    result = get_document_summary(_sample_sections(), client=client)
    assert result.to_dict() == mock_response
