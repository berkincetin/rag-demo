"use client";

/** Compare models on the fixed 13-question set. */

import { useEffect, useState } from "react";
import { EvalRow, Model, api } from "@/lib/api";
import { formatCost, formatLatency, formatRate } from "@/lib/format";
import { Badge, Button, Card, SectionTitle, TableWrap, Td, Th } from "./ui";

export function Evaluation({ models }: { models: Model[] }) {
  const [selected, setSelected] = useState<string[]>([]);
  const [cases, setCases] = useState(0);
  const [estimate, setEstimate] = useState<{
    knownCostUsd: number;
    unpricedModels: string[];
  } | null>(null);
  const [consented, setConsented] = useState(false);
  const [busy, setBusy] = useState(false);
  const [rows, setRows] = useState<EvalRow[]>([]);
  const [note, setNote] = useState("");

  useEffect(() => {
    // Server fetch on mount; state is set from the awaited response.
    api
      .evalCases()
      .then((data) => setCases(data.count))
      .catch(() => {});
  }, []);

  // The estimate is fetched when the selection changes rather than in an
  // effect, so clearing it stays a plain event-handler update.
  function toggle(id: string) {
    const next = selected.includes(id)
      ? selected.filter((value) => value !== id)
      : [...selected, id];
    setSelected(next);
    if (next.length === 0) {
      setEstimate(null);
      return;
    }
    api.evalEstimate(next).then(setEstimate).catch(() => {});
  }

  async function run() {
    setBusy(true);
    setNote(`⏳ ${selected.length} model × ${cases} soru çalışıyor — dakikalar sürebilir…`);
    try {
      const data = await api.runEvaluation(selected);
      setRows(data.results);
      setNote(`✅ ${data.results.length} model değerlendirildi.`);
    } catch (error) {
      setNote(`❌ ${error instanceof Error ? error.message : error}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <Card className="p-4">
        <SectionTitle>Karşılaştırılacak modeller</SectionTitle>
        <p className="mb-3 text-xs text-[var(--text-dim)]">
          {cases} soruluk sabit set: atıf oranı, kaynak isabeti, kanıt isabeti ve
          konu dışı red isabeti ölçülür. Cevabın üslubu <b>puanlanmaz</b>.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {models.map((model) => (
            <button
              key={model.id}
              onClick={() => toggle(model.id)}
              className={`rounded-lg border px-2.5 py-1.5 font-mono text-[11px] transition
                ${
                  selected.includes(model.id)
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "hover:border-[var(--accent)]"
                }`}
            >
              {model.id}
            </button>
          ))}
        </div>

        {estimate && (
          <div className="mt-3 rounded-lg bg-[var(--surface-2)] p-3 text-xs">
            <div>
              Tahmini maliyet (<b>yaklaşık, ±%50</b>):{" "}
              {formatCost(estimate.knownCostUsd)} · {selected.length} model × {cases} soru
            </div>
            {estimate.unpricedModels.length > 0 && (
              <div className="mt-1 text-[var(--warn)]">
                ⚠️ Fiyatı bilinmeyen: {estimate.unpricedModels.join(", ")} — maliyet eksik.
              </div>
            )}
            <div className="mt-1 text-[var(--warn)]">
              ⚠️ Bu işlem dakikalar sürer ve bulut modellerinde ücretlidir.
            </div>
          </div>
        )}

        <label className="mt-3 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={consented}
            onChange={(event) => setConsented(event.target.checked)}
            className="h-4 w-4 accent-[var(--accent)]"
          />
          Maliyeti ve süreyi anladım
        </label>

        <div className="mt-3">
          <Button
            variant="primary"
            onClick={run}
            disabled={busy || !consented || selected.length === 0}
          >
            {busy ? "Çalışıyor…" : "Değerlendirmeyi başlat"}
          </Button>
        </div>
        {note && <p className="mt-2 text-sm">{note}</p>}
      </Card>

      {rows.length > 0 && (
        <Card className="p-4">
          <SectionTitle>Sonuç</SectionTitle>
          <TableWrap>
            <table className="w-full">
              <thead>
                <tr>
                  <Th>Model</Th>
                  <Th>Atıf oranı</Th>
                  <Th>Kaynak isabeti</Th>
                  <Th>Kanıt isabeti</Th>
                  <Th>Red isabeti</Th>
                  <Th>Ort. süre</Th>
                  <Th>Maliyet</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={row.modelId}>
                    <Td mono>
                      <span className="flex items-center gap-2">
                        {row.modelId}
                        {index === 0 && <Badge tone="ok">en iyi</Badge>}
                      </span>
                    </Td>
                    <Td>{formatRate(row.citationRate)}</Td>
                    <Td>{formatRate(row.sourceAccuracy)}</Td>
                    <Td>{formatRate(row.evidenceHit)}</Td>
                    <Td>{formatRate(row.refusalAccuracy)}</Td>
                    <Td>{formatLatency(row.avgLatencyMs)}</Td>
                    <Td>{formatCost(row.totalCostUsd)}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        </Card>
      )}
    </div>
  );
}
