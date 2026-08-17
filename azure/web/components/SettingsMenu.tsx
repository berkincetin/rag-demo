"use client";

import { useEffect, useRef, useState } from "react";

import { MODEL_OPTIONS, readStoredModel, storeModel } from "@/lib/settings";

type Unavailable = { id: string; label: string; reason: string };

/**
 * Model seçimi.
 *
 * Seçim tarayıcıda saklanıyor ve her soruyla gönderiliyor; sunucu onu yine de
 * kendi kataloğuna karşı doğruluyor. Kotası olmayan modeller sunucudan
 * `unavailable` altında sebebiyle geliyor ve burada devre dışı gösteriliyor —
 * sessizce başarısız olan bir seçenek bırakılmıyor.
 */
export default function SettingsMenu({ collapsed }: { collapsed: boolean }) {
  const [open, setOpen] = useState(false);
  // Lazy initializer, effect değil: kaydedilmiş seçim tek seferde, ikinci bir
  // render olmadan okunur. Sunucuda `readStoredModel` varsayılanı döndürür.
  const [selected, setSelected] = useState<string>(readStoredModel);
  const [unavailable, setUnavailable] = useState<Unavailable[]>([]);
  const [warnings, setWarnings] = useState<Record<string, string>>({});
  const panelRef = useRef<HTMLDivElement>(null);

  // Kotasızların listesi sunucunun bildiği bir şey; sabit kodlanırsa kota
  // açıldığında arayüz yanlış bilgi vermeye devam eder.
  useEffect(() => {
    if (!open || unavailable.length > 0) return;
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch("/api/proxy/api/models");
        if (!response.ok) return;
        const data = await response.json();
        if (cancelled) return;
        setUnavailable(data.unavailable ?? []);
        setWarnings(data.warnings ?? {});
      } catch {
        // Menü dağıtılmış modellerle çalışmaya devam eder.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, unavailable.length]);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!panelRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function choose(id: string) {
    setSelected(id);
    storeModel(id);
    setOpen(false);
  }

  const activeLabel =
    MODEL_OPTIONS.find((option) => option.id === selected)?.label ?? MODEL_OPTIONS[0].label;

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setOpen((value) => !value)}
        title={`Model: ${activeLabel}`}
        className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm
          text-[var(--text-dim)] transition-colors hover:bg-[var(--surface-2)]
          hover:text-[var(--text)] ${collapsed ? "justify-center px-0" : ""}`}
      >
        ⚙️ {!collapsed && <span className="truncate">{activeLabel}</span>}
      </button>

      {open && (
        <div
          className="absolute bottom-full left-0 z-20 mb-1 w-72 rounded-xl border
            border-[var(--border)] bg-[var(--surface)] p-2 shadow-[var(--shadow)]"
        >
          <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-dim)]">
            Sohbet modeli
          </p>

          {MODEL_OPTIONS.map((option) => (
            <button
              key={option.id}
              onClick={() => choose(option.id)}
              className={`block w-full rounded-lg px-2 py-1.5 text-left transition-colors ${
                option.id === selected
                  ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                  : "text-[var(--text)] hover:bg-[var(--surface-2)]"
              }`}
            >
              <span className="block text-[12px] font-medium">{option.label}</span>
              <span className="block text-[10px] leading-snug text-[var(--text-dim)]">
                {option.note}
              </span>
              {warnings[option.id] && (
                <span className="mt-0.5 block text-[10px] leading-snug text-[var(--warn)]">
                  ⚠ {warnings[option.id]}
                </span>
              )}
            </button>
          ))}

          {unavailable.length > 0 && (
            <>
              <p className="mt-2 px-2 pb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-dim)]">
                Kullanılamıyor
              </p>
              {unavailable.map((model) => (
                <div
                  key={model.id}
                  className="cursor-not-allowed rounded-lg px-2 py-1.5 opacity-55"
                  title={model.reason}
                >
                  <span className="block text-[12px] text-[var(--text-dim)] line-through">
                    {model.label}
                  </span>
                  <span className="block text-[10px] leading-snug text-[var(--text-dim)]">
                    {model.reason}
                  </span>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
