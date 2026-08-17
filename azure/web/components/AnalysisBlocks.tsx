"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type {
  AnalysisBlock,
  CodeBlock,
  FigureBlock,
  StreamBlock,
  TableBlock,
} from "@/lib/analysis";

/**
 * Matplotlib figürleri beyaz zeminli üretildi. Koyu temada sayfaya doğrudan
 * konursa göz alır, o yüzden her iki temada da beyaz bir kart içinde durur.
 */
function Figure({ block }: { block: FigureBlock }) {
  return (
    <figure className="my-4 overflow-x-auto rounded-xl border border-[var(--border)] bg-white p-3">
      {/* eslint-disable-next-line @next/next/no-img-element -- derleme anında
          üretilen statik PNG; next/image'in optimizasyonu burada iş görmez */}
      <img src={block.src} alt={block.alt} className="mx-auto block max-w-full" />
    </figure>
  );
}

/** Geniş tablolar sayfayı yatay kaydırmaz; kendi kabında kaydırır. */
function Table({ block }: { block: TableBlock }) {
  return (
    <div className="my-4 overflow-x-auto rounded-xl border border-[var(--border)]">
      <table className="w-full border-collapse text-left text-[12px]">
        <thead>
          <tr className="bg-[var(--surface-2)]">
            {block.headers.map((header, index) => (
              <th
                key={index}
                className="whitespace-nowrap border-b border-[var(--border)] px-3 py-2
                  font-semibold text-[var(--text)]"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="even:bg-[var(--surface-2)]/40">
              {row.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className="whitespace-nowrap border-b border-[var(--border)] px-3 py-1.5
                    text-[var(--text-dim)] last:border-b-0"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Kod katlanabilir: değerlendiren doğrulayabilsin, okuyan boğulmasın. */
function Code({ block }: { block: CodeBlock }) {
  const [open, setOpen] = useState(false);
  const lineCount = block.source.split("\n").length;

  return (
    <div className="my-3">
      <button
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-1.5 rounded px-1 py-0.5 text-[11px] text-[var(--text-dim)]
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
        {open ? "Kodu gizle" : `Kodu göster (${lineCount} satır)`}
      </button>

      {open && (
        <pre
          className="mt-1.5 overflow-x-auto rounded-xl border border-[var(--border)]
            bg-[var(--surface-2)] px-3 py-2.5 text-[11px] leading-relaxed text-[var(--text)]"
        >
          <code>{block.source}</code>
        </pre>
      )}
    </div>
  );
}

/** `print()` çıktısı — hizalama anlam taşıdığı için önbiçimli kalır. */
function Stream({ block }: { block: StreamBlock }) {
  return (
    <pre
      className="my-3 overflow-x-auto rounded-xl border border-[var(--border)]
        bg-[var(--surface-2)] px-3 py-2.5 text-[11px] leading-relaxed text-[var(--text-dim)]"
    >
      {block.text}
    </pre>
  );
}

export default function AnalysisBlocks({ blocks }: { blocks: AnalysisBlock[] }) {
  return (
    <>
      {blocks.map((block, index) => {
        switch (block.type) {
          case "narrative":
            return (
              <div key={index} className="analysis-prose">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.markdown}</ReactMarkdown>
              </div>
            );
          case "table":
            return <Table key={index} block={block} />;
          case "figure":
            return <Figure key={index} block={block} />;
          case "code":
            return <Code key={index} block={block} />;
          case "stream":
            return <Stream key={index} block={block} />;
        }
      })}
    </>
  );
}
