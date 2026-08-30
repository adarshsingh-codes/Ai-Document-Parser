"""
Reads plain .txt files. The only real complexity here is encoding —
not every .txt file is UTF-8, so we try a few common encodings before
giving up, instead of crashing on the first weird file a user uploads.
"""
from backend.parsers.base import ParsedDocument, ParsedPage, ParsingError, validate_file_exists
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_ENCODINGS_TO_TRY = ("utf-8", "utf-8-sig", "latin-1", "cp1252")


def parse_txt(file_path: str) -> ParsedDocument:
    path = validate_file_exists(file_path)

    raw_bytes = path.read_bytes()
    text = None
    used_encoding = None

    for encoding in _ENCODINGS_TO_TRY:
        try:
            text = raw_bytes.decode(encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise ParsingError(
            f"Could not decode '{path.name}' with any of {_ENCODINGS_TO_TRY}. "
            "The file may be corrupt or not actually a text file."
        )

    if used_encoding != "utf-8":
        logger.info("Decoded %s using fallback encoding '%s'.", path.name, used_encoding)

    return ParsedDocument(
        filename=path.name,
        file_type="txt",
        full_text=text.strip(),
        pages=[ParsedPage(page_number=1, text=text.strip())],
        metadata={"encoding": used_encoding},
    )
