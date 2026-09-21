"use client";

import { Upload } from "lucide-react";
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
  const [dragging, setDragging] = useState(false);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    handleFiles(event.dataTransfer.files);
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`rounded-2xl border-2 border-dashed px-6 py-14 text-center ${
        dragging ? "border-blue-500 bg-blue-50" : "border-blue-200 bg-white"
      }`}
    >
      <Upload className="mx-auto h-8 w-8 text-blue-600" />
      <p className="mt-4 text-lg font-semibold text-slate-900">
        Drag & drop your document here
      </p>
      <p className="mt-2 text-sm text-slate-500">PDF, JPG or PNG • PDFs up to 20 MB / 30 pages • images up to 10 MB</p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        disabled={busy}
        onChange={(event) => {
          handleFiles(event.target.files);
          event.target.value = "";
        }}
      />
      <div className="mt-6">
        <Button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
        >
          {busy ? "Uploading…" : "Choose file"}
        </Button>
      </div>
    </div>
  );
}
