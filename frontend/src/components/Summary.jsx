import { useState } from "react";
import { CopyIcon, CheckIcon } from "./Icons.jsx";

function buildClipboardText(summary) {
  const points = (summary.key_points || []).map((p) => `- ${p}`).join("\n");
  return points ? `${summary.document_summary}\n\n${points}` : summary.document_summary;
}

export default function Summary({ summary, aiAvailable, aiError }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(buildClipboardText(summary));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be denied by the browser; the button simply
      // won't show the "Copied" confirmation in that case.
    }
  }

  return (
    <div className="card" id="summary">
      <div className="card-header-row">
        <h2>Summary</h2>
        {summary && (
          <button className="ghost-button" onClick={handleCopy} aria-label="Copy summary to clipboard">
            {copied ? <CheckIcon /> : <CopyIcon />}
            {copied ? "Copied" : "Copy"}
          </button>
        )}
      </div>
      {!aiAvailable && (
        <div className="notice">
          AI summary unavailable{aiError ? ` (${aiError})` : ""}. Showing deterministic results only.
        </div>
      )}
      {summary ? (
        <>
          <p className="document-summary">{summary.document_summary}</p>
          {summary.key_points?.length > 0 && (
            <ul className="key-points">
              {summary.key_points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <p className="empty-state">No summary available for this document.</p>
      )}
    </div>
  );
}
