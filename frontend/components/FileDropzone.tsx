"use client";

import { useCallback, useRef, useState } from "react";

interface Props {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

export default function FileDropzone({ onFileSelected, disabled }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      const file = files[0];
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        return;
      }
      onFileSelected(file);
    },
    [onFileSelected]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (!disabled && (e.key === "Enter" || e.key === " ")) inputRef.current?.click();
      }}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-8 py-16 text-center transition-colors ${
        disabled
          ? "cursor-not-allowed border-ink/10 bg-ink/5 opacity-60"
          : isDragging
          ? "border-accent bg-accent/5"
          : "border-ink/20 bg-white hover:border-accent/50 hover:bg-accent/5"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        disabled={disabled}
        onChange={(e) => handleFiles(e.target.files)}
      />
      <p className="font-display text-xl text-ink">Upload your book</p>
      <p className="mt-2 text-sm text-ink/60">PDF files only</p>
      <p className="mt-1 text-xs text-ink/40">Maximum file size: configurable by your administrator</p>
      <span className="mt-6 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white">
        Choose a PDF
      </span>
    </div>
  );
}
