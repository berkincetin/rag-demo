"use client";

/** Token, latency and cost history. */

import { useCallback, useEffect, useState } from "react";
import { ModelSummary, RunRecord, api } from "@/lib/api";
import {
  formatCost,
  formatGpu,
  formatInt,
  formatLatency,
  formatPercent,
  formatRam,
  formatRate,
} from "@/lib/format";
import { Badge, Button, Card, Empty, SectionTitle, TableWrap, Td, Th } from "./ui";

export function Metrics() {
  const [summaries, setSummaries] = useState<ModelSummary[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [confirming, setConfirming] = useState(false);

  const load = useCallback(async () => {
    const data = await api.metrics();
    setSummaries(data.summaries);
    setRuns(data.runs);
  }, []);

  useEffect(() => {
    // Server fetch on mount. State is set from the awaited response, not
    // synchronously during the effect — the rule cannot see past the await.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load().catch(() => {});
  }, [load]);

  async function wipe() {
    setConfirming(false);
    await api.clearMetrics();
    await load();
  }

  if (runs.length === 0) {
    return (
      <div className="mx-auto max-w-5xl">
        <Card className="p-4">
          <Empty>Henüz ölçüm yok. Sohbet sekmesinden bir soru sorun.</Empty>
          <Button variant="ghost" onClick={load}>
            Yenile
          </Button>
        </Card>
      </div>
    );
  }

  const slowest = Math.max(...summaries.map((s) => s.avgLatencyMs), 1);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <Card className="p-4">
        <SectionTitle
          right={
            <span className="flex gap-1">
              <Button variant="ghost" onClick={load}>
                Yenile
              </Button>
              {confirming ? (
                <>
                  <Button variant="danger" onClick={wipe}>
                    Evet, sil
                  </Button>
                  <Button variant="ghost" onClick={() => setConfirming(false)}>
                    Vazgeç
                  </Button>
                </>
              ) : (
                <Button variant="ghost" onClick={() => setConfirming(true)}>
                  Geçmişi temizle
                </Button>
              )}
            </span>
          }
        >
          Model karşılaştırması
        </SectionTitle>

        {/* Latency bars: the comparison the demo is actually about — local vs
            cloud — reads instantly here and not from a number column. */}
        <div className="mb-4 flex flex-col gap-2">
          {summaries.map((summary) => (
            <div key={summary.modelId} className="flex items-center gap-2">
              <span className="w-56 shrink-0 truncate font-mono text-[11px]">
                {summary.modelId}
              </span>
              <div className="h-4 flex-1 overflow-hidden rounded bg-[var(--surface-2)]">
                <div
                  className="h-full rounded bg-[var(--accent)] transition-all"
                  style={{ width: `${(summary.avgLatencyMs / slowest) * 100}%` }}
                />
              </div>
              <span className="w-20 shrink-0 text-right text-[11px] text-[var(--text-dim)]">
                {formatLatency(summary.avgLatencyMs)}
              </span>
            </div>
          ))}
        </div>

        <TableWrap>
          <table className="w-full">
            <thead>
              <tr>
                <Th>Model</Th>
                <Th>Koşu</Th>
                <Th>Ort. süre</Th>
                <Th>Giriş tk</Th>
                <Th>Çıkış tk</Th>
                <Th>Ort. atıf</Th>
                <Th>Kapı</Th>
                <Th>Maliyet</Th>
              </tr>
            </thead>
            <tbody>
              {summaries.map((summary) => (
                <tr key={summary.modelId}>
                  <Td mono>{summary.modelId}</Td>
                  <Td>{summary.runs}</Td>
                  <Td>{formatLatency(summary.avgLatencyMs)}</Td>
                  <Td>{formatInt(summary.totalInputTokens)}</Td>
                  <Td>{formatInt(summary.totalOutputTokens)}</Td>
                  <Td>{summary.avgCitations.toFixed(1).replace(".", ",")}</Td>
                  <Td>{formatRate(summary.gatePassRate)}</Td>
                  <Td>
                    {formatCost(summary.totalCostUsd)}
                    {summary.totalCostUsd !== null &&
                      summary.pricedRuns < summary.runs && (
                        <span className="ml-1 text-[11px] text-[var(--warn)]">
                          ({summary.pricedRuns}/{summary.runs} koşu)
                        </span>
                      )}
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
      </Card>

      <Card className="p-4">
        <SectionTitle>Son koşular ({runs.length})</SectionTitle>
        <TableWrap>
          <table className="w-full">
            <thead>
              <tr>
                <Th>Zaman</Th>
                <Th>Model</Th>
                <Th>Soru</Th>
                <Th>Süre</Th>
                <Th>Giriş</Th>
                <Th>Çıkış</Th>
                <Th>CPU</Th>
                <Th>RAM</Th>
                <Th>GPU</Th>
                <Th>Maliyet</Th>
                <Th>Atıf</Th>
                <Th>Kapı</Th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run, index) => (
                <tr key={index}>
                  <Td mono>{run.ts?.slice(0, 19).replace("T", " ") ?? "—"}</Td>
                  <Td mono>{run.modelId}</Td>
                  <Td>
                    <span className="block max-w-64 truncate" title={run.question}>
                      {run.question}
                    </span>
                  </Td>
                  <Td>{formatLatency(run.latencyMs)}</Td>
                  <Td>{formatInt(run.inputTokens)}</Td>
                  <Td>{formatInt(run.outputTokens)}</Td>
                  <Td>{formatPercent(run.peakCpuPercent)}</Td>
                  <Td>{formatRam(run.peakRamMb)}</Td>
                  <Td>{formatGpu(run.gpuVramMb)}</Td>
                  <Td>{formatCost(run.costUsd)}</Td>
                  <Td>{run.citationCount}</Td>
                  <Td>
                    <Badge tone={run.gatePassed ? "ok" : "warn"}>
                      {run.gatePassed ? "geçti" : "reddedildi"}
                    </Badge>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableWrap>
        <p className="mt-3 text-[11px] text-[var(--text-dim)]">
          ℹ️ Sorular ölçüm veritabanına kaydedilir. Gerçek bir dağıtımda bu kişisel
          veri içerebilir.
        </p>
      </Card>
    </div>
  );
}
