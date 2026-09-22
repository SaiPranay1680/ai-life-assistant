"use client";

import { CloudUpload } from "lucide-react";
import { useCallback, useRef, useState, type DragEvent } from "react";
import { Button } from "@/components/ui/Button";

const ACCEPT = ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png";

export function UploadBox({
  onFile,
  busy,
}: {
  onFile: (file: File) => void;
  busy?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const dragCount = useRef(0);
  const [dragging, setDragging] = useState(false);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  function resetDrag() {
    dragCount.current = 0;
    setDragging(false);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    resetDrag();
    if (busy) return;
    handleFiles(event.dataTransfer.files);
  }

  return (
    <div
      onDragEnter={(event) => {
        event.preventDefault();
        if (busy) return;
        dragCount.current += 1;
        setDragging(true);
      }}
      onDragOver={(event) => {
        event.preventDefault();
        if (busy) event.dataTransfer.dropEffect = "none";
      }}
      onDragLeave={(event) => {
        event.preventDefault();
        dragCount.current = Math.max(0, dragCount.current - 1);
        if (dragCount.current === 0) setDragging(false);
      }}
      onDrop={onDrop}
      aria-busy={busy || undefined}
      className={`rounded-3xl border-2 border-dashed px-6 py-16 text-center ${
        dragging ? "border-blue-500 bg-blue-50" : "border-blue-200 bg-white"
      } ${busy ? "opacity-70" : ""}`}
    >
      <CloudUpload className="mx-auto h-10 w-10 text-blue-500" aria-hidden="true" />
      <p id="upload-title" className="mt-4 text-lg font-semibold text-slate-900">
        Drag & drop your document here
      </p>
<<<<<<< Updated upstream
      <p className="mt-2 text-sm text-slate-500">PDF, JPG or PNG • up to 20 MB</p>
=======
      <p id="upload-hint" className="mt-2 text-sm text-slate-500">
        PDF, JPG or PNG • PDFs up to 20 MB / 30 pages • images up to 10 MB
      </p>
>>>>>>> Stashed changes
      <input
        ref={inputRef}
        id="inbox-file"
        type="file"
        accept={ACCEPT}
        className="sr-only"
        tabIndex={-1}
        disabled={busy}
        aria-labelledby="upload-title"
        aria-describedby="upload-hint"
        onChange={(event) => {
          handleFiles(event.target.files);
          event.target.value = "";
        }}
      />
      <div className="mt-6">
        <Button
          type="button"
          variant="secondary"
          className="border-blue-200 text-blue-700 hover:bg-blue-50"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
        >
          {busy ? "Uploading…" : "Choose file"}
        </Button>
      </div>
    </div>
  );
}
