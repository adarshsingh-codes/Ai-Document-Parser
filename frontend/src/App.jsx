import { useState } from "react";
import FileUpload from "./components/FileUpload.jsx";
import DocumentOverview from "./components/DocumentOverview.jsx";
import Summary from "./components/Summary.jsx";
import TopicTree from "./components/TopicTree.jsx";
import KeywordExplorer from "./components/KeywordExplorer.jsx";
import Sidebar from "./components/Sidebar.jsx";
import { DownloadIcon, FileIcon } from "./components/Icons.jsx";
import { useTheme } from "./useTheme.js";
import { useBackendStatus } from "./useBackendStatus.js";

const NETWORK_ERROR_MESSAGE =
  "Could not reach the backend. Make sure the API server is running, then try again.";

const STATUS = {
  IDLE: "idle",
  ANALYZING: "analyzing",
  DONE: "done",
  ERROR: "error",
};

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const backendStatus = useBackendStatus();
  const [status, setStatus] = useState(STATUS.IDLE);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState(null);

  async function handleFileSelected(file, validationError) {
    if (validationError) {
      setError(validationError);
      setStatus(STATUS.ERROR);
      return;
    }

    setFileName(file.name);
    setStatus(STATUS.ANALYZING);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${response.status})`);
      }

      const data = await response.json();
      setResult(data);
      setStatus(STATUS.DONE);
    } catch (err) {
      const isNetworkError = err instanceof TypeError;
      setError(isNetworkError ? NETWORK_ERROR_MESSAGE : err.message || "Something went wrong while analyzing the document.");
      setStatus(STATUS.ERROR);
    }
  }

  function reset() {
    setStatus(STATUS.IDLE);
    setResult(null);
    setError(null);
    setFileName(null);
  }

  function downloadJson() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.filename || "analysis"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="dashboard">
      <Sidebar
        theme={theme}
        onToggleTheme={toggleTheme}
        backendStatus={backendStatus}
        showNav={status === STATUS.DONE}
      />

      <main className="dashboard-main">
        <header className="main-header">
          <h1>AI Document Parser</h1>
          <p>Upload a document to identify its topics, subtopics, and keywords.</p>
        </header>

        {status === STATUS.IDLE && <FileUpload onFileSelected={handleFileSelected} />}

        {status === STATUS.ANALYZING && (
          <div className="card status-card">
            <span className="spinner" />
            <div style={{ flex: 1 }}>
              <div className="status-filename">
                <FileIcon style={{ verticalAlign: "-3px", marginRight: 6 }} />
                {fileName}
              </div>
              <div className="status-sub">Parsing, extracting keywords, and generating topics&hellip;</div>
              <div className="progress-track">
                <div className="progress-fill" />
              </div>
            </div>
          </div>
        )}

        {status === STATUS.ERROR && (
          <>
            <div className="error-banner" role="alert">
              {error}
            </div>
            <button className="reset-link" onClick={reset}>
              Try another file
            </button>
          </>
        )}

        {status === STATUS.DONE && result && (
          <>
            <div className="results-toolbar">
              <button className="ghost-button" onClick={downloadJson}>
                <DownloadIcon /> Download JSON
              </button>
            </div>
            <DocumentOverview
              filename={result.filename}
              fileType={result.file_type}
              pageCount={result.page_count}
              pages={result.pages}
            />
            <Summary summary={result.summary} aiAvailable={result.ai_available} aiError={result.ai_error} />
            <TopicTree topics={result.topics} />
            <KeywordExplorer result={result} />
            <button className="reset-link" onClick={reset}>
              Analyze another file
            </button>
          </>
        )}
      </main>
    </div>
  );
}
