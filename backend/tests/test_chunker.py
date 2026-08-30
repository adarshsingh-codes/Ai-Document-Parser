from backend.parsers.base import ParsedPage
from backend.processing.chunker import chunk_pages, chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_returns_single_chunk():
    text = "This is a short paragraph that fits easily in one chunk."
    chunks = chunk_text(text, max_chars=1000)
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].chunk_index == 0


def test_never_splits_a_paragraph_that_fits():
    # Two paragraphs that together exceed max_chars should split into two
    # chunks along the paragraph boundary, not mid-sentence.
    p1 = "A" * 400
    p2 = "B" * 400
    text = f"{p1}\n\n{p2}"
    chunks = chunk_text(text, max_chars=500, overlap_chars=0)
    assert len(chunks) == 2
    assert chunks[0].text == p1
    assert chunks[1].text == p2


def test_chunks_carry_incrementing_index():
    p1, p2, p3 = "A" * 400, "B" * 400, "C" * 400
    text = f"{p1}\n\n{p2}\n\n{p3}"
    chunks = chunk_text(text, max_chars=500, overlap_chars=0)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_overlap_carries_context_between_chunks():
    p1 = "A" * 400
    p2 = "B" * 400
    text = f"{p1}\n\n{p2}"
    chunks = chunk_text(text, max_chars=500, overlap_chars=50)
    assert len(chunks) == 2
    # Second chunk should start with the tail of the first chunk's content.
    assert chunks[1].text.startswith("A" * 50)
    assert "B" * 400 in chunks[1].text


def test_oversized_single_paragraph_is_hard_split():
    huge_paragraph = "X" * 3000
    chunks = chunk_text(huge_paragraph, max_chars=1000, overlap_chars=100)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 1000


def test_page_number_is_attached_to_chunks():
    chunks = chunk_text("Some content here.", max_chars=1000, page_number=7)
    assert chunks[0].page_number == 7


def test_chunk_to_dict_shape():
    chunks = chunk_text("Some content here.", page_number=3)
    d = chunks[0].to_dict()
    assert set(d.keys()) == {"text", "chunk_index", "page", "section", "char_count"}
    assert d["page"] == 3
    assert d["section"] is None
    assert d["char_count"] == len("Some content here.")


def test_chunk_pages_tags_each_chunk_with_correct_page_and_global_index():
    pages = [
        ParsedPage(page_number=1, text="Page one content, fairly short."),
        ParsedPage(page_number=2, text="Page two content, also short."),
    ]
    chunks = chunk_pages(pages, max_chars=1000)
    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2
    # Global chunk_index should be sequential across pages, not reset per page.
    assert [c.chunk_index for c in chunks] == [0, 1]


def test_chunk_pages_skips_blank_pages():
    pages = [
        ParsedPage(page_number=1, text="Real content on page one."),
        ParsedPage(page_number=2, text="   "),  # blank page
        ParsedPage(page_number=3, text="Real content on page three."),
    ]
    chunks = chunk_pages(pages, max_chars=1000)
    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 3
