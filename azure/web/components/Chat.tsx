"use client";

/**
 * Chat view.
 *
 * The design rule here, learned the hard way in the Gradio build: everything
 * about an answer belongs *to that answer*. Sources, tool calls and cost are
 * rendered inside the assistant message bubble, not in a side panel or a strip
 * below the composer — so scrolling back to an older answer still shows what
 * backed it.
 */

import { useEffect, useRef, useState } from "react";
import { Answer, api } from "@/lib/api";
import {
  formatCost,
  formatGpu,
  formatLatency,
  formatRam,
  formatTokens,
  splitCitation,
} from "@/lib/format";
import { Badge, Button, Card, Input } from "./ui";

type Turn = {
  question: string;
  answer: Answer | null;
  error?: string;
};

const EXAMPLES = [
  { label: "Yıllık izin", q: "Yıllık izin talebimi nasıl yaparım?", tag: "XLSX" },
  {
    label: "Yakıt limiti",
    q: "Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?",
    tag: "DOCX tablosu",
  },
  {
    label: "Aksef kontrendikasyon",
    q: "Aksef 500 mg'ın kontrendikasyonları nelerdir?",
    tag: "PDF",
  },
  { label: "Vitatin95", q: "Vitatin95 ürününün ürün müdürü kim?", tag: "XLSX" },
  { label: "Konu dışı", q: "Bugün hava nasıl olacak?", tag: "reddetmeli" },
];

export function Chat({ activeModel }: { activeModel: string | null }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [userName, setUserName] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, busy]);

  async function send(question: string) {
    const trimmed = question.trim();
    if (!trimmed || busy) return;
    setDraft("");
    setBusy(true);
    setTurns((prev) => [...prev, { question: trimmed, answer: null }]);
    try {
      const answer = await api.ask(trimmed, userName);
      setTurns((prev) =>
        prev.map((turn, index) =>
          index === prev.length - 1 ? { ...turn, answer } : turn,
        ),
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setTurns((prev) =>
        prev.map((turn, index) =>
          index === prev.length - 1 ? { ...turn, error: message } : turn,
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    await api.clearChat();
    setTurns([]);
  }

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        {turns.length === 0 && !busy ? (
          <Welcome onPick={send} />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-5 pb-2">
            {turns.map((turn, index) => (
              <TurnView key={index} turn={turn} />
            ))}
            {busy && <Thinking />}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="mx-auto w-full max-w-3xl">
        <Card className="p-2">
          <div className="flex items-end gap-2">
            <textarea
              value={draft}
              rows={1}
              disabled={busy}
              placeholder={
                activeModel ? "Belgeler hakkında sorun…" : "Önce bir model seçin…"
              }
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  send(draft);
                }
              }}
              className="max-h-40 min-h-[38px] flex-1 resize-none bg-transparent px-2 py-2
                text-sm outline-none placeholder:text-[var(--text-dim)]"
            />
            <Button
              variant="primary"
              onClick={() => send(draft)}
              disabled={busy || !draft.trim()}
            >
              {busy ? "Yanıtlanıyor…" : "Gönder"}
            </Button>
          </div>
        </Card>

        <div className="mt-2 flex flex-wrap items-center gap-2">
          <div className="w-44">
            <Input
              value={userName}
              onChange={setUserName}
              placeholder="Adınız (isteğe bağlı)"
            />
          </div>
          <span className="text-[11px] text-[var(--text-dim)]">
            Model son 5 turu hatırlar · reddedilen cevaplar belleğe girmez
          </span>
          <div className="ml-auto">
            <Button variant="ghost" onClick={reset} disabled={!turns.length}>
              Sohbeti temizle
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Welcome({ onPick }: { onPick: (question: string) => void }) {
  return (
    <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center gap-6 py-10">
      <div className="text-center">
        <div className="text-3xl">📚</div>
        <h2 className="mt-3 text-lg font-semibold">Şirket Bilgi Asistanı</h2>
        <p className="mt-1 text-sm text-[var(--text-dim)]">
          Altı belge üzerinde soru sorun. Her cevap kaynağıyla birlikte gelir;
          belgede olmayanı uydurmaz.
        </p>
      </div>
      <div className="grid w-full gap-2 sm:grid-cols-2">
        {EXAMPLES.map((example) => (
          <button
            key={example.q}
            onClick={() => onPick(example.q)}
            className="group rounded-xl border bg-[var(--surface)] p-3 text-left
              transition hover:border-[var(--accent)] hover:shadow-[var(--shadow)]"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium">{example.label}</span>
              <Badge tone="neutral">{example.tag}</Badge>
            </div>
            <span className="mt-1 block text-xs text-[var(--text-dim)]">
              {example.q}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Thinking() {
  return (
    <div className="animate-rise flex items-center gap-2 text-sm text-[var(--text-dim)]">
      <span className="dot h-1.5 w-1.5 rounded-full bg-current" />
      <span className="dot h-1.5 w-1.5 rounded-full bg-current [animation-delay:.15s]" />
      <span className="dot h-1.5 w-1.5 rounded-full bg-current [animation-delay:.3s]" />
      <span className="ml-1">Belgeler taranıyor…</span>
    </div>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  return (
    <div className="animate-rise flex flex-col gap-3">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-[var(--accent)]
          px-3.5 py-2 text-sm text-[var(--accent-fg)]">
          {turn.question}
        </div>
      </div>

      {turn.error && (
        <Card className="border-[var(--danger)] p-3 text-sm text-[var(--danger)]">
          {turn.error}
        </Card>
      )}

      {turn.answer && <AnswerView answer={turn.answer} />}
    </div>
  );
}

function AnswerView({ answer }: { answer: Answer }) {
  const [showTrace, setShowTrace] = useState(false);

  return (
    <Card className="overflow-hidden">
      <div className="whitespace-pre-wrap px-4 py-3 text-sm leading-relaxed">
        {answer.text}
      </div>

      {answer.grounded ? (
        <div className="border-t bg-[var(--surface-2)] px-4 py-2.5">
          <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide
            text-[var(--text-dim)]">
            Kaynaklar
          </div>
          <ol className="flex flex-col gap-1">
            {answer.citations.map((citation, index) => {
              const { file, where } = splitCitation(citation);
              return (
                <li key={index} className="flex items-baseline gap-2 text-xs">
                  <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center
                    rounded bg-[var(--accent-soft)] text-[10px] font-semibold
                    text-[var(--accent)]">
                    {index + 1}
                  </span>
                  <span className="font-medium">{file}</span>
                  {where && (
                    <span className="text-[var(--text-dim)]">{where}</span>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      ) : (
        <div className="border-t bg-[var(--warn-soft)] px-4 py-2 text-xs text-[var(--warn)]">
          Kaynak gösterilmedi — bu bir ret ya da &quot;bilgim yok&quot; yanıtı.
        </div>
      )}

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t px-4 py-2
        text-[11px] text-[var(--text-dim)]">
        <span className="font-mono">{answer.modelId}</span>
        <span>{formatLatency(answer.latencyMs)}</span>
        <span>{formatTokens(answer.inputTokens, answer.outputTokens)}</span>
        <span>{formatCost(answer.costUsd)}</span>
        {answer.toolTrace.length > 0 && (
          <button
            onClick={() => setShowTrace((value) => !value)}
            className="ml-auto underline underline-offset-2 hover:text-[var(--text)]"
          >
            {showTrace ? "Araç izini gizle" : `Araç izi (${answer.toolTrace.length})`}
          </button>
        )}
      </div>

      {showTrace && (
        <div className="border-t px-4 py-2">
          {answer.toolTrace.map((call, index) => (
            <div key={index} className="py-1 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-mono font-medium">{call.name}</span>
                <Badge tone={call.injected ? "warn" : "ok"}>
                  {call.injected ? "otomatik" : "model seçti"}
                </Badge>
                <span className="text-[var(--text-dim)]">
                  {call.chars.toLocaleString("tr-TR")} karakter
                </span>
              </div>
              <pre className="mt-1 overflow-x-auto rounded bg-[var(--surface-2)] p-2
                font-mono text-[11px] text-[var(--text-dim)]">
                {JSON.stringify(call.arguments, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
