from backend.processing.structure import detect_structure


def test_empty_text_returns_no_sections():
    assert detect_structure("") == []
    assert detect_structure("   ") == []


def test_no_headings_falls_back_to_single_document_section():
    text = "just a plain paragraph with no headings at all in it whatsoever."
    sections = detect_structure(text)
    assert len(sections) == 1
    assert sections[0].title == "Document"
    assert sections[0].level == 1
    assert "plain paragraph" in sections[0].content


def test_all_caps_line_detected_as_topic():
    text = "OPERATING SYSTEMS\nThis chapter introduces core OS concepts."
    sections = detect_structure(text)
    assert len(sections) == 1
    assert sections[0].title == "OPERATING SYSTEMS"
    assert sections[0].level == 1
    assert "introduces core OS concepts" in sections[0].content


def test_title_case_line_detected_as_subtopic_under_topic():
    text = (
        "OPERATING SYSTEMS\n"
        "General introduction text goes here.\n"
        "Process Management\n"
        "Process scheduling is a core responsibility of the kernel.\n"
    )
    sections = detect_structure(text)
    assert len(sections) == 1
    topic = sections[0]
    assert topic.title == "OPERATING SYSTEMS"
    assert len(topic.children) == 1
    subtopic = topic.children[0]
    assert subtopic.title == "Process Management"
    assert subtopic.level == 2
    assert "core responsibility of the kernel" in subtopic.content


def test_numbered_headings_set_depth():
    text = (
        "1. Introduction\n"
        "Some intro text.\n"
        "1.1 Background\n"
        "Some background text.\n"
        "2. Methodology\n"
        "Some methodology text.\n"
    )
    sections = detect_structure(text)
    assert len(sections) == 2
    assert sections[0].title == "Introduction"
    assert sections[0].level == 1
    assert len(sections[0].children) == 1
    assert sections[0].children[0].title == "Background"
    assert sections[0].children[0].level == 2
    assert sections[1].title == "Methodology"


def test_chapter_prefixed_heading_detected_as_topic():
    text = "Chapter 1: Getting Started\nThis is the getting started content."
    sections = detect_structure(text)
    assert len(sections) == 1
    assert sections[0].title == "Getting Started"
    assert sections[0].level == 1


def test_content_accumulates_under_correct_section():
    text = (
        "TOPIC ONE\n"
        "Line A for topic one.\n"
        "Line B for topic one.\n"
        "TOPIC TWO\n"
        "Line C for topic two.\n"
    )
    sections = detect_structure(text)
    assert len(sections) == 2
    assert "Line A for topic one" in sections[0].content
    assert "Line B for topic one" in sections[0].content
    assert "Line C" not in sections[0].content
    assert "Line C for topic two" in sections[1].content


def test_known_limitation_consecutive_title_case_headings_nest_instead_of_sibling():
    # Documents a real heuristic limitation: without numbering or ALL CAPS,
    # two consecutive Title Case headings can't be distinguished from a
    # topic/subtopic pair, so the second nests under the first rather than
    # becoming a sibling. This is expected to improve once Phase 3's AI
    # layer re-ranks structure — flagging it here so a future fix doesn't
    # silently break an assumption nobody wrote down.
    text = "Topic One\nLine A.\nTopic Two\nLine B.\n"
    sections = detect_structure(text)
    assert len(sections) == 1
    assert sections[0].children[0].title == "Topic Two"


def test_sentence_like_line_not_treated_as_heading():
    # Ends in a period and is a full sentence -> should not be misdetected as a heading.
    text = "This is a normal sentence that happens to be short."
    sections = detect_structure(text)
    assert sections[0].title == "Document"  # fell back, no heading detected


def test_to_dict_produces_nested_structure():
    text = "OPERATING SYSTEMS\nIntro text.\nProcess Management\nScheduling text."
    sections = detect_structure(text)
    d = sections[0].to_dict()
    assert d["title"] == "OPERATING SYSTEMS"
    assert d["children"][0]["title"] == "Process Management"
    assert d["children"][0]["level"] == 2


def test_content_before_first_heading_is_not_dropped():
    # Regression test: text before any recognized heading used to be
    # silently discarded because there was no section to attach it to.
    # Found via manual real-file testing on a PDF whose title line
    # ("Project Plan: AI Document Parser") wasn't detected as a heading
    # (mixed-case acronym "AI" broke the Title Case check), causing the
    # entire first page's content to vanish from the structure output.
    text = (
        "Project Plan: AI Document Parser\n"
        "Some intro sentence that isn't detected as a heading.\n"
        "TOPIC TWO\n"
        "Content under topic two.\n"
    )
    sections = detect_structure(text)
    assert len(sections) == 2
    assert sections[0].title == "Introduction"
    assert "Project Plan: AI Document Parser" in sections[0].content
    assert "intro sentence" in sections[0].content
    assert sections[1].title == "TOPIC TWO"
