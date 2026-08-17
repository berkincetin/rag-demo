"use client";

import { useEffect, useRef, useState } from "react";

import { Conversation } from "@/lib/types";

export default function ConversationItem({
  conversation,
  active,
  collapsed,
  onSelect,
  onRename,
  onDelete,
}: {
  conversation: Conversation;
  active: boolean;
  collapsed: boolean;
  onSelect: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(conversation.title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  function commit() {
    setEditing(false);
    const clean = draft.trim();
    if (clean && clean !== conversation.title) onRename(clean);
    else setDraft(conversation.title);
  }

  if (collapsed) {
    return (
      <button
        onClick={onSelect}
        title={conversation.title}
        className={`flex h-9 w-10 items-center justify-center rounded-lg text-sm transition-colors
          ${
            active
              ? "bg-[var(--accent-soft)] text-[var(--accent)]"
              : "text-[var(--text-dim)] hover:bg-[var(--surface-2)]"
          }`}
      >
        💬
      </button>
    );
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") commit();
          if (event.key === "Escape") {
            setDraft(conversation.title);
            setEditing(false);
          }
        }}
        className="w-full rounded-lg border border-[var(--accent)] bg-[var(--bg)] px-2 py-1.5
          text-sm text-[var(--text)] outline-none"
      />
    );
  }

  return (
    <div
      className={`group flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm transition-colors
        ${
          active
            ? "bg-[var(--accent-soft)] text-[var(--accent)]"
            : "text-[var(--text-dim)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
        }`}
    >
      <button onClick={onSelect} className="flex-1 truncate text-left">
        {conversation.title}
      </button>

      <div className="flex shrink-0 gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
        <button
          onClick={() => {
            setDraft(conversation.title);
            setEditing(true);
          }}
          title="Yeniden adlandır"
          className="rounded p-1 hover:bg-[var(--surface)]"
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
          >
            <path d="M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4z" />
          </svg>
        </button>
        <button
          onClick={onDelete}
          title="Sil"
          className="rounded p-1 hover:bg-[var(--surface)] hover:text-[var(--danger)]"
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
          >
            <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />
          </svg>
        </button>
      </div>
    </div>
  );
}
