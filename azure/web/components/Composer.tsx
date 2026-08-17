"use client";

import { useEffect, useRef, useState } from "react";

import { DocumentInfo } from "@/lib/types";
import DocumentChips from "./DocumentChips";

export default function Composer({
  onSend,
  disabled,
  placeholder,
  documents,
  onPickFile,
  onRemoveDocument,
  uploading,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
  placeholder: string;
  documents: DocumentInfo[];
  onPickFile: () => void;
  onRemoveDocument: (filename: string) => void;
  uploading: boolean;
}) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-growing textarea, capped so a long paste cannot eat the transcript.
  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = Math.min(element.scrollHeight, 200) + "px";
  }, [text]);

  function submit() {
    const clean = text.trim();
    if (!clean || disabled) return;
    onSend(clean);
    setText("");
  }

  return (
    <div className="border-t border-[var(--border)] bg-[var(--bg)] px-4 py-3">
      <DocumentChips documents={documents} onRemove={onRemoveDocument} />

      <div
        className="mx-auto flex max-w-3xl items-end gap-1 rounded-2xl border border-[var(--border)]
          bg-[var(--surface)] p-2 focus-within:border-[var(--accent)]"
      >
        <button
          onClick={onPickFile}
          disabled={uploading}
          title="Doküman ekle (.pdf, .docx, .xlsx, .txt)"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl
            text-[var(--text-dim)] transition-colors hover:bg-[var(--surface-2)]
            hover:text-[var(--text)] disabled:opacity-40"
        >
          {uploading ? (
            <span className="stream-cursor" />
          ) : (
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path
                d="M21.4 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2
                  9.19a2 2 0 01-2.83-2.83l8.49-8.48"
              />
            </svg>
          )}
        </button>

        <textarea
          ref={textareaRef}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          rows={1}
          placeholder={placeholder}
          className="flex-1 resize-none bg-transparent px-1 py-1.5 text-sm text-[var(--text)]
            outline-none placeholder:text-[var(--text-dim)]"
        />

        <button
          onClick={submit}
          disabled={disabled || !text.trim()}
          title="Gönder (Enter)"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl
            bg-[var(--accent)] text-[var(--accent-fg)] transition-colors
            disabled:cursor-not-allowed disabled:opacity-40"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 19V5M5 12l7-7 7 7" />
          </svg>
        </button>
      </div>

      <p className="mx-auto mt-1.5 max-w-3xl text-center text-[11px] text-[var(--text-dim)]">
        Enter ile gönder, Shift+Enter ile yeni satır
      </p>
    </div>
  );
}
