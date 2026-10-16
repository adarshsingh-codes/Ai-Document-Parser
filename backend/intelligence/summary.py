"""
AI-generated document-level summary.

Distinct from Topic.summary (topics.py) which is a one-sentence gist per
topic — this module produces a whole-document overview plus a short list
of key points, meant to sit at the top of a document's analysis view
(the kind of thing you'd read before deciding whether to open the doc
at all). Takes the same structure.py sections as topics.py for input
consistency, but summarizes across all of them at once rather than
per-section.

Expected output shape:
{
  "document_summary": "2-4 sentence overview of the whole document",
  "key_points": ["point 1", "point 2", "point 3"]
}
"""
from dataclasses import dataclass, field

from backend.intelligence.llm_client import DEFAULT_MODEL, LLMError, call_json_completion, get_client
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a document analysis assistant. You will be given a \
document's cleaned text, split into top-level sections (title + content). \
Your job is to produce a concise overview of the ENTIRE document — not a \
per-section summary — plus a short list of the most important key points.

Respond with ONLY a JSON object in this exact shape, no other text:
{
  "document_summary": "2 to 4 sentences summarizing the whole document",
  "key_points": ["short point 1", "short point 2", "short point 3"]
}

Rules:
- "document_summary" must be 2 to 4 sentences, written in your own words (never copy sentences verbatim from the input).
- "key_points" must contain between 2 and 6 short bullet-style points, each a single sentence or short phrase.
- Focus on what someone deciding whether to read the full document would want to know first.
- Do not repeat the document's title verbatim as a key point."""


@dataclass
class DocumentSummary:
    document_summary: str
    key_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"document_summary": self.document_summary, "key_points": self.key_points}


def _build_user_prompt(sections: list) -> str:
    """sections: list of backend.processing.structure.Section objects."""
    lines = ["Document sections:"]
    for i, section in enumerate(sections):
        content_preview = section.content[:1500]  # cap per-section length sent to the LLM
        lines.append(f"\n[Section {i}] Title: {section.title}\nContent: {content_preview}")
    return "\n".join(lines)


def _validate_and_parse(raw: dict) -> DocumentSummary:
    if "document_summary" not in raw or not isinstance(raw["document_summary"], str):
        raise LLMError(f"LLM response missing string 'document_summary': {raw}")

    summary_text = raw["document_summary"].strip()
    if not summary_text:
        raise LLMError("LLM returned an empty 'document_summary'.")

    key_points = raw.get("key_points", [])
    if not isinstance(key_points, list) or not all(isinstance(p, str) for p in key_points):
        raise LLMError(f"'key_points' must be a list of strings: {raw}")

    key_points = [p.strip() for p in key_points if p.strip()]
    if not key_points:
        raise LLMError("LLM returned no usable 'key_points'.")

    return DocumentSummary(document_summary=summary_text, key_points=key_points)


def get_document_summary(sections: list, client=None, model: str = DEFAULT_MODEL) -> DocumentSummary:
    """Generate a whole-document summary + key points from structure.py sections.

    `client` is injectable for tests (pass a mock with chat.completions.create);
    defaults to a real OpenAI client reading OPENAI_API_KEY from env.
    Raises LLMError if there's nothing to summarize (empty sections) or the
    LLM response doesn't validate.
    """
    if not sections:
        raise LLMError("Cannot summarize a document with no sections.")

    if client is None:
        client = get_client()

    user_prompt = _build_user_prompt(sections)
    raw = call_json_completion(client, _SYSTEM_PROMPT, user_prompt, model=model)
    return _validate_and_parse(raw)
