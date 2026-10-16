import { useState } from "react";
import Keywords from "./Keywords.jsx";

export default function DocumentOverview({ filename, fileType, pageCount, pages }) {
  const [activePage, setActivePage] = useState(pages?.[0]?.page_number ?? null);
  const active = pages?.find((p) => p.page_number === activePage);

  return (
    <div className="card" id="overview">
      <h2>Document</h2>
      <div className="overview-meta">
        <span>
          <strong>{filename}</strong>
        </span>
        <span className="file-type-badge">{fileType?.toUpperCase()}</span>
        <span>
          {pageCount} page{pageCount === 1 ? "" : "s"}
        </span>
      </div>

      {pages?.length > 0 && (
        <>
          <div className="page-strip">
            {pages.map((p) => (
              <button
                key={p.page_number}
                className={`page-chip${p.page_number === activePage ? " active" : ""}`}
                onClick={() => setActivePage(p.page_number)}
              >
                Page {p.page_number}
              </button>
            ))}
          </div>
          {active?.keywords?.length > 0 ? (
            <Keywords keywords={active.keywords} />
          ) : (
            <p className="empty-state">No keywords found on this page.</p>
          )}
        </>
      )}
    </div>
  );
}
