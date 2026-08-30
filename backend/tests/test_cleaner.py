from backend.processing.cleaner import clean_text, is_empty_after_cleaning


def test_collapses_excess_blank_lines():
    raw = "Operating Systems\n\n\n\n   Process Management\n\n\n\nProcess   scheduling   is..."
    result = clean_text(raw)
    assert result == "Operating Systems\n\nProcess Management\n\nProcess scheduling is..."


def test_collapses_multiple_spaces():
    assert clean_text("Process   scheduling    is   fair.") == "Process scheduling is fair."


def test_strips_trailing_and_leading_whitespace_per_line():
    raw = "  Heading   \n   Body text   \n"
    assert clean_text(raw) == "Heading\nBody text"


def test_fixes_space_before_punctuation():
    assert clean_text("This is a sentence .") == "This is a sentence."
    assert clean_text("Wait , what ?") == "Wait, what?"


def test_normalizes_windows_and_mac_line_endings():
    assert clean_text("Line one\r\nLine two\rLine three") == "Line one\nLine two\nLine three"


def test_empty_string_returns_empty():
    assert clean_text("") == ""


def test_whitespace_only_string_returns_empty():
    assert clean_text("   \n\n   \t  ") == ""


def test_is_empty_after_cleaning():
    assert is_empty_after_cleaning("   \n\n  ") is True
    assert is_empty_after_cleaning("actual content") is False


def test_idempotent_on_already_clean_text():
    clean = "Operating Systems\n\nProcess Management\n\nProcess scheduling is fair."
    assert clean_text(clean) == clean


def test_preserves_single_paragraph_breaks():
    # Exactly one blank line between paragraphs should be preserved, not collapsed away.
    raw = "Paragraph one.\n\nParagraph two."
    assert clean_text(raw) == "Paragraph one.\n\nParagraph two."
