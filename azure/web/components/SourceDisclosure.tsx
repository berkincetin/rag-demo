"use client";

import { useState } from "react";

/**
 * The citation labels behind one answer, collapsed by default.
 *
 * Unlike the reference project there is no web-search fallback here: every
 * answer is either grounded in the corpus (or an uploaded file) or refused, so
 * an empty list means the model was told to stay silent rather than guess.
 */
export default function SourceDisclosure({ citations }: { citations: string[] }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-1">
      <button
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-1 rounded px-1 py-0.5 text-[11px] text-[var(--text-dim)]
          transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
      >
        <svg
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`transition-transform ${open ? "rotate-90" : ""}`}
        >
          <path d="M9 18l6-6-6-6" />
        </svg>
        {citations.length > 0 ? `${citations.length} kaynak` : "Kaynak yok"}
      </button>

      {open && (
        <div
          className="mt-1 flex flex-col gap-1 rounded-lg border border-[var(--border)]
            bg-[var(--surface-2)] px-3 py-2"
        >
          {citations.length === 0 ? (
            <p className="text-[11px] text-[var(--text-dim)]">Bu cevap bir kaynağa dayanmıyor.</p>
          ) : (
            citations.map((citation) => (
              <p key={citation} className="text-[11px] leading-relaxed text-[var(--text)]">
                {citation}
              </p>
            ))
          )}
        </div>
      )}
    </div>
  );
}
