"""
POST /analyze — parses a file (like /upload) but also runs it through
the full Phase 2 processing pipeline: clean -> chunk -> detect structure.

Kept as a separate endpoint from /upload rather than folding into it,
so /upload stays a pure "give me the raw extracted text" endpoint and
this one is explicitly "give me the processed/structured view."
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from backend.parsers.base import ParsingError
from backend.parsers.dispatcher import SUPPORTED_EXTENSIONS, parse_document
from backend.processing.chunker import chunk_pages
from backend.processing.cleaner import clean_pages
from backend.processing.structure import detect_structure
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "documents"


@router.post("/analyze")
async def analyze_document(file: UploadFile):
    extension = Path(file.filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. "
                   f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    DOCUMENTS_DIR.mkdir(exist_ok=True)
    save_path = DOCUMENTS_DIR / file.filename
    contents = await file.read()
    save_path.write_bytes(contents)

    try:
        parsed = parse_document(str(save_path))
    except ParsingError as e:
        logger.error("Parsing failed for %s: %s", file.filename, e)
        raise HTTPException(status_code=422, detail=str(e))

    cleaned_pages = clean_pages(parsed.pages)
    chunks = chunk_pages(cleaned_pages, max_chars=800, overlap_chars=100)
    cleaned_full_text = "\n\n".join(p.text for p in cleaned_pages if p.text)
    sections = detect_structure(cleaned_full_text)

    logger.info(
        "Analyzed %s: %d pages, %d chunks, %d top-level sections",
        parsed.filename, parsed.page_count, len(chunks), len(sections),
    )

    return {
        "filename": parsed.filename,
        "file_type": parsed.file_type,
        "page_count": parsed.page_count,
        "chunk_count": len(chunks),
        "chunks": [c.to_dict() for c in chunks],
        "structure": [s.to_dict() for s in sections],
    }
