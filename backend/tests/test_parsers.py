"""
Quick sanity tests for Phase 1 (parsers). Run with:
    python -m pytest backend/tests/test_parsers.py -v

from the AI-Document-Parser/ root.
"""
import tempfile
from pathlib import Path

import pytest

from backend.parsers.base import ParsingError
from backend.parsers.dispatcher import parse_document
from backend.parsers.txt_parser import parse_txt


def test_parse_txt_basic():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello world.\nThis is a test document.")
        path = f.name

    result = parse_txt(path)
    assert result.file_type == "txt"
    assert "Hello world" in result.full_text
    assert result.page_count == 1

    Path(path).unlink()


def test_parse_txt_empty_file_raises():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        path = f.name  # empty file, nothing written

    with pytest.raises(ParsingError):
        parse_txt(path)

    Path(path).unlink()


def test_dispatcher_unsupported_extension():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
        f.write("data")
        path = f.name

    with pytest.raises(ParsingError):
        parse_document(path)

    Path(path).unlink()


def test_dispatcher_missing_file():
    with pytest.raises(ParsingError):
        parse_document("/tmp/this_file_does_not_exist_12345.txt")
