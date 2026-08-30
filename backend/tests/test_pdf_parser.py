"""
Unit tests for backend/parsers/pdf_parser.py.

We generate real PDF fixtures on the fly with reportlab instead of
committing binary .pdf files to the repo — keeps the repo clean and
the tests self-contained. reportlab is a test-only dependency.
"""
import tempfile
from pathlib import Path

import pytest

from backend.parsers.base import ParsingError
from backend.parsers.pdf_parser import parse_pdf


def _make_pdf(pages_text: list[str]) -> str:
    """Build a real multi-page PDF and return its path."""
    from reportlab.pdfgen import canvas

    import os
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    c = canvas.Canvas(path)
    for text in pages_text:
        c.drawString(72, 700, text)
        c.showPage()
    c.save()
    return path


def test_parse_pdf_single_page():
    path = _make_pdf(["Hello from page one."])
    try:
        result = parse_pdf(path)
        assert result.file_type == "pdf"
        assert result.page_count == 1
        assert "Hello from page one" in result.full_text
    finally:
        Path(path).unlink()


def test_parse_pdf_multi_page():
    path = _make_pdf(["First page content.", "Second page content.", "Third page content."])
    try:
        result = parse_pdf(path)
        assert result.page_count == 3
        assert "First page content" in result.full_text
        assert "Second page content" in result.full_text
        assert "Third page content" in result.full_text
        # Confirm page objects line up individually, not just concatenated full_text.
        assert result.pages[0].page_number == 1
        assert "First page" in result.pages[0].text
        assert result.pages[2].page_number == 3
        assert "Third page" in result.pages[2].text
    finally:
        Path(path).unlink()


def test_parse_pdf_missing_file_raises():
    with pytest.raises(ParsingError):
        parse_pdf("/tmp/does_not_exist_ai_doc_parser.pdf")


def test_parse_pdf_empty_file_raises():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = f.name  # zero bytes, not a real PDF at all

    try:
        with pytest.raises(ParsingError):
            parse_pdf(path)
    finally:
        Path(path).unlink()


def test_parse_pdf_corrupt_file_raises():
    # Real bytes, but not a valid PDF structure — should hit our except-and-wrap branch.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"this is not a real pdf file, just plain garbage bytes")
        path = f.name

    try:
        with pytest.raises(ParsingError):
            parse_pdf(path)
    finally:
        Path(path).unlink()
