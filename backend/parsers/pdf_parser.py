"""
Extracts text from PDF files, page by page, using pdfplumber.

pdfplumber over PyPDF2: better text-extraction accuracy on real-world
PDFs (multi-column layouts, tables), at the cost of being a bit slower.
For a document-intelligence tool, accuracy matters more than raw speed.
"""
from backend.parsers.base import ParsedDocument, ParsedPage, ParsingError, validate_file_exists
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def parse_pdf(file_path: str) -> ParsedDocument:
    path = validate_file_exists(file_path)

    try:
        import pdfplumber
    except ImportError as e:
        raise ParsingError(
            "pdfplumber is not installed. Run: pip install pdfplumber"
        ) from e

    pages: list[ParsedPage] = []

    try:
        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) == 0:
                raise ParsingError(f"PDF has no pages: {file_path}")

            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages.append(ParsedPage(page_number=i, text=text.strip()))
    except ParsingError:
        raise
    except Exception as e:
        # pdfplumber raises many different underlying exceptions
        # (pdfminer errors, PDFSyntaxError, etc.) for a corrupt/encrypted file.
        raise ParsingError(f"Failed to parse PDF '{path.name}': {e}") from e

    full_text = "\n\n".join(p.text for p in pages if p.text)

    if not full_text.strip():
        logger.warning(
            "No extractable text found in %s — it may be a scanned/image-only PDF "
            "that needs OCR (not yet supported).",
            path.name,
        )

    return ParsedDocument(
        filename=path.name,
        file_type="pdf",
        full_text=full_text,
        pages=pages,
        metadata={"page_count": len(pages)},
    )
