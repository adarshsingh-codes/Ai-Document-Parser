"""
Extracts text from Word (.docx) files using python-docx.

DOCX has no real concept of "pages" (page breaks are a rendering detail,
not stored positions), so we treat each paragraph as a unit and don't
try to fake page numbers. We still wrap it in ParsedPage(page_number=1)
so the shape matches PDF/TXT for downstream code.
"""
from backend.parsers.base import ParsedDocument, ParsedPage, ParsingError, validate_file_exists
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def parse_docx(file_path: str) -> ParsedDocument:
    path = validate_file_exists(file_path)

    try:
        import docx
    except ImportError as e:
        raise ParsingError(
            "python-docx is not installed. Run: pip install python-docx"
        ) from e

    try:
        document = docx.Document(str(path))
    except Exception as e:
        raise ParsingError(f"Failed to parse DOCX '{path.name}': {e}") from e

    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]

    # Also pull text out of tables — plain `document.paragraphs` skips table content entirely.
    table_text = []
    for table in document.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                table_text.append(row_text)

    full_text = "\n\n".join(paragraphs)
    if table_text:
        full_text += "\n\n[Tables]\n" + "\n".join(table_text)

    if not full_text.strip():
        logger.warning("No extractable text found in %s (empty document?).", path.name)

    return ParsedDocument(
        filename=path.name,
        file_type="docx",
        full_text=full_text,
        pages=[ParsedPage(page_number=1, text=full_text)],
        metadata={"paragraph_count": len(paragraphs), "table_count": len(document.tables)},
    )
