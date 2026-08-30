"""
Single entry point for parsing any supported file: parse_document(path).
This is the only function the rest of the app should ever call directly —
it hides which specific parser module handled the file.
"""
from pathlib import Path

from backend.parsers.base import ParsedDocument, ParsingError
from backend.parsers.docx_parser import parse_docx
from backend.parsers.pdf_parser import parse_pdf
from backend.parsers.txt_parser import parse_txt

_PARSERS_BY_EXTENSION = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".txt": parse_txt,
}

SUPPORTED_EXTENSIONS = tuple(_PARSERS_BY_EXTENSION.keys())


def parse_document(file_path: str) -> ParsedDocument:
    extension = Path(file_path).suffix.lower()

    parser_fn = _PARSERS_BY_EXTENSION.get(extension)
    if parser_fn is None:
        raise ParsingError(
            f"Unsupported file type '{extension}'. "
            f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    return parser_fn(file_path)
