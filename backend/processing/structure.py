"""
Deterministic structure detection: builds a topic -> subtopic tree from
heading-like lines, using heuristics only (no LLM calls yet — that's
Phase 3's job to *enhance* this, not replace it).

Heuristics for "this line is a heading":
  - Short (<= HEADING_MAX_WORDS words) and doesn't end in sentence punctuation
  - Title Case or ALL CAPS
  - Numbered headings like "1.", "1.1", "Chapter 2", "Section 3:"

Two heading levels are supported for now (topic / subtopic), based on
numbering depth (e.g. "1." = topic, "1.1" = subtopic) or, lacking
numbers, ALL CAPS = topic and Title Case = subtopic. This is intentionally
simple; Phase 3's AI layer can later re-rank or relabel these once an
LLM is in the loop, but every document should get *some* structure
without needing one.
"""
import re
from dataclasses import dataclass, field

_HEADING_MAX_WORDS = 10

_NUMBERED_HEADING = re.compile(r"^(\d+(\.\d+)*)[.\)]?\s+(.*)")
_CHAPTER_OR_SECTION = re.compile(r"^(Chapter|Section|Part)\s+\d+[:\.]?\s*(.*)", re.IGNORECASE)
_SENTENCE_ENDING_PUNCTUATION = (".", ",", ";")  # a heading ending in these is unlikely


@dataclass
class Section:
    title: str
    level: int  # 1 = topic, 2 = subtopic
    content: str = ""
    children: list["Section"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "level": self.level,
            "content": self.content,
            "children": [c.to_dict() for c in self.children],
        }


def _looks_like_heading(line: str) -> tuple[bool, int]:
    """Return (is_heading, level) — level 1 = topic, level 2 = subtopic."""
    stripped = line.strip()
    if not stripped:
        return False, 0

    if stripped.endswith(_SENTENCE_ENDING_PUNCTUATION):
        return False, 0

    word_count = len(stripped.split())
    if word_count > _HEADING_MAX_WORDS:
        return False, 0

    numbered_match = _NUMBERED_HEADING.match(stripped)
    if numbered_match:
        depth = numbered_match.group(1).count(".") + 1
        return True, min(depth, 2)

    if _CHAPTER_OR_SECTION.match(stripped):
        return True, 1

    if stripped.isupper() and word_count <= _HEADING_MAX_WORDS:
        return True, 1

    if stripped.istitle() and word_count <= _HEADING_MAX_WORDS:
        return True, 2

    return False, 0


def detect_structure(text: str) -> list[Section]:
    """Parse cleaned text into a topic/subtopic tree based on heading heuristics.

    Text with no detectable headings at all comes back as a single
    level-1 Section titled "Document" containing all the text — callers
    should not assume the tree always has more than one node.
    """
    if not text or not text.strip():
        return []

    lines = [line for line in text.split("\n") if line.strip() != ""]

    sections: list[Section] = []
    current_topic: Section | None = None
    current_subtopic: Section | None = None
    content_buffer: list[str] = []

    def flush_content():
        if not content_buffer:
            return
        text_block = "\n".join(content_buffer).strip()
        if not text_block:
            content_buffer.clear()
            return
        nonlocal current_topic
        target = current_subtopic or current_topic
        if target is None:
            # Content appearing before any heading was found (e.g. a title
            # line our heuristics didn't recognize). Rather than silently
            # dropping it, give it a placeholder topic so no text is lost.
            current_topic = Section(title="Introduction", level=1)
            sections.append(current_topic)
            target = current_topic
        target.content = (target.content + "\n" + text_block).strip() if target.content else text_block
        content_buffer.clear()

    for line in lines:
        is_heading, level = _looks_like_heading(line)

        if is_heading:
            flush_content()
            title = re.sub(r"^\d+(\.\d+)*[.\)]?\s*", "", line.strip())
            title = re.sub(r"^(Chapter|Section|Part)\s+\d+[:\.]?\s*", "", title, flags=re.IGNORECASE) or line.strip()

            if level == 1:
                current_topic = Section(title=title, level=1)
                sections.append(current_topic)
                current_subtopic = None
            else:
                new_subtopic = Section(title=title, level=2)
                if current_topic is None:
                    # A subtopic-looking heading with no topic yet: promote it to a topic.
                    current_topic = Section(title=title, level=1)
                    sections.append(current_topic)
                    current_subtopic = None
                else:
                    current_topic.children.append(new_subtopic)
                    current_subtopic = new_subtopic
        else:
            content_buffer.append(line)

    flush_content()

    if not sections:
        # No headings detected anywhere — fall back to one flat "Document" section
        # so callers always get *something* usable rather than an empty list.
        return [Section(title="Document", level=1, content=text.strip())]

    if len(sections) == 1 and sections[0].title == "Introduction" and not sections[0].children:
        # The only "section" we created was the no-heading-found placeholder
        # (i.e. no real heading was ever detected anywhere in the text) —
        # relabel it to match the plain "no structure" fallback above,
        # rather than implying an "Introduction" heading exists when it doesn't.
        sections[0].title = "Document"

    return sections
