"use client";

/** API keys and active-model selection. */

import { useEffect, useState } from "react";
import { Model, ProviderStatus, api } from "@/lib/api";
import { Badge, Button, Card, Input, SectionTitle, Select } from "./ui";

const LABELS: Record<string, string> = {
  anthropic: "Anthropic (Claude)",
  openai: "OpenAI (GPT)",
  gemini: "Google Gemini",
};

export function Providers({
  models,
  activeId,
  onChanged,
}: {
  models: Model[];
  activeId: string | null;
  onChanged: () => void;
}) {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [provider, setProvider] = useState("anthropic");
  const [key, setKey] = useState("");
  const [note, setNote] = useState("");
  // `null` means "follow the active model"; a string is an explicit pick that
  // has not been applied yet. Derived rather than synced in an effect.
  const [picked, setPicked] = useState<string | null>(null);
  const selected = picked ?? activeId ?? "";

  useEffect(() => {
    api
      .providers()
      .then((data) => setProviders(data.providers))
      .catch(() => {});
  }, []);

  async function save() {
    if (!key.trim()) return;
    try {
      const data = await api.saveKey(provider, key);
      setProviders(data.providers);
      setKey(""); // never keep the key in a DOM value
      setNote(`✅ ${LABELS[provider] ?? provider} anahtarı kaydedildi.`);
      onChanged();
    } catch (error) {
      setNote(`❌ ${error instanceof Error ? error.message : error}`);
    }
  }

  async function activate() {
    try {
      const data = await api.setActiveModel(selected);
      setNote(
        data.priced
          ? `✅ Aktif model: ${selected}`
          : `✅ Aktif model: ${selected} — ⚠️ fiyat girilmedi, maliyet hesaplanmayacak.`,
      );
      onChanged();
    } catch (error) {
      setNote(`❌ ${error instanceof Error ? error.message : error}`);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <Card className="p-4">
        <SectionTitle>1 · API anahtarı</SectionTitle>
        <div className="flex flex-wrap items-end gap-2">
          <div className="w-52">
            <Select
              label="Sağlayıcı"
              value={provider}
              onChange={setProvider}
              options={Object.keys(LABELS).map((value) => ({
                value,
                label: LABELS[value],
              }))}
            />
          </div>
          <div className="min-w-52 flex-1">
            <Input
              label="Anahtar"
              type="password"
              value={key}
              onChange={setKey}
              placeholder="sk-…"
              onEnter={save}
            />
          </div>
          <Button variant="primary" onClick={save} disabled={!key.trim()}>
            Kaydet
          </Button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {providers.map((status) => (
            <Badge
              key={status.provider}
              tone={status.configured ? "ok" : "neutral"}
            >
              {LABELS[status.provider] ?? status.provider}
              {status.configured ? ` · ${status.masked}` : " · girilmedi"}
            </Badge>
          ))}
        </div>

        <p className="mt-3 text-[11px] text-[var(--text-dim)]">
          🔒 Anahtarlar yalnızca bu oturumun belleğinde tutulur — diske yazılmaz,
          log&apos;a düşmez, sekmeyi kapatınca silinir.
        </p>
      </Card>

      <Card className="p-4">
        <SectionTitle>2 · Aktif model</SectionTitle>
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-64 flex-1">
            <Select
              label="Soruları hangi model cevaplasın?"
              value={selected}
              onChange={setPicked}
              options={models.map((model) => ({
                value: model.id,
                label: `${model.label} · ${model.provider}${model.local ? " (yerel)" : ""}`,
              }))}
            />
          </div>
          <Button variant="primary" onClick={activate} disabled={!selected}>
            Kullan
          </Button>
        </div>
        {models.length === 0 && (
          <p className="mt-2 text-xs text-[var(--warn)]">
            Kullanılabilir model yok. Bir anahtar girin veya Ollama&apos;yı başlatın.
          </p>
        )}
      </Card>

      {note && <p className="text-sm">{note}</p>}
    </div>
  );
}
