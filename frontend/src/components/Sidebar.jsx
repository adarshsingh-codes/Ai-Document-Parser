import ThemeToggle from "./ThemeToggle.jsx";

const STATUS_LABEL = {
  checking: "Checking backend…",
  online: "Backend connected",
  offline: "Backend unreachable",
};

const NAV_SECTIONS = [
  { href: "#overview", label: "Overview" },
  { href: "#summary", label: "Summary" },
  { href: "#topics", label: "Topics" },
  { href: "#keywords", label: "Keyword Explorer" },
];

export default function Sidebar({ theme, onToggleTheme, backendStatus, showNav }) {
  return (
    <aside className="dashboard-sidebar" aria-label="Sidebar">
      <div className="brand">
        <div className="brand-title">AI Document Parser</div>
        <div className="brand-subtitle">Topics, subtopics &amp; keywords</div>
      </div>

      <div
        className={`connection-indicator ${backendStatus}`}
        role="status"
        aria-live="polite"
      >
        <span className="status-dot" />
        {STATUS_LABEL[backendStatus]}
      </div>

      {showNav && (
        <nav className="sidebar-nav" aria-label="Document sections">
          {NAV_SECTIONS.map((item) => (
            <a className="nav-link" href={item.href} key={item.href}>
              {item.label}
            </a>
          ))}
        </nav>
      )}

      <div className="sidebar-footer">
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </aside>
  );
}
