"use client";

/**
 * Conversation state and every call that changes it.
 *
 * The browser owns conversations; the server is told what it needs per request
 * (summary + unsummarized history) and remembers nothing between them.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { buildContext, messagesToSummarize, needsSummarization, SUMMARY_BLOCK } from "./memory";
import { readSseStream } from "./sse";
import {
  createConversation,
  generateTitle,
  loadConversations,
  newId,
  saveConversations,
} from "./storage";
import { Conversation, DocumentInfo, Message } from "./types";

const BASE = "/api/proxy";

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [documentsByConversation, setDocumentsByConversation] = useState<
    Record<string, DocumentInfo[]>
  >({});
  const [loaded, setLoaded] = useState(false);

  // Streaming closures need the newest list, which a captured `conversations`
  // cannot give them. Assigned in an effect, not during render: effects run
  // before any event handler for that render can fire, so readers still see
  // the current value.
  const conversationsRef = useRef<Conversation[]>([]);
  useEffect(() => {
    conversationsRef.current = conversations;
  }, [conversations]);

  useEffect(() => {
    const stored = loadConversations();
    const list = stored.length > 0 ? stored : [createConversation()];
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setConversations(list);
    setActiveId(list[0].id);
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (!loaded) return;
    const error = saveConversations(conversations);
    // Syncing to an external store (localStorage) and reporting its failure is
    // exactly the case the rule exempts; the quota error has no other path to
    // the user, and a silent failed write loses their conversation.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (error) setToast(error);
  }, [conversations, loaded]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  const active = conversations.find((c) => c.id === activeId) ?? null;
  const activeDocuments = activeId ? (documentsByConversation[activeId] ?? []) : [];

  const updateConversation = useCallback(
    (id: string, updater: (c: Conversation) => Conversation) => {
      setConversations((previous) => previous.map((c) => (c.id === id ? updater(c) : c)));
    },
    [],
  );

  // --- documents ------------------------------------------------------------

  const refreshDocuments = useCallback(async (conversationId: string) => {
    try {
      const response = await fetch(
        `${BASE}/api/documents?conversation_id=${encodeURIComponent(conversationId)}`,
      );
      if (!response.ok) return;
      const data = await response.json();
      setDocumentsByConversation((previous) => ({
        ...previous,
        [conversationId]: data.documents ?? [],
      }));
    } catch {
      // The list stays as it was; the next switch retries.
    }
  }, []);

  useEffect(() => {
    // Server-side uploads expire on a TTL while the browser still lists them,
    // so reconcile whenever the conversation changes. State is set from the
    // awaited response, which the rule cannot distinguish from a synchronous
    // set during the effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (activeId) void refreshDocuments(activeId);
  }, [activeId, refreshDocuments]);

  const uploadDocument = useCallback(
    async (file: File): Promise<string | null> => {
      if (!activeId) return "Aktif sohbet yok.";
      const form = new FormData();
      form.append("file", file);
      form.append("conversation_id", activeId);
      try {
        const response = await fetch(`${BASE}/api/documents/upload`, {
          method: "POST",
          body: form,
        });
        const data = await response.json();
        if (!response.ok) return data.detail ?? "Yükleme başarısız.";
        const documents: DocumentInfo[] = data.documents ?? [];
        setDocumentsByConversation((previous) => ({ ...previous, [activeId]: documents }));
        updateConversation(activeId, (c) => ({
          ...c,
          documentName: documents.map((d) => d.filename).join(", ") || null,
          updatedAt: Date.now(),
        }));
        return null;
      } catch {
        return "Yükleme başarısız: bağlantı hatası.";
      }
    },
    [activeId, updateConversation],
  );

  const removeDocument = useCallback(
    async (filename: string) => {
      if (!activeId) return;
      try {
        const response = await fetch(
          `${BASE}/api/documents?conversation_id=${encodeURIComponent(activeId)}` +
            `&filename=${encodeURIComponent(filename)}`,
          { method: "DELETE" },
        );
        if (!response.ok) return;
        const data = await response.json();
        setDocumentsByConversation((previous) => ({
          ...previous,
          [activeId]: data.documents ?? [],
        }));
      } catch {
        // Leave the chip in place; the next refresh reconciles.
      }
    },
    [activeId],
  );

  // --- summarization --------------------------------------------------------

  const maybeSummarize = useCallback(
    async (conversationId: string) => {
      const conversation = conversationsRef.current.find((c) => c.id === conversationId);
      if (!conversation || !needsSummarization(conversation)) return;

      try {
        const response = await fetch(`${BASE}/api/summarize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            previousSummary: conversation.summary ?? "",
            messages: messagesToSummarize(conversation).map((m) => ({
              role: m.role,
              content: m.content,
            })),
          }),
        });
        if (!response.ok) return;
        const data = await response.json();
        if (!data.summary) return;
        updateConversation(conversationId, (c) => ({
          ...c,
          summary: data.summary,
          summarizedUpTo: c.summarizedUpTo + SUMMARY_BLOCK,
        }));
      } catch {
        // Retried on the next block; the user never waits for this.
      }
    },
    [updateConversation],
  );

  // --- asking ---------------------------------------------------------------

  const runAsk = useCallback(
    async (conversationId: string, question: string, baseMessages: Message[]) => {
      const conversation = conversationsRef.current.find((c) => c.id === conversationId);
      if (!conversation) return;

      const userMessage: Message = {
        id: newId(),
        role: "user",
        content: question,
        createdAt: Date.now(),
      };
      const assistantMessage: Message = {
        id: newId(),
        role: "assistant",
        content: "",
        createdAt: Date.now(),
      };

      updateConversation(conversationId, (c) => ({
        ...c,
        title: baseMessages.length === 0 ? generateTitle(question) : c.title,
        messages: [...baseMessages, userMessage, assistantMessage],
        updatedAt: Date.now(),
      }));
      setStreaming(true);

      const { summary, recentMessages } = buildContext({
        ...conversation,
        messages: baseMessages,
      });

      const patch = (updater: (m: Message) => Message) =>
        updateConversation(conversationId, (c) => ({
          ...c,
          messages: c.messages.map((m) => (m.id === assistantMessage.id ? updater(m) : m)),
        }));

      try {
        const response = await fetch(`${BASE}/api/ask/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question,
            conversationId,
            summary,
            history: recentMessages.map((m) => ({ role: m.role, content: m.content })),
          }),
        });

        if (!response.ok || !response.body) {
          const data = await response.json().catch(() => ({ detail: "Bilinmeyen hata" }));
          patch((m) => ({ ...m, error: data.detail ?? "Bilinmeyen hata" }));
          return;
        }

        await readSseStream(response.body, (event) => {
          if (event.type === "start") {
            patch((m) => ({ ...m, content: "" }));
          } else if (event.type === "token") {
            const text = String(event.content ?? "");
            patch((m) => ({ ...m, content: m.content + text }));
          } else if (event.type === "replace") {
            // The citation gate substituted the answer after it streamed.
            patch((m) => ({ ...m, content: String(event.content ?? "") }));
          } else if (event.type === "meta") {
            patch((m) => ({
              ...m,
              citations: (event.citations as string[]) ?? [],
              grounded: Boolean(event.grounded),
            }));
          } else if (event.type === "error") {
            patch((m) => ({ ...m, error: String(event.detail ?? "Bilinmeyen hata") }));
          }
        });
      } catch {
        patch((m) => ({ ...m, error: "Bağlantı kesildi." }));
      } finally {
        setStreaming(false);
        updateConversation(conversationId, (c) => ({ ...c, updatedAt: Date.now() }));
        void maybeSummarize(conversationId);
      }
    },
    [maybeSummarize, updateConversation],
  );

  const sendMessage = useCallback(
    (question: string) => {
      if (!activeId || streaming) return;
      const conversation = conversationsRef.current.find((c) => c.id === activeId);
      if (!conversation) return;
      void runAsk(activeId, question, conversation.messages);
    },
    [activeId, runAsk, streaming],
  );

  /** Drop the last answer and ask the last question again. */
  const regenerate = useCallback(() => {
    if (!activeId || streaming) return;
    const conversation = conversationsRef.current.find((c) => c.id === activeId);
    if (!conversation) return;
    const reversedIndex = [...conversation.messages].reverse().findIndex((m) => m.role === "user");
    if (reversedIndex === -1) return;
    const index = conversation.messages.length - 1 - reversedIndex;
    void runAsk(
      activeId,
      conversation.messages[index].content,
      conversation.messages.slice(0, index),
    );
  }, [activeId, runAsk, streaming]);

  /** Edit a question and re-run the conversation from that point. */
  const editAndResend = useCallback(
    (messageId: string, newText: string) => {
      if (!activeId || streaming) return;
      const conversation = conversationsRef.current.find((c) => c.id === activeId);
      if (!conversation) return;
      const index = conversation.messages.findIndex((m) => m.id === messageId);
      if (index === -1) return;
      void runAsk(activeId, newText, conversation.messages.slice(0, index));
    },
    [activeId, runAsk, streaming],
  );

  // --- conversation management ---------------------------------------------

  const newConversation = useCallback(() => {
    const fresh = createConversation();
    setConversations((previous) => [fresh, ...previous]);
    setActiveId(fresh.id);
  }, []);

  const selectConversation = useCallback((id: string) => setActiveId(id), []);

  const renameConversation = useCallback(
    (id: string, title: string) => {
      const clean = title.trim();
      if (!clean) return;
      updateConversation(id, (c) => ({ ...c, title: clean, updatedAt: Date.now() }));
    },
    [updateConversation],
  );

  const deleteConversation = useCallback(
    (id: string) => {
      // Uploads belong to the conversation; dropping it drops them server-side
      // too. Omitting `filename` clears the whole conversation.
      void fetch(`${BASE}/api/documents?conversation_id=${encodeURIComponent(id)}`, {
        method: "DELETE",
      }).catch(() => undefined);

      setConversations((previous) => {
        const next = previous.filter((c) => c.id !== id);
        if (next.length === 0) {
          const fresh = createConversation();
          setActiveId(fresh.id);
          return [fresh];
        }
        if (id === activeId) setActiveId(next[0].id);
        return next;
      });
    },
    [activeId],
  );

  return {
    conversations,
    activeId,
    active,
    streaming,
    uploading,
    setUploading,
    toast,
    setToast,
    activeDocuments,
    uploadDocument,
    removeDocument,
    sendMessage,
    regenerate,
    editAndResend,
    selectConversation,
    newConversation,
    renameConversation,
    deleteConversation,
  };
}
