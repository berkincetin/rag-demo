"use client";

/**
 * App shell: persistent left rail, one view at a time.
 *
 * A rail rather than tabs because the active model belongs in view at all
 * times — it changes what every other screen does, and burying it in a tab is
 * what made the earlier layouts hard to follow.
 */

import { useCallback, useEffect, useState } from "react";
import { Chat } from "@/components/Chat";
import { Evaluation } from "@/components/Evaluation";
import { LocalModels } from "@/components/LocalModels";
import { Metrics } from "@/components/Metrics";
import { Providers } from "@/components/Providers";
import { Model, api } from "@/lib/api";
import { Badge } from "@/components/ui";

type View = "chat" | "providers" | "local" | "metrics" | "evaluation";

const NAV: { id: View; label: string; icon: string }[] = [
  { id: "chat", label: "Sohbet", icon: "💬" },
  { id: "providers", label: "Sağlayıcılar", icon: "🔑" },
  { id: "local", label: "Yerel Modeller", icon: "📦" },
  { id: "metrics", label: "Metrikler", icon: "📊" },
  { id: "evaluation", label: "Değerlendirme", icon: "🎯" },
];

export default function Home() {
  const [view, setView] = useState<View>("chat");
  const [models, setModels] = useState<Model[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  // Lazy initializer rather than an effect: reads the stored choice (falling
  // back to the OS preference) once, on mount, without a second render.
  const [dark, setDark] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    const stored = localStorage.getItem("rag-theme");
    if (stored) return stored === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  const refreshModels = useCallback(async () => {
    try {
      const data = await api.models();
      setModels(data.models);
      setActiveId(data.activeId);
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, []);

  useEffect(() => {
    // Server fetch on mount; state is set from the awaited response, which the
    // rule cannot distinguish from a synchronous set during the effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refreshModels();
  }, [refreshModels]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("rag-theme", dark ? "dark" : "light");
  }, [dark]);

  const active = models.find((model) => model.id === activeId);

  return (
    <div className="flex h-screen">
      <aside className="flex w-56 shrink-0 flex-col border-r bg-[var(--surface)]">
        <div className="flex items-center gap-2 px-4 py-4">
          <span className="text-lg">📚</span>
          <div className="leading-tight">
            <div className="text-sm font-semibold">Bilgi Asistanı</div>
            <div className="text-[10px] text-[var(--text-dim)]">RAG Agent</div>
          </div>
        </div>

        <nav className="flex flex-col gap-0.5 px-2">
          {NAV.map((item) => (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition
                ${
                  view === item.id
                    ? "bg-[var(--accent-soft)] font-medium text-[var(--accent)]"
                    : "text-[var(--text-dim)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
                }`}
            >
              <span>{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="mt-auto flex flex-col gap-2 p-3">
          <div className="rounded-lg bg-[var(--surface-2)] p-2.5">
            <div className="text-[10px] uppercase tracking-wide text-[var(--text-dim)]">
              Aktif model
            </div>
            {active ? (
              <>
                <div className="mt-0.5 break-all font-mono text-[11px]">{active.id}</div>
                <div className="mt-1">
                  <Badge tone={active.local ? "neutral" : "accent"}>
                    {active.local ? "🖥️ yerel" : `🤖 ${active.provider}`}
                  </Badge>
                </div>
              </>
            ) : (
              <div className="mt-1 text-[11px] text-[var(--warn)]">
                seçilmedi — Sağlayıcılar
              </div>
            )}
          </div>

          <button
            onClick={() => setDark((value) => !value)}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm
              text-[var(--text-dim)] transition hover:bg-[var(--surface-2)]
              hover:text-[var(--text)]"
          >
            {dark ? "☀️" : "🌙"} {dark ? "Açık tema" : "Koyu tema"}
          </button>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {offline && (
          <div className="bg-[var(--danger-soft)] px-4 py-2 text-sm text-[var(--danger)]">
            API&apos;ye ulaşılamıyor. <span className="font-mono">uvicorn src.rag.api:app
            --port 8000</span> çalışıyor mu?
          </div>
        )}
        {/* Chat manages its own scrolling (transcript scrolls, composer is
            pinned); the other views scroll as a whole page. */}
        <div
          className={`min-h-0 flex-1 p-4 ${
            view === "chat" ? "overflow-hidden" : "overflow-y-auto"
          }`}
        >
          {view === "chat" && <Chat activeModel={activeId} />}
          {view === "providers" && (
            <Providers models={models} activeId={activeId} onChanged={refreshModels} />
          )}
          {view === "local" && <LocalModels onChanged={refreshModels} />}
          {view === "metrics" && <Metrics />}
          {view === "evaluation" && <Evaluation models={models} />}
        </div>
      </main>
    </div>
  );
}
