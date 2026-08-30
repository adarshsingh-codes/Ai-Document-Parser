"""
POST /upload — accepts a PDF/DOCX/TXT file, saves it to documents/,
parses it, and returns the extracted text + basic metadata.

This is intentionally the ONLY thing this endpoint does right now.
No topics, no summary, no embeddings yet — that's the whole point of
building phase by phase instead of wiring everything at once.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from backend.parsers.base import ParsingError
from backend.parsers.dispatcher import SUPPORTED_EXTENSIONS, parse_document
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "documents"


@router.post("/upload")
async def upload_document(file: UploadFile):
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
    logger.info("Saved upload: %s (%d bytes)", save_path.name, len(contents))

    try:
        parsed = parse_document(str(save_path))
    except ParsingError as e:
        logger.error("Parsing failed for %s: %s", file.filename, e)
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "filename": parsed.filename,
        "file_type": parsed.file_type,
        "page_count": parsed.page_count,
        "char_count": parsed.char_count,
        "metadata": parsed.metadata,
        "text_preview": parsed.full_text[:500],
        "full_text": parsed.full_text,
    }
