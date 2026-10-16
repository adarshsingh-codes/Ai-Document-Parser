"""
Unit tests for backend/intelligence/keywords.py.

Pure function, no network/mocking needed — RAKE is deterministic given
the same input text.
"""
from backend.intelligence.keywords import extract_keywords


def test_empty_text_returns_empty_list():
    assert extract_keywords("") == []
    assert extract_keywords("   \n  ") == []


def test_stopword_only_text_returns_empty_list():
    assert extract_keywords("the and of a is to") == []


def test_extracts_multi_word_phrase_over_split_words():
    text = "Linear regression is a supervised machine learning algorithm."
    keywords = extract_keywords(text)
    phrases = [k.phrase for k in keywords]
    assert "linear regression" in phrases
    assert "supervised machine learning algorithm" in phrases


def test_results_sorted_by_score_descending():
    text = (
        "Operating systems manage processes and memory. "
        "Process scheduling is a core operating systems responsibility. "
        "Memory management works alongside process scheduling."
    )
    keywords = extract_keywords(text)
    scores = [k.score for k in keywords]
    assert scores == sorted(scores, reverse=True)


def test_max_keywords_caps_result_length():
    text = (
        "Apples oranges bananas grapes mangoes kiwis pears plums cherries "
        "peaches apricots figs dates melons berries."
    )
    keywords = extract_keywords(text, max_keywords=3)
    assert len(keywords) == 3


def test_to_dict_shape():
    keywords = extract_keywords("Natural language processing is fascinating.")
    d = keywords[0].to_dict()
    assert set(d.keys()) == {"phrase", "score"}
    assert isinstance(d["phrase"], str)
    assert isinstance(d["score"], float)


def test_repeated_phrase_counted_once():
    text = "Neural networks are powerful. Neural networks learn from data."
    keywords = extract_keywords(text)
    phrases = [k.phrase for k in keywords]
    assert phrases.count("neural networks") == 1
