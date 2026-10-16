"""
Unit tests for backend/intelligence/topics.py.

All Gemini calls are mocked — these tests never touch the network,
cost money, or require GEMINI_API_KEY. See
backend/tests/manual_test_topics_live.py for a real-API smoke test.
"""
import json
from unittest.mock import MagicMock

import pytest

from backend.intelligence.llm_client import LLMError
from backend.intelligence.topics import get_topics_and_subtopics
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


def test_empty_sections_returns_empty_list_without_calling_llm():
    client = MagicMock()
    result = get_topics_and_subtopics([], client=client)
    assert result == []
    client.models.generate_content.assert_not_called()


def test_happy_path_parses_topics_and_subtopics():
    mock_response = {
        "topics": [
            {
                "title": "Operating Systems Overview",
                "summary": "Introduces OS concepts.",
                "subtopics": [{"title": "Process Management", "summary": "Kernel manages processes."}],
                "source_section_indices": [0, 1],
            }
        ]
    }
    client = _mock_client_returning(mock_response)
    topics = get_topics_and_subtopics(_sample_sections(), client=client)

    assert len(topics) == 1
    assert topics[0].title == "Operating Systems Overview"
    assert topics[0].source_section_indices == [0, 1]
    assert len(topics[0].subtopics) == 1
    assert topics[0].subtopics[0].title == "Process Management"


def test_sends_section_content_to_the_llm():
    mock_response = {"topics": [{"title": "T", "summary": "S", "subtopics": [], "source_section_indices": [0, 1]}]}
    client = _mock_client_returning(mock_response)
    get_topics_and_subtopics(_sample_sections(), client=client)

    call_kwargs = client.models.generate_content.call_args.kwargs
    prompt = call_kwargs["contents"]
    assert "operating systems" in prompt.lower()
    assert "Process Management" in prompt


def test_missing_topics_key_raises_llm_error():
    client = _mock_client_returning({"not_topics": []})
    with pytest.raises(LLMError):
        get_topics_and_subtopics(_sample_sections(), client=client)


def test_topic_missing_title_raises_llm_error():
    bad_response = {"topics": [{"summary": "no title here", "source_section_indices": [0]}]}
    client = _mock_client_returning(bad_response)
    with pytest.raises(LLMError):
        get_topics_and_subtopics(_sample_sections(), client=client)


def test_invalid_section_index_raises_llm_error():
    bad_response = {"topics": [{"title": "T", "source_section_indices": [99]}]}
    client = _mock_client_returning(bad_response)
    with pytest.raises(LLMError):
        get_topics_and_subtopics(_sample_sections(), client=client)


def test_non_json_response_raises_llm_error():
    client = MagicMock()
    response = MagicMock()
    response.text = "this is not json at all"
    client.models.generate_content.return_value = response

    with pytest.raises(LLMError):
        get_topics_and_subtopics(_sample_sections(), client=client)


def test_api_exception_is_wrapped_as_llm_error():
    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("connection refused")
    with pytest.raises(LLMError):
        get_topics_and_subtopics(_sample_sections(), client=client)


def test_unassigned_section_raises_llm_error():
    # Only section 0 is assigned; section 1 is left out entirely — this must
    # now raise rather than silently proceed, since every section needs
    # exactly one owning topic for citations to stay unambiguous.
    mock_response = {"topics": [{"title": "T", "summary": "S", "subtopics": [], "source_section_indices": [0]}]}
    client = _mock_client_returning(mock_response)
    with pytest.raises(LLMError):
        get_topics_and_subtopics(_sample_sections(), client=client)


def test_duplicate_section_index_across_topics_raises_llm_error():
    # Section 0 assigned to two different topics — ambiguous ownership,
    # must be rejected rather than silently accepted.
    mock_response = {
        "topics": [
            {"title": "Topic A", "summary": "S", "subtopics": [], "source_section_indices": [0]},
            {"title": "Topic B", "summary": "S", "subtopics": [], "source_section_indices": [0, 1]},
        ]
    }
    client = _mock_client_returning(mock_response)
    with pytest.raises(LLMError):
        get_topics_and_subtopics(_sample_sections(), client=client)


def test_duplicate_section_index_within_same_topic_raises_llm_error():
    mock_response = {
        "topics": [{"title": "T", "summary": "S", "subtopics": [], "source_section_indices": [0, 0, 1]}]
    }
    client = _mock_client_returning(mock_response)
    with pytest.raises(LLMError):
        get_topics_and_subtopics(_sample_sections(), client=client)


def test_topic_to_dict_shape():
    mock_response = {
        "topics": [
            {
                "title": "T",
                "summary": "S",
                "subtopics": [{"title": "ST", "summary": "SS"}],
                "source_section_indices": [0, 1],
            }
        ]
    }
    client = _mock_client_returning(mock_response)
    topics = get_topics_and_subtopics(_sample_sections(), client=client)
    d = topics[0].to_dict()
    assert d == {
        "title": "T",
        "summary": "S",
        "subtopics": [{"title": "ST", "summary": "SS"}],
        "source_section_indices": [0, 1],
    }
