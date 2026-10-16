import { useState } from "react";
import Keywords from "./Keywords.jsx";
import { ChevronIcon } from "./Icons.jsx";

function TopicNode({ topic }) {
  const [open, setOpen] = useState(true);

  return (
    <div className="topic">
      <div
        className="topic-header"
        role="button"
        tabIndex={0}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen((o) => !o);
          }
        }}
      >
        <span className="topic-title">
          <span className={`topic-caret${open ? " open" : ""}`}>
            <ChevronIcon />
          </span>
          {topic.title}
        </span>
      </div>
      {open && (
        <>
          {topic.summary && <p className="topic-summary">{topic.summary}</p>}
          <Keywords keywords={topic.keywords} />
          {topic.subtopics?.length > 0 && (
            <div className="subtopic-list">
              {topic.subtopics.map((subtopic) => (
                <div className="subtopic" key={subtopic.title}>
                  <div className="subtopic-title">{subtopic.title}</div>
                  {subtopic.summary && <p className="subtopic-summary">{subtopic.summary}</p>}
                  <Keywords keywords={subtopic.keywords} />
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function TopicTree({ topics }) {
  return (
    <div className="card" id="topics">
      <h2>Topics &amp; Subtopics</h2>
      {topics?.length > 0 ? (
        topics.map((topic) => <TopicNode topic={topic} key={topic.title} />)
      ) : (
        <p className="empty-state">No topics available for this document.</p>
      )}
    </div>
  );
}
