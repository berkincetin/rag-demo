"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AnalysisBlocks from "@/components/AnalysisBlocks";
import analysisData from "@/lib/analysis.json";
import { sectionLinks, type AnalysisDocument } from "@/lib/analysis";
import { applyTheme, readStoredTheme } from "@/lib/theme";

const document_ = analysisData as AnalysisDocument;
const links = sectionLinks(document_);

/**
 * Bölüm 2 analizinin statik sunumu.
 *
 * Veri derleme anında `azure/scripts/export_analysis.py` ile üretilir, bu yüzden
 * sayfa hiçbir hesaplama yapmaz ve backend'e istek atmaz. Sohbetle aynı kabuğu
 * ve aynı renk paletini kullanır; `middleware.ts` matcher'ı `_next/static`
 * dışında her şeyi kapsadığı için bu sayfa da figürleri de giriş arkasındadır.
 */
export default function AnalysisPage() {
  const [activeId, setActiveId] = useState(links[0]?.href.slice(1) ?? "");
  const [menuOpen, setMenuOpen] = useState(false);

  // Bu ayrı bir rota: sohbette seçilen tema `<html>` sınıfıyla taşınmadığı için
  // burada yeniden uygulanır, yoksa koyu temadaki kullanıcı açık sayfaya düşer.
  useEffect(() => {
    applyTheme(readStoredTheme());
  }, []);

  // Okunan bölümü kenar çubuğunda işaretle. IntersectionObserver kaydırma
  // dinleyicisinden ucuz: tarayıcı kesişimi kendisi hesaplar.
  useEffect(() => {
    const headings = links
      .map((link) => window.document.getElementById(link.href.slice(1)))
      .filter((element): element is HTMLElement => element !== null);

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (visible) setActiveId(visible.target.id);
      },
      { rootMargin: "-80px 0px -70% 0px" },
    );

    headings.forEach((heading) => observer.observe(heading));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="flex h-dvh flex-col bg-[var(--bg)] text-[var(--text)]">
      <header
        className="flex shrink-0 items-center gap-3 border-b border-[var(--border)]
          bg-[var(--surface)] px-4 py-3"
      >
        <button
          onClick={() => setMenuOpen((value) => !value)}
          className="rounded-lg border border-[var(--border)] px-2 py-1 text-[12px]
            text-[var(--text-dim)] transition-colors hover:bg-[var(--surface-2)] lg:hidden"
          aria-label="Bölümler"
        >
          Bölümler
        </button>

        <div className="min-w-0 flex-1">
          <h1 className="truncate text-[14px] font-semibold">
            Bölüm 2 — İlaç Sektörü Satış ve Talep Analizi
          </h1>
          <p className="truncate text-[11px] text-[var(--text-dim)]">
            4 pazar · 124 ay · 7 analiz görevi — tüm sayılar notebook&apos;ta çalışan koddan
          </p>
        </div>

        <Link
          href="/"
          className="shrink-0 rounded-lg bg-[var(--accent)] px-3 py-1.5 text-[12px]
            font-medium text-[var(--accent-fg)] transition-opacity hover:opacity-90"
        >
          Sohbete dön
        </Link>
      </header>

      <div className="flex min-h-0 flex-1">
        <nav
          className={`${menuOpen ? "block" : "hidden"} w-64 shrink-0 overflow-y-auto
            border-r border-[var(--border)] bg-[var(--surface)] p-3 lg:block`}
        >
          <p className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-dim)]">
            Bölümler
          </p>
          {links.map((link) => {
            const isActive = link.href.slice(1) === activeId;
            return (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className={`block rounded-lg px-2 py-1.5 text-[12px] leading-snug transition-colors ${
                  isActive
                    ? "bg-[var(--accent-soft)] font-medium text-[var(--accent)]"
                    : "text-[var(--text-dim)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
                }`}
              >
                {link.label}
              </a>
            );
          })}
        </nav>

        <main className="min-w-0 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-5 py-6">
            {document_.sections.map((section) => (
              <section key={section.id} id={section.id} className="scroll-mt-4 pb-8">
                <h2
                  className="mb-3 border-b border-[var(--border)] pb-2 text-[16px]
                    font-semibold text-[var(--text)]"
                >
                  {section.title}
                </h2>
                <AnalysisBlocks blocks={section.blocks} />
              </section>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
