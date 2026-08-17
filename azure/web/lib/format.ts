/**
 * Turkish display formatting.
 *
 * Mirrors `src/rag/ui_state.py`: a value that was never measured is labelled,
 * never rendered as zero. "$0,0000" for an unpriced model would be a lie, and
 * "—" for a rate with no applicable cases keeps it out of comparisons.
 */

const tr = (value: number, decimals: number) =>
  value.toFixed(decimals).replace(".", ",");

export function formatLatency(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${tr(ms / 1000, 1)} sn`;
}

export function formatCost(usd: number | null): string {
  return usd === null ? "fiyat girilmedi" : `$${tr(usd, 4)}`;
}

export function formatRate(rate: number | null): string {
  return rate === null ? "—" : `%${Math.round(rate * 100)}`;
}

export function formatPercent(value: number | null): string {
  return value === null ? "—" : `%${value.toFixed(0)}`;
}

export function formatRam(mb: number | null): string {
  if (mb === null) return "—";
  return mb >= 1024 ? `${tr(mb / 1024, 1)} GB` : `${mb} MB`;
}

/** `null` = could not measure; `0` = loaded but running on the CPU. */
export function formatGpu(vramMb: number | null): string {
  if (vramMb === null) return "ölçülmedi";
  if (vramMb === 0) return "CPU'da";
  return `${tr(vramMb / 1024, 1)} GB VRAM`;
}

export function formatSize(bytes: number | null): string {
  if (bytes === null) return "boyut bilinmiyor";
  // Decimal units, matching what `ollama list` prints.
  if (bytes >= 1_000_000_000) return `${tr(bytes / 1_000_000_000, 1)} GB`;
  return `${tr(bytes / 1_000_000, 1)} MB`;
}

export function formatTokens(input: number | null, output: number | null): string {
  if (input === null) return "token ölçülmedi";
  return `↑${input.toLocaleString("tr-TR")} / ↓${(output ?? 0).toLocaleString("tr-TR")}`;
}

export function formatInt(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("tr-TR");
}

/** Split "dosya.docx — Bölüm 3, s.4" into its file and location halves. */
export function splitCitation(citation: string): { file: string; where: string } {
  const [file, ...rest] = citation.split("—");
  return { file: file.trim(), where: rest.join("—").trim() };
}
