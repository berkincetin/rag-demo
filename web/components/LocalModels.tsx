"use client";

/** Ollama models: list, pull, delete. */

import { useCallback, useEffect, useState } from "react";
import { OllamaModel, api } from "@/lib/api";
import { formatSize } from "@/lib/format";
import { Button, Card, Empty, Input, SectionTitle, Td, Th, TableWrap } from "./ui";

const SUGGESTED = ["qwen2.5:7b-instruct", "llama3.1:8b", "gemma2:9b", "qwen2.5:0.5b"];

export function LocalModels({ onChanged }: { onChanged: () => void }) {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [available, setAvailable] = useState(true);
  const [baseUrl, setBaseUrl] = useState("");
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.ollama();
      setModels(data.models);
      setAvailable(data.available);
      setBaseUrl(data.baseUrl);
    } catch (error) {
      setNote(`❌ ${error instanceof Error ? error.message : error}`);
    }
  }, []);

  useEffect(() => {
    // Server fetch on mount; state is set from the awaited response.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
  }, [refresh]);

  async function pull() {
    if (!name.trim()) return;
    setBusy(true);
    setNote(`⏳ ${name} indiriliyor — bu birkaç dakika sürebilir…`);
    try {
      await api.pullModel(name.trim());
      setNote(`✅ ${name} indirildi.`);
      setName("");
      await refresh();
      onChanged();
    } catch (error) {
      setNote(`❌ ${error instanceof Error ? error.message : error}`);
    } finally {
      setBusy(false);
    }
  }

  async function remove(target: string) {
    setConfirming(null);
    try {
      await api.deleteModel(target);
      setNote(`🗑️ ${target} silindi.`);
      await refresh();
      onChanged();
    } catch (error) {
      setNote(`❌ ${error instanceof Error ? error.message : error}`);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      {!available && (
        <Card className="border-[var(--danger)] p-3 text-sm text-[var(--danger)]">
          Ollama&apos;ya ulaşılamıyor (<span className="font-mono">{baseUrl}</span>).
        </Card>
      )}

      <Card className="p-4">
        <SectionTitle
          right={
            <Button variant="ghost" onClick={refresh}>
              Yenile
            </Button>
          }
        >
          Yüklü modeller ({models.length})
        </SectionTitle>
        {models.length === 0 ? (
          <Empty>Henüz model yok. Aşağıdan indirebilirsiniz.</Empty>
        ) : (
          <TableWrap>
            <table className="w-full">
              <thead>
                <tr>
                  <Th>Model</Th>
                  <Th>Boyut</Th>
                  <Th> </Th>
                </tr>
              </thead>
              <tbody>
                {models.map((model) => (
                  <tr key={model.name}>
                    <Td mono>{model.name}</Td>
                    <Td>{formatSize(model.sizeBytes)}</Td>
                    <Td>
                      {confirming === model.name ? (
                        <span className="flex gap-1">
                          <Button variant="danger" onClick={() => remove(model.name)}>
                            Evet, sil
                          </Button>
                          <Button variant="ghost" onClick={() => setConfirming(null)}>
                            Vazgeç
                          </Button>
                        </span>
                      ) : (
                        <Button variant="ghost" onClick={() => setConfirming(model.name)}>
                          Sil
                        </Button>
                      )}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableWrap>
        )}
      </Card>

      <Card className="p-4">
        <SectionTitle>Model indir</SectionTitle>
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-56 flex-1">
            <Input
              label="Model adı"
              value={name}
              onChange={setName}
              placeholder="qwen2.5:7b-instruct"
              onEnter={pull}
            />
          </div>
          <Button variant="primary" onClick={pull} disabled={busy || !name.trim()}>
            {busy ? "İndiriliyor…" : "İndir"}
          </Button>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {SUGGESTED.filter((s) => !models.some((m) => m.name === s)).map((s) => (
            <button
              key={s}
              onClick={() => setName(s)}
              className="rounded-md border px-2 py-1 font-mono text-[11px]
                text-[var(--text-dim)] transition hover:border-[var(--accent)]
                hover:text-[var(--text)]"
            >
              {s}
            </button>
          ))}
        </div>
        <p className="mt-3 text-[11px] text-[var(--text-dim)]">
          ⚠️ Modeller birkaç GB olabilir; indirme dakikalar sürer.
        </p>
      </Card>

      {note && <p className="text-sm">{note}</p>}
    </div>
  );
}
