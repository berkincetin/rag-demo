"use client";

/**
 * App shell: conversation rail on the left, transcript and composer on the right.
 *
 * Reduced from the local build. The Providers, Local Models and Evaluation
 * views are gone: this deployment talks to one server-held Azure model, so
 * there is no key to enter and no model to pull, and running the evaluation
 * suite from a browser is a cost-amplification path against the Azure quota.
 */

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import ChatPane from "@/components/ChatPane";
import Composer from "@/components/Composer";
import Sidebar from "@/components/Sidebar";
import { STORAGE_KEY } from "@/lib/storage";
import { applyTheme, readStoredTheme } from "@/lib/theme";
import { useConversations } from "@/lib/useConversations";

export default function Home() {
  const router = useRouter();
  const {
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
  } = useConversations();

  const [collapsed, setCollapsed] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Lazy initializer rather than an effect: reads the stored choice (falling
  // back to the OS preference) once, on mount, without a second render.
  const [dark, setDark] = useState<boolean>(readStoredTheme);

  useEffect(() => {
    applyTheme(dark);
  }, [dark]);

  async function handleFiles(files: FileList) {
    setUploading(true);
    const errors: string[] = [];
    for (const file of Array.from(files)) {
      const error = await uploadDocument(file);
      if (error) errors.push(`${file.name}: ${error}`);
    }
    setUploading(false);

    if (errors.length > 0) {
      setToast(errors[0]);
    } else {
      setToast(
        files.length === 1 ? `${files[0].name} yüklendi` : `${files.length} doküman yüklendi`,
      );
    }
  }

  async function signOut() {
    // Conversations live in this browser, so signing out must clear them —
    // otherwise the next person at this machine reads the previous session.
    localStorage.removeItem(STORAGE_KEY);
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  let placeholder = "Sorunuzu yazın";
  if (streaming) placeholder = "Cevap yazılıyor…";

  return (
    <div
      className="flex h-screen overflow-hidden"
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(event) => {
        // Only clear when the pointer truly left the window.
        if (event.currentTarget.contains(event.relatedTarget as Node)) return;
        setDragging(false);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        const files = event.dataTransfer.files;
        if (files && files.length > 0) void handleFiles(files);
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.xlsx,.txt"
        multiple
        className="hidden"
        onChange={(event) => {
          const files = event.target.files;
          if (files && files.length > 0) void handleFiles(files);
          event.target.value = "";
        }}
      />

      <Sidebar
        conversations={conversations}
        activeId={activeId}
        collapsed={collapsed}
        dark={dark}
        onToggleCollapse={() => setCollapsed((value) => !value)}
        onToggleTheme={() => setDark((value) => !value)}
        onSelect={selectConversation}
        onNew={newConversation}
        onRename={renameConversation}
        onDelete={deleteConversation}
        onSignOut={signOut}
      />

      <main className="relative flex min-w-0 flex-1 flex-col">
        <ChatPane
          messages={active?.messages ?? []}
          streaming={streaming}
          onRegenerate={regenerate}
          onEdit={editAndResend}
          onPickFile={() => fileInputRef.current?.click()}
          documentCount={activeDocuments.length}
          uploading={uploading}
        />

        <Composer
          onSend={sendMessage}
          disabled={streaming}
          placeholder={placeholder}
          documents={activeDocuments}
          onPickFile={() => fileInputRef.current?.click()}
          onRemoveDocument={removeDocument}
          uploading={uploading}
        />

        {dragging && (
          <div
            className="pointer-events-none absolute inset-0 z-40 flex items-center justify-center
              border-2 border-dashed border-[var(--accent)] bg-[var(--accent-soft)]/60"
          >
            <p
              className="rounded-xl bg-[var(--surface)] px-4 py-2 text-sm font-medium
                text-[var(--text)] shadow-lg"
            >
              Dokümanları buraya bırakın
            </p>
          </div>
        )}
      </main>

      {toast && (
        <div
          className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 animate-rise rounded-xl
            border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--text)]
            shadow-lg"
        >
          {toast}
        </div>
      )}
    </div>
  );
}
