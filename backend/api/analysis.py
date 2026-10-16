"""
POST /analyze — parses a file (like /upload), then runs the full
intelligence pipeline on it: clean -> detect structure -> extract
keywords (per page + per section) -> AI topics/subtopics + summary.

The deterministic half (parsing, cleaning, structure, keywords) never
depends on the Gemini API and always runs. The AI half (topics + summary)
is best-effort: if it fails for any reason (missing GEMINI_API_KEY, quota,
network), the endpoint still returns 200 with the deterministic results
plus ai_available=False and an ai_error message, rather than failing the
whole request over an optional enhancement.
"""
import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.intelligence.keywords import extract_keywords
from backend.intelligence.llm_client import LLMError
from backend.intelligence.summary import get_document_summary
from backend.intelligence.topics import Topic, get_topics_and_subtopics
from backend.parsers.base import ParsingError
from backend.parsers.dispatcher import SUPPORTED_EXTENSIONS, parse_document
from backend.processing.cleaner import clean_pages
from backend.processing.structure import Section, detect_structure
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

DOCUMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "documents"

_MAX_KEYWORDS_PER_PAGE = 8
_MAX_KEYWORDS_PER_SECTION = 8
_MAX_KEYWORDS_PER_TOPIC = 10

# Observed in testing: Gemini call latency is highly variable (seconds to
# multiple minutes under high API demand or once a rate limit kicks in),
# and neither the SDK call nor asyncio.gather bounds that on their own. A
# hard ceiling here is what actually makes "graceful degradation" graceful
# for the person waiting on the request, instead of degrading correctly
# but only after several minutes.
_AI_LAYER_TIMEOUT_SECONDS = 45


def _section_to_dict_with_keywords(section: Section) -> dict:
    return {
        "title": section.title,
        "level": section.level,
        "content": section.content,
        "keywords": [k.to_dict() for k in extract_keywords(section.content, _MAX_KEYWORDS_PER_SECTION)],
        "children": [_section_to_dict_with_keywords(child) for child in section.children],
    }


def _topic_to_dict_with_keywords(topic: Topic, sections: list[Section]) -> dict:
    topic_text = "\n\n".join(sections[i].content for i in topic.source_section_indices)
    return {
        "title": topic.title,
        "summary": topic.summary,
        "keywords": [k.to_dict() for k in extract_keywords(topic_text, _MAX_KEYWORDS_PER_TOPIC)],
        "source_section_indices": topic.source_section_indices,
        "subtopics": [
            {
                "title": subtopic.title,
                "summary": subtopic.summary,
                "keywords": [
                    k.to_dict()
                    for k in extract_keywords(f"{subtopic.title}. {subtopic.summary}", _MAX_KEYWORDS_PER_TOPIC)
                ],
            }
            for subtopic in topic.subtopics
        ],
    }


async def _run_ai_layer(sections: list[Section]):
    """Run topic/subtopic extraction and document summarization concurrently
    (both are blocking Gemini calls, so each goes on its own thread), bounded
    by _AI_LAYER_TIMEOUT_SECONDS so a slow Gemini response degrades promptly
    instead of leaving the request hanging."""
    return await asyncio.wait_for(
        asyncio.gather(
            run_in_threadpool(get_topics_and_subtopics, sections),
            run_in_threadpool(get_document_summary, sections),
        ),
        timeout=_AI_LAYER_TIMEOUT_SECONDS,
    )


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
    cleaned_full_text = "\n\n".join(p.text for p in cleaned_pages if p.text)
    sections = detect_structure(cleaned_full_text)

    pages = [
        {
            "page_number": page.page_number,
            "keywords": [k.to_dict() for k in extract_keywords(page.text, _MAX_KEYWORDS_PER_PAGE)],
        }
        for page in cleaned_pages
    ]
    sections_out = [_section_to_dict_with_keywords(s) for s in sections]

    ai_available = True
    ai_error = None
    topics: list[Topic] = []
    summary = None

    try:
        topics, summary = await _run_ai_layer(sections)
    except LLMError as e:
        logger.warning("AI layer unavailable for %s: %s", parsed.filename, e)
        ai_available = False
        ai_error = str(e)
    except asyncio.TimeoutError:
        logger.warning(
            "AI layer timed out after %ss for %s", _AI_LAYER_TIMEOUT_SECONDS, parsed.filename
        )
        ai_available = False
        ai_error = f"AI analysis timed out after {_AI_LAYER_TIMEOUT_SECONDS}s (Gemini API is responding slowly)."

    topics_out = [_topic_to_dict_with_keywords(t, sections) for t in topics]

    logger.info(
        "Analyzed %s: %d pages, %d top-level sections, %d topics (ai_available=%s)",
        parsed.filename, parsed.page_count, len(sections), len(topics_out), ai_available,
    )

    return {
        "filename": parsed.filename,
        "file_type": parsed.file_type,
        "page_count": parsed.page_count,
        "ai_available": ai_available,
        "ai_error": ai_error,
        "summary": summary.to_dict() if summary else None,
        "topics": topics_out,
        "sections": sections_out,
        "pages": pages,
    }
