import { useMemo, useState } from "react";
import { SearchIcon } from "./Icons.jsx";

function buildKeywordIndex(result) {
  const rows = [];

  for (const page of result.pages || []) {
    for (const kw of page.keywords || []) {
      rows.push({ phrase: kw.phrase, score: kw.score, source: `Page ${page.page_number}` });
    }
  }

  for (const topic of result.topics || []) {
    for (const kw of topic.keywords || []) {
      rows.push({ phrase: kw.phrase, score: kw.score, source: `Topic: ${topic.title}` });
    }
    for (const subtopic of topic.subtopics || []) {
      for (const kw of subtopic.keywords || []) {
        rows.push({ phrase: kw.phrase, score: kw.score, source: `Subtopic: ${subtopic.title}` });
      }
    }
  }

  return rows.sort((a, b) => b.score - a.score);
}

export default function KeywordExplorer({ result }) {
  const [query, setQuery] = useState("");
  const allKeywords = useMemo(() => buildKeywordIndex(result), [result]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return allKeywords;
    return allKeywords.filter((row) => row.phrase.toLowerCase().includes(q));
  }, [allKeywords, query]);

  return (
    <div className="card" id="keywords">
      <h2>Keyword Explorer</h2>

      <div className="search-field">
        <SearchIcon className="search-field-icon" />
        <input
          type="search"
          className="search-input"
          placeholder="Search all extracted keywords…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search all extracted keywords"
        />
      </div>

      <div className="keyword-explorer-meta">
        {filtered.length} of {allKeywords.length} keyword{allKeywords.length === 1 ? "" : "s"}
      </div>

      {filtered.length > 0 ? (
        <ul className="keyword-row-list">
          {filtered.map((row, i) => (
            <li className="keyword-row" key={`${row.phrase}-${row.source}-${i}`}>
              <span className="keyword-row-phrase">{row.phrase}</span>
              <span className="keyword-row-source">{row.source}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty-state">No keywords match &ldquo;{query}&rdquo;.</p>
      )}
    </div>
  );
}
