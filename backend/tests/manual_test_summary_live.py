"""
MANUAL / LIVE TEST — makes a real call to the Gemini API. Costs a small
amount of money and requires GEMINI_API_KEY to be set. Not picked up by
pytest's default discovery. Run explicitly:

    python backend/tests/manual_test_summary_live.py
"""
import json
import sys

from backend.processing.structure import detect_structure
from backend.intelligence.summary import get_document_summary
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
    print(f"Found {len(sections)} top-level section(s).\n")

    print("Calling real Gemini API for document summary...")
    try:
        result = get_document_summary(sections)
    except LLMError as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)

    print("\nGot summary back:\n")
    print(json.dumps(result.to_dict(), indent=2))

    # Sanity checks a human should eyeball, not hard assertions.
    if len(result.key_points) < 2:
        print("\nNOTE: fewer than 2 key points came back — worth a look.")
    if len(result.document_summary.split(".")) < 2:
        print("\nNOTE: document_summary looks like it might be a single sentence, not 2-4.")
    else:
        print("\nLooks reasonable at a glance.")


if __name__ == "__main__":
    main()
