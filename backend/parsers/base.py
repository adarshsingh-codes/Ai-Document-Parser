"""
Common contract for every parser (PDF, DOCX, TXT, ...).

Every parser takes a file path and returns a ParsedDocument. Nothing
downstream (processing/, intelligence/, etc.) should ever need to know
which file type the text originally came from — that's the whole point
of standardizing on this shape now, before more parsers get added.
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedPage:
    """One page/slide/section of raw extracted text, 1-indexed."""
    page_number: int
    text: str


@dataclass
class ParsedDocument:
    """Result of parsing any supported file type."""
    filename: str
    file_type: str          # "pdf" | "docx" | "txt"
    full_text: str           # all pages/paragraphs joined together
    pages: list[ParsedPage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def page_count(self) -> int:
        return len(self.pages) or 1

    @property
    def char_count(self) -> int:
        return len(self.full_text)


class ParsingError(Exception):
    """Raised when a file can't be read or parsed (corrupt, wrong extension, etc.)."""
    pass


def validate_file_exists(file_path: str) -> Path:
    path = Path(file_path)
    if not path.exists():
        raise ParsingError(f"File not found: {file_path}")
    if path.stat().st_size == 0:
        raise ParsingError(f"File is empty: {file_path}")
    return path
