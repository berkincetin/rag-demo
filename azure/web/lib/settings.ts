/**
 * Model tercihi — tarayıcı genelinde, her istekle gönderilir.
 *
 * Buradaki liste sunucudaki katalogla eşleşir ama onun yerine geçmez: sunucu
 * gelen seçimi kendi kataloğuna karşı yeniden doğrular ve tanımadığını 400 ile
 * reddeder. Bu dosyanın işi menüyü çizmek ve geçersiz bir değerin hiç
 * gönderilmemesini sağlamak.
 *
 * Kotası olmayan modeller (Cohere ailesi, üçüncü embedding) burada yok:
 * sunucu onları `unavailable` altında sebebiyle bildiriyor ve menü listeyi
 * oradan zenginleştiriyor.
 */

export const MODEL_KEY = "rag-model";
export const DEFAULT_MODEL_ID = "gpt-4.1-mini";

export type ModelOption = {
  id: string;
  label: string;
  note: string;
};

/** Dağıtılmış ve seçilebilir modeller, menüdeki sırayla. */
export const MODEL_OPTIONS: ModelOption[] = [
  {
    id: "gpt-4.1-mini",
    label: "GPT-4.1 mini",
    note: "Varsayılan — kapı eşikleri bu modelle kalibre edildi",
  },
  {
    id: "gpt-5-mini",
    label: "GPT-5 mini",
    note: "Alternatif — akıl yürütme adımı için geniş token bütçesi",
  },
  {
    id: "Phi-4-mini-instruct",
    label: "Phi-4 mini instruct",
    note: "Bütçe — küçük model, araç çağırdığı ölçüldü",
  },
];

const VALID_IDS = new Set(MODEL_OPTIONS.map((option) => option.id));

export function isKnownModel(id: string | null | undefined): boolean {
  return typeof id === "string" && VALID_IDS.has(id);
}

/** Kaydedilmiş seçim; yoksa ya da artık geçerli değilse varsayılan. */
export function readStoredModel(): string {
  if (typeof window === "undefined") return DEFAULT_MODEL_ID;
  const stored = localStorage.getItem(MODEL_KEY);
  return isKnownModel(stored) ? (stored as string) : DEFAULT_MODEL_ID;
}

/** Seçimi kalıcılaştırır. Tanınmayan bir değer sessizce yok sayılır. */
export function storeModel(id: string): void {
  if (typeof window === "undefined" || !isKnownModel(id)) return;
  localStorage.setItem(MODEL_KEY, id);
}

export type AskBodyInput = {
  question: string;
  conversationId: string;
  summary: string;
  history: { role: string; content: string }[];
};

/**
 * `/api/ask/stream` gövdesi.
 *
 * Model seçimi burada tek yerden ekleniyor. Çağıran tarafın `readStoredModel()`
 * çağırıp alanı elle koyması gerekseydi, ikinci bir çağrı yeri eklendiğinde
 * sessizce unutulur ve o yol her zaman varsayılan modelle çalışırdı.
 */
export function buildAskBody(input: AskBodyInput) {
  return { ...input, modelId: readStoredModel() };
}
