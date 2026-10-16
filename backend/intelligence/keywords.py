"""
Deterministic keyword extraction (RAKE — Rapid Automatic Keyword
Extraction), stdlib only.

Deliberately NOT LLM-based, unlike topics.py/summary.py: this needs to run
once per page and once per section of every uploaded document, and doing
that with an API call per page would be slow, expensive, and rate-limited.
RAKE is a well-known statistical algorithm — score words by how often they
co-occur with other words vs. how often they appear alone, then score
candidate phrases (runs of non-stopwords) by summing their word scores.

Reference: Rose et al., "Automatic Keyword Extraction from Individual
Documents" (2010).
"""
import re
from collections import defaultdict
from dataclasses import dataclass

_STOPWORDS = frozenset("""
a about above after again against all am an and any are aren't as at be
because been before being below between both but by can't cannot could
couldn't did didn't do does doesn't doing don't down during each few for
from further had hadn't has hasn't have haven't having he he'd he'll he's
her here here's hers herself him himself his how how's i i'd i'll i'm i've
if in into is isn't it it's its itself let's me more most mustn't my
myself no nor not of off on once only or other ought our ours ourselves
out over own same shan't she she'd she'll she's should shouldn't so some
such than that that's the their theirs them themselves then there there's
these they they'd they'll they're they've this those through to too under
until up very was wasn't we we'd we'll we're we've were weren't what
what's when when's where where's which while who who's whom why why's
with won't would wouldn't you you'd you'll you're you've your yours
yourself yourselves
""".split())

# Splits on anything that isn't a letter, digit, or internal apostrophe —
# this both tokenizes words and (via the stopword/punctuation gaps it
# creates) delimits candidate phrases.
_WORD_OR_BREAK = re.compile(r"[a-zA-Z0-9]+(?:'[a-zA-Z]+)?")

_MIN_WORD_LEN = 2
_MAX_PHRASE_WORDS = 4


@dataclass
class KeywordScore:
    phrase: str
    score: float

    def to_dict(self) -> dict:
        return {"phrase": self.phrase, "score": round(self.score, 2)}


def _split_into_candidate_phrases(text: str) -> list[list[str]]:
    """Break text into runs of consecutive non-stopwords (a stopword, or any
    non-word character/newline, ends the current candidate phrase)."""
    phrases: list[list[str]] = []
    current: list[str] = []
    pos = 0

    for match in _WORD_OR_BREAK.finditer(text):
        # A gap before this word (punctuation, whitespace beyond a single
        # space, or a line break) also breaks the phrase.
        gap = text[pos:match.start()]
        if "\n" in gap or re.search(r"[^\w\s']", gap):
            if current:
                phrases.append(current)
                current = []

        word = match.group().lower()
        pos = match.end()

        if word in _STOPWORDS or len(word) < _MIN_WORD_LEN or word.isdigit():
            if current:
                phrases.append(current)
                current = []
            continue

        current.append(word)
        if len(current) >= _MAX_PHRASE_WORDS:
            phrases.append(current)
            current = []

    if current:
        phrases.append(current)

    return phrases


def _score_words(phrases: list[list[str]]) -> dict[str, float]:
    degree: dict[str, int] = defaultdict(int)
    freq: dict[str, int] = defaultdict(int)

    for phrase in phrases:
        span = len(phrase) - 1
        for word in phrase:
            freq[word] += 1
            degree[word] += span  # co-occurrences with the OTHER words in this phrase

    for word in freq:
        degree[word] += freq[word]  # RAKE convention: a word co-occurs with itself once too

    return {word: degree[word] / freq[word] for word in freq}


def extract_keywords(text: str, max_keywords: int = 8) -> list[KeywordScore]:
    """Extract up to `max_keywords` keyword phrases from `text`, ranked by
    RAKE score (highest first). Returns [] for empty/whitespace-only text or
    text with no non-stopword content."""
    if not text or not text.strip():
        return []

    phrases = _split_into_candidate_phrases(text)
    if not phrases:
        return []

    word_scores = _score_words(phrases)

    phrase_scores: dict[str, float] = {}
    for phrase in phrases:
        joined = " ".join(phrase)
        score = sum(word_scores[word] for word in phrase)
        # A phrase can repeat verbatim across the document — keep its best score.
        phrase_scores[joined] = max(score, phrase_scores.get(joined, 0.0))

    ranked = sorted(phrase_scores.items(), key=lambda item: item[1], reverse=True)
    return [KeywordScore(phrase=phrase, score=score) for phrase, score in ranked[:max_keywords]]
