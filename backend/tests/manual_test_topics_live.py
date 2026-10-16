"""
MANUAL / LIVE TEST — makes a real call to the Gemini API. Costs a small
amount of money and requires GEMINI_API_KEY to be set. This is
deliberately named so pytest's default discovery (test_*.py) does NOT
pick it up automatically — run it explicitly:

    python backend/tests/manual_test_topics_live.py

Use this to sanity-check real model output after changing the prompt,
switching models, or before trusting mocked unit tests alone.
"""
import json
import sys

from backend.processing.structure import detect_structure
from backend.intelligence.topics import get_topics_and_subtopics
from backend.intelligence.llm_client import LLMError

SAMPLE_DOCUMENT = """OPERATING SYSTEMS

This chapter introduces the core responsibilities of an operating system,
including process management, memory management, and file systems.

Process Management

A process is a program in execution. The kernel is responsible for
creating, scheduling, and terminating processes. Common scheduling
algorithms include Round Robin, First-Come-First-Served, and
Shortest-Job-First.

Memory Management

The operating system manages allocation and deallocation of memory
space as needed by processes. Virtual memory allows a process to use
more memory than is physically available by swapping pages to disk.

DATABASE SYSTEMS

This chapter covers relational database concepts, including normalization,
transactions, and indexing strategies for query performance.
"""


def main():
    print("Detecting deterministic structure...")
    sections = detect_structure(SAMPLE_DOCUMENT)
    print(f"Found {len(sections)} top-level section(s):")
    for i, s in enumerate(sections):
        print(f"  [{i}] {s.title} (level {s.level}, {len(s.children)} children)")

    print("\nCalling real Gemini API for topic/subtopic extraction...")
    try:
        topics = get_topics_and_subtopics(sections)
    except LLMError as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)

    print(f"\nGot {len(topics)} topic(s) back:\n")
    print(json.dumps([t.to_dict() for t in topics], indent=2))

    # A few sanity checks a human should eyeball, not hard assertions —
    # real model output varies run to run.
    all_indices = {i for t in topics for i in t.source_section_indices}
    expected_indices = set(range(len(sections)))
    if all_indices != expected_indices:
        print(
            f"\nNOTE: section indices don't perfectly match "
            f"(got {sorted(all_indices)}, expected {sorted(expected_indices)}). "
            "Worth a look, but not necessarily a bug — check the output above."
        )
    else:
        print("\nAll sections were accounted for across topics. Looks good.")


if __name__ == "__main__":
    main()
