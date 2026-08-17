"use client";

import { DocumentInfo } from "@/lib/types";

/**
 * Documents uploaded to the active conversation.
 *
 * These live in server memory with a TTL and are dropped on sign-out, so the
 * chip list is reconciled with the backend whenever the conversation changes.
 */
function Chip({ document, onRemove }: { document: DocumentInfo; onRemove: () => void }) {
  return (
    <div
      className="flex max-w-full items-center gap-1.5 rounded-lg border border-[var(--border)]
        bg-[var(--surface-2)] px-2 py-1 text-xs"
    >
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="shrink-0 text-[var(--accent)]"
      >
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <path d="M14 2v6h6" />
      </svg>
      <span className="truncate text-[var(--text)]">{document.filename}</span>
      <span className="shrink-0 text-[var(--text-dim)]">{document.chunkCount} parça</span>
      <button
        onClick={onRemove}
        title="Kaldır"
        className="shrink-0 rounded p-0.5 text-[var(--text-dim)] transition-colors
          hover:bg-[var(--surface)] hover:text-[var(--text)]"
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
        >
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

export default function DocumentChips({
  documents,
  onRemove,
}: {
  documents: DocumentInfo[];
  onRemove: (filename: string) => void;
}) {
  if (documents.length === 0) return null;

  return (
    <div className="mx-auto mb-2 flex max-w-3xl flex-wrap gap-1.5">
      {documents.map((document) => (
        <Chip
          key={document.filename}
          document={document}
          onRemove={() => onRemove(document.filename)}
        />
      ))}
    </div>
  );
}
