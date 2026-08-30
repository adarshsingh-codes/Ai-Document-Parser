"""
Splits a document's text into chunks small enough to feed an LLM /
embed individually, while carrying metadata (page, position) needed
for citations later in the RAG phase.

Strategy: chunk by paragraphs first (never split mid-sentence if we can
help it), packing paragraphs into a chunk until we hit max_chars, then
starting a new chunk. A small overlap is carried between consecutive
chunks so retrieval doesn't lose context that straddles a chunk boundary.

We deliberately don't tokenize with a real LLM tokenizer here — char
count is a good-enough proxy for phase 2. Swapping in a token-based
length function later (for a specific embedding model) is a one-line change.
"""
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    chunk_index: int
    page_number: int | None = None
    section: str | None = None  # filled in once structure.py exists; None for now
    char_count: int = field(init=False)

    def __post_init__(self):
        self.char_count = len(self.text)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "chunk_index": self.chunk_index,
            "page": self.page_number,
            "section": self.section,
            "char_count": self.char_count,
        }


def _split_into_paragraphs(text: str) -> list[str]:
    """Split on blank lines (the paragraph boundary cleaner.py preserves)."""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def chunk_text(
    text: str,
    max_chars: int = 1000,
    overlap_chars: int = 150,
    page_number: int | None = None,
) -> list[Chunk]:
    """Chunk a single block of text (e.g. one page) into overlapping Chunks.

    Paragraphs are never split mid-sentence unless a single paragraph alone
    exceeds max_chars, in which case it's hard-split as a fallback.
    """
    if not text or not text.strip():
        return []

    paragraphs = _split_into_paragraphs(text)
    if not paragraphs:
        return []

    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_len = 0

    def flush_chunk():
        nonlocal current_parts, current_len
        if not current_parts:
            return
        chunk_text_value = "\n\n".join(current_parts).strip()
        if chunk_text_value:
            chunks.append(
                Chunk(text=chunk_text_value, chunk_index=len(chunks), page_number=page_number)
            )
        current_parts = []
        current_len = 0

    for paragraph in paragraphs:
        # A single paragraph longer than max_chars: hard-split it on its own.
        if len(paragraph) > max_chars:
            flush_chunk()
            for start in range(0, len(paragraph), max_chars - overlap_chars):
                piece = paragraph[start:start + max_chars]
                if piece.strip():
                    chunks.append(
                        Chunk(text=piece.strip(), chunk_index=len(chunks), page_number=page_number)
                    )
            continue

        candidate_len = current_len + len(paragraph) + (2 if current_parts else 0)  # +2 for "\n\n"

        if candidate_len > max_chars and current_parts:
            # Flush current chunk, then start the next one with a small overlap:
            # carry the tail of the previous chunk's text forward for context continuity.
            previous_text = "\n\n".join(current_parts)
            flush_chunk()
            overlap_tail = previous_text[-overlap_chars:].strip() if overlap_chars > 0 else ""
            if overlap_tail:
                current_parts = [overlap_tail]
                current_len = len(overlap_tail)

        current_parts.append(paragraph)
        current_len += len(paragraph) + (2 if len(current_parts) > 1 else 0)

    flush_chunk()

    # Re-index in case hard-splits happened out of order relative to flush_chunk's counter.
    for i, c in enumerate(chunks):
        c.chunk_index = i

    return chunks


def chunk_pages(pages: list, max_chars: int = 1000, overlap_chars: int = 150) -> list[Chunk]:
    """Chunk every page of a document, keeping each chunk tagged with its page number.

    `pages` is a list of ParsedPage-like objects (has .page_number and .text).
    """
    all_chunks: list[Chunk] = []
    for page in pages:
        page_chunks = chunk_text(
            page.text, max_chars=max_chars, overlap_chars=overlap_chars, page_number=page.page_number
        )
        all_chunks.extend(page_chunks)

    for i, c in enumerate(all_chunks):
        c.chunk_index = i

    return all_chunks
