import { useRef, useState } from "react";
import { UploadIcon } from "./Icons.jsx";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt"];

function hasAcceptedExtension(filename) {
  const lower = filename.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export default function FileUpload({ onFileSelected }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function handleFiles(fileList) {
    const file = fileList?.[0];
    if (!file) return;
    if (!hasAcceptedExtension(file.name)) {
      onFileSelected(null, `Unsupported file type. Please upload a ${ACCEPTED_EXTENSIONS.join(", ")} file.`);
      return;
    }
    onFileSelected(file, null);
  }

  return (
    <div
      className={`dropzone${dragging ? " dragging" : ""}`}
      role="button"
      tabIndex={0}
      aria-label={`Upload a document. Supports ${ACCEPTED_EXTENSIONS.join(", ")}`}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <UploadIcon className="dropzone-icon" />
      <div className="dropzone-title">Drop a document here, or click to browse</div>
      <div className="dropzone-hint">Supports {ACCEPTED_EXTENSIONS.join(", ")}</div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
