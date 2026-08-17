"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Message } from "@/lib/types";
import SourceDisclosure from "./SourceDisclosure";

function CopyButton({ text, label = "Kopyala" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // No clipboard permission — nothing useful to say, so stay quiet.
    }
  }

  return (
    <button
      onClick={copy}
      title={label}
      className="rounded p-1 text-[var(--text-dim)] transition-colors
        hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
    >
      {copied ? (
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M20 6L9 17l-5-5" />
        </svg>
      ) : (
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="9" y="9" width="12" height="12" rx="2" />
          <path d="M5 15V5a2 2 0 012-2h10" />
        </svg>
      )}
    </button>
  );
}

export default function MessageBubble({
  message,
  streaming,
  onRegenerate,
  onEdit,
}: {
  message: Message;
  streaming: boolean;
  onRegenerate: () => void;
  onEdit: (newText: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);

  const isUser = message.role === "user";

  if (isUser && editing) {
    return (
      <div className="flex animate-rise justify-end">
        <div className="w-full max-w-[80%]">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={3}
            className="w-full resize-none rounded-xl border border-[var(--accent)]
              bg-[var(--surface)] p-3 text-sm text-[var(--text)] outline-none"
          />
          <div className="mt-1 flex justify-end gap-2">
            <button
              onClick={() => {
                setDraft(message.content);
                setEditing(false);
              }}
              className="rounded-lg px-3 py-1 text-xs text-[var(--text-dim)]
                hover:bg-[var(--surface-2)]"
            >
              İptal
            </button>
            <button
              onClick={() => {
                const clean = draft.trim();
                if (!clean) return;
                setEditing(false);
                onEdit(clean);
              }}
              className="rounded-lg bg-[var(--accent)] px-3 py-1 text-xs text-[var(--accent-fg)]"
            >
              Gönder
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="group flex animate-rise justify-end">
        <div className="flex max-w-[80%] items-start gap-1">
          <div className="flex gap-0.5 pt-1 opacity-0 transition-opacity group-hover:opacity-100">
            <CopyButton text={message.content} />
            <button
              onClick={() => {
                setDraft(message.content);
                setEditing(true);
              }}
              title="Düzenle"
              className="rounded p-1 text-[var(--text-dim)] transition-colors
                hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            >
              <svg
                width="14"
                height="14"
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
          </div>
          <div
            className="whitespace-pre-wrap rounded-2xl rounded-br-md bg-[var(--accent)]
              px-4 py-2.5 text-sm text-[var(--accent-fg)]"
          >
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  const empty = !message.content && !message.error;

  return (
    <div className="group flex animate-rise justify-start">
      <div className="max-w-[85%]">
        <div
          className="rounded-2xl rounded-bl-md border border-[var(--border)] bg-[var(--surface)]
            px-4 py-3 text-sm text-[var(--text)]"
        >
          {message.error ? (
            <p className="text-[var(--danger)]">{message.error}</p>
          ) : empty ? (
            <span className="stream-cursor" />
          ) : (
            <div>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => <p className="mb-2 leading-relaxed last:mb-0">{children}</p>,
                  ul: ({ children }) => (
                    <ul className="mb-2 list-disc pl-5 last:mb-0">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="mb-2 list-decimal pl-5 last:mb-0">{children}</ol>
                  ),
                  li: ({ children }) => <li className="mb-0.5">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  a: ({ children, href }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[var(--accent)] underline"
                    >
                      {children}
                    </a>
                  ),
                  table: ({ children }) => (
                    <div className="mb-2 overflow-x-auto">
                      <table className="w-full border-collapse text-xs">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th
                      className="border border-[var(--border)] bg-[var(--surface-2)] px-2 py-1
                        text-left font-semibold"
                    >
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-[var(--border)] px-2 py-1">{children}</td>
                  ),
                  code: ({ className, children }) => {
                    const isBlock = (className ?? "").includes("language-");
                    if (!isBlock) {
                      return (
                        <code
                          className="rounded bg-[var(--surface-2)] px-1 py-0.5 font-mono
                            text-[0.85em]"
                        >
                          {children}
                        </code>
                      );
                    }
                    const codeText = String(children).replace(/\n$/, "");
                    return (
                      <span className="relative mb-2 block">
                        <span className="absolute right-1.5 top-1.5 z-10">
                          <CopyButton text={codeText} label="Kodu kopyala" />
                        </span>
                        <code
                          className="block overflow-x-auto rounded-lg bg-[var(--surface-2)] p-3
                            font-mono text-xs"
                        >
                          {codeText}
                        </code>
                      </span>
                    );
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
              {streaming && <span className="stream-cursor ml-0.5" />}
            </div>
          )}
        </div>

        {!empty && (
          <div className="pl-1">
            <div className="flex gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
              {message.content && <CopyButton text={message.content} />}
              <button
                onClick={onRegenerate}
                title="Yeniden üret"
                className="rounded p-1 text-[var(--text-dim)] transition-colors
                  hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12a9 9 0 11-3-6.7L21 8" />
                  <path d="M21 3v5h-5" />
                </svg>
              </button>
            </div>
            {!streaming && !message.error && message.citations !== undefined && (
              <SourceDisclosure citations={message.citations} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
