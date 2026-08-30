"""
Light-touch text normalization for freshly-parsed documents.

Deliberately conservative: we're fixing extraction artifacts (excess
whitespace, repeated blank lines, stray spaces before punctuation),
NOT rewriting or paraphrasing content. RAG and citations later depend
on the text staying faithful to the original — over-cleaning here
would quietly corrupt everything downstream.
"""
import re

# 3+ blank lines -> collapse to exactly one blank line (i.e. one \n\n\n\n... -> \n\n)
_MULTI_BLANK_LINES = re.compile(r"\n\s*\n\s*(\n\s*)+")

# 2+ regular spaces/tabs (not newlines) -> single space
_MULTI_SPACE = re.compile(r"[ \t]{2,}")

# Trailing whitespace at the end of a line
_TRAILING_WHITESPACE = re.compile(r"[ \t]+(?=\n)")

# A space immediately before punctuation like ".", ",", ":", ";", "!", "?"
_SPACE_BEFORE_PUNCTUATION = re.compile(r"[ \t]+([.,;:!?])")


def clean_text(text: str) -> str:
    """Normalize whitespace in extracted text without touching wording.

    Safe to call on already-clean text (idempotent) and on empty strings.
    """
    if not text:
        return ""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip trailing spaces/tabs on each line before collapsing blank lines,
    # so a line of only whitespace is treated as a true blank line.
    cleaned = _TRAILING_WHITESPACE.sub("", cleaned)

    # Collapse runs of 3+ newlines (with only whitespace between them) into
    # a single blank line (\n\n) — preserves paragraph breaks, removes excess.
    cleaned = _MULTI_BLANK_LINES.sub("\n\n", cleaned)

    # Collapse repeated spaces/tabs within a line.
    cleaned = _MULTI_SPACE.sub(" ", cleaned)

    # Fix stray space before punctuation, e.g. "scheduling is ." -> "scheduling is."
    cleaned = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", cleaned)

    # Strip leading/trailing blank lines and spaces on each individual line.
    lines = [line.strip(" \t") for line in cleaned.split("\n")]
    cleaned = "\n".join(lines)

    return cleaned.strip()


def clean_pages(pages: list) -> list:
    """Apply clean_text to each ParsedPage's .text, returning new page-like dicts.

    Kept generic (works on ParsedPage objects with .page_number/.text) so it
    doesn't need to import backend.parsers.base and create a circular import.
    """
    cleaned_pages = []
    for page in pages:
        cleaned_pages.append(
            type(page)(page_number=page.page_number, text=clean_text(page.text))
        )
    return cleaned_pages


def is_empty_after_cleaning(text: str) -> bool:
    """True if there's no real content left after cleaning (e.g. a blank page)."""
    return len(clean_text(text)) == 0
