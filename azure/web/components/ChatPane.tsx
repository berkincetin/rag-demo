"use client";

import { useEffect, useRef } from "react";

import { Message } from "@/lib/types";
import MessageBubble from "./MessageBubble";

export default function ChatPane({
  messages,
  streaming,
  onRegenerate,
  onEdit,
  onPickFile,
  documentCount,
  uploading,
}: {
  messages: Message[];
  streaming: boolean;
  onRegenerate: () => void;
  onEdit: (id: string, text: string) => void;
  onPickFile: () => void;
  documentCount: number;
  uploading: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-4">
        <div className="w-full max-w-md text-center">
          <div
            className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl
              bg-[var(--accent-soft)] text-[var(--accent)]"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
          </div>
          <h2 className="mb-1.5 text-lg font-semibold text-[var(--text)]">Bilgi Asistanı</h2>
          {/* Unlike the reference project the corpus is always loaded, so an
              upload is optional rather than a precondition. */}
          <p className="mb-5 text-sm text-[var(--text-dim)]">
            Şirket dokümanlarına soru sorabilir veya bu sohbete kendi dosyanızı ekleyebilirsiniz.
            Cevap bulunamazsa asistan bunu açıkça söyler.
          </p>

          <button
            onClick={onPickFile}
            disabled={uploading}
            className="mx-auto flex w-full items-center justify-center gap-2 rounded-xl border-2
              border-dashed border-[var(--border)] px-4 py-6 text-sm text-[var(--text-dim)]
              transition-colors hover:border-[var(--accent)] hover:text-[var(--text)]
              disabled:opacity-50"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <path d="M17 8l-5-5-5 5" />
              <path d="M12 3v12" />
            </svg>
            {uploading
              ? "Yükleniyor…"
              : documentCount > 0
                ? "Başka bir doküman ekleyin"
                : "Doküman yükleyin veya sürükleyip bırakın"}
          </button>

          {documentCount > 0 && (
            <p className="mt-3 text-xs text-[var(--text-dim)]">
              {documentCount} doküman bu sohbete yüklü.
            </p>
          )}
        </div>
      </div>
    );
  }

  const lastIndex = messages.length - 1;

  return (
    <div className="flex-1 overflow-y-auto px-4 py-5">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        {messages.map((message, index) => (
          <MessageBubble
            key={message.id}
            message={message}
            streaming={streaming && index === lastIndex && message.role === "assistant"}
            onRegenerate={onRegenerate}
            onEdit={(text) => onEdit(message.id, text)}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
