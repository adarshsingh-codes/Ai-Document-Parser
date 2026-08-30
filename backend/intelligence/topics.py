"""
AI-enhanced topic/subtopic extraction.

Design decision (confirmed with user before building): this does NOT
replace backend.processing.structure — the deterministic heading tree
stays the ground truth for page/section boundaries. This module takes
that tree (+ the cleaned chunk text) and asks the LLM to produce
semantic topic/subtopic labels and summaries, each linked back to the
structure.py section index it came from via source_section_indices.
That linkage is what lets citations later say "this topic came from
page 7" without the LLM ever needing to know about pages itself.

Expected output shape (confirmed with user before building):
{
  "topics": [
    {
      "title": "...",
      "summary": "...",
      "subtopics": [{"title": "...", "summary": "..."}],
      "source_section_indices": [0, 1]
    }
  ]
}
"""
from dataclasses import dataclass, field

from backend.intelligence.llm_client import DEFAULT_MODEL, LLMError, call_json_completion, get_client
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a document analysis assistant. You will be given a \
document's cleaned text, already split into top-level sections (each with an \
index, a title, and content). Your job is to identify the main topics and \
subtopics actually discussed, using the existing sections as your primary \
signal — merge sections that clearly cover the same topic, and split a \
section into multiple topics only if it obviously covers unrelated things.

Respond with ONLY a JSON object in this exact shape, no other text:
{
  "topics": [
    {
      "title": "short topic title",
      "summary": "one sentence describing this topic",
      "subtopics": [
        {"title": "short subtopic title", "summary": "one sentence"}
      ],
      "source_section_indices": [0, 1]
    }
  ]
}

Rules:
- "source_section_indices" must reference the 0-based indices of the input sections given to you.
- Every input section index must appear in exactly one topic's source_section_indices — not zero, not more than one.
- subtopics can be an empty list if a topic has no clear subdivisions.
- Keep titles under 8 words. Keep summaries to one sentence.
- If the document has only one section with no real internal structure, return a single topic."""


@dataclass
class Subtopic:
    title: str
    summary: str = ""


@dataclass
class Topic:
    title: str
    summary: str = ""
    subtopics: list[Subtopic] = field(default_factory=list)
    source_section_indices: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "summary": self.summary,
            "subtopics": [{"title": s.title, "summary": s.summary} for s in self.subtopics],
            "source_section_indices": self.source_section_indices,
        }


def _build_user_prompt(sections: list) -> str:
    """sections: list of backend.processing.structure.Section objects."""
    lines = ["Sections:"]
    for i, section in enumerate(sections):
        content_preview = section.content[:1000]  # cap per-section length sent to the LLM
        lines.append(f"\n[Section {i}] Title: {section.title}\nContent: {content_preview}")
    return "\n".join(lines)


def _validate_and_parse(raw: dict, num_sections: int) -> list[Topic]:
    if "topics" not in raw or not isinstance(raw["topics"], list):
        raise LLMError(f"LLM response missing 'topics' list: {raw}")

    topics: list[Topic] = []
    seen_indices: set[int] = set()

    for item in raw["topics"]:
        if "title" not in item:
            raise LLMError(f"Topic missing 'title': {item}")

        indices = item.get("source_section_indices", [])
        if not isinstance(indices, list):
            raise LLMError(f"'source_section_indices' must be a list: {item}")
        for idx in indices:
            if not isinstance(idx, int) or idx < 0 or idx >= num_sections:
                raise LLMError(f"Invalid section index {idx} (document has {num_sections} sections)")
            if idx in seen_indices:
                raise LLMError(
                    f"Section index {idx} was assigned to more than one topic — "
                    "each section must map to exactly one topic for citations to stay unambiguous."
                )
            seen_indices.add(idx)

        subtopics = [
            Subtopic(title=st.get("title", ""), summary=st.get("summary", ""))
            for st in item.get("subtopics", [])
        ]

        topics.append(
            Topic(
                title=item["title"],
                summary=item.get("summary", ""),
                subtopics=subtopics,
                source_section_indices=indices,
            )

        )

    missing = set(range(num_sections)) - seen_indices
    if missing:
        raise LLMError(
            f"LLM left {len(missing)} section(s) unassigned to any topic: {sorted(missing)}. "
            "Every input section must be covered by exactly one topic."
        )

    return topics


def get_topics_and_subtopics(sections: list, client=None, model: str = DEFAULT_MODEL) -> list[Topic]:
    """Extract semantic topics/subtopics from a document's structure tree.

    `sections` is the flat top-level list returned by
    backend.processing.structure.detect_structure(). `client` is
    injectable for tests (pass a mock with chat.completions.create);
    defaults to a real OpenAI client reading OPENAI_API_KEY from env.
    """
    if not sections:
        return []

    if client is None:
        client = get_client()

    user_prompt = _build_user_prompt(sections)
    raw = call_json_completion(client, _SYSTEM_PROMPT, user_prompt, model=model)
    return _validate_and_parse(raw, num_sections=len(sections))
