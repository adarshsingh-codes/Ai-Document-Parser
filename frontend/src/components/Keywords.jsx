export default function Keywords({ keywords }) {
  if (!keywords || keywords.length === 0) {
    return null;
  }

  return (
    <div className="keyword-list">
      {keywords.map((kw) => (
        <span className="keyword-pill" key={kw.phrase}>
          {kw.phrase}
        </span>
      ))}
    </div>
  );
}
