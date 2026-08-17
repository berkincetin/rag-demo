/**
 * Model tercihi: okuma, doğrulama ve kalıcılık.
 *
 * Tercih tarayıcıda saklanıyor ve her istekle gönderiliyor. Sunucu onu yine de
 * kataloğa karşı doğruluyor — buradaki testler istemcinin *geçerli* bir değer
 * göndermesini sabitliyor, sunucu tarafındaki reddi değil.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildAskBody,
  DEFAULT_MODEL_ID,
  MODEL_KEY,
  readStoredModel,
  storeModel,
} from "@/lib/settings";

function stubStorage(initial?: Record<string, string>) {
  const store = new Map<string, string>(Object.entries(initial ?? {}));
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => void store.set(key, value),
    removeItem: (key: string) => void store.delete(key),
  });
  vi.stubGlobal("window", {});
  return store;
}

describe("readStoredModel", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("kayıt yoksa kalibre edilmiş varsayılana düşer", () => {
    stubStorage();

    expect(readStoredModel()).toBe(DEFAULT_MODEL_ID);
  });

  it("kaydedilmiş geçerli bir seçimi okur", () => {
    stubStorage({ [MODEL_KEY]: "gpt-5-mini" });

    expect(readStoredModel()).toBe("gpt-5-mini");
  });

  it("tanınmayan bir kaydı yok sayıp varsayılana döner", () => {
    // Eski bir sürümden kalmış ya da elle kurcalanmış değer.
    stubStorage({ [MODEL_KEY]: "silinmis-model" });

    expect(readStoredModel()).toBe(DEFAULT_MODEL_ID);
  });

  it("sunucuda render edilirken varsayılanı verir", () => {
    vi.stubGlobal("window", undefined);

    expect(readStoredModel()).toBe(DEFAULT_MODEL_ID);
  });
});

describe("storeModel", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("geçerli bir seçimi kalıcılaştırır", () => {
    const store = stubStorage();

    storeModel("Phi-4-mini-instruct");

    expect(store.get(MODEL_KEY)).toBe("Phi-4-mini-instruct");
  });

  it("tanınmayan bir seçimi yazmaz", () => {
    const store = stubStorage();

    storeModel("../gizli");

    expect(store.get(MODEL_KEY)).toBeUndefined();
  });
});

describe("buildAskBody", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("seçili modeli isteğe ekler", () => {
    stubStorage({ [MODEL_KEY]: "gpt-5-mini" });

    const body = buildAskBody({
      question: "yakıt limiti",
      conversationId: "c1",
      summary: "",
      history: [],
    });

    expect(body.modelId).toBe("gpt-5-mini");
  });

  it("seçim yokken varsayılanı gönderir", () => {
    stubStorage();

    const body = buildAskBody({
      question: "s",
      conversationId: "c1",
      summary: "",
      history: [],
    });

    expect(body.modelId).toBe(DEFAULT_MODEL_ID);
  });

  it("kurcalanmış bir kaydı sunucuya taşımaz", () => {
    stubStorage({ [MODEL_KEY]: "../gizli" });

    const body = buildAskBody({
      question: "s",
      conversationId: "c1",
      summary: "",
      history: [],
    });

    expect(body.modelId).toBe(DEFAULT_MODEL_ID);
  });

  it("sorunun ve geçmişin alanlarını korur", () => {
    stubStorage();

    const body = buildAskBody({
      question: "yakıt limiti",
      conversationId: "c9",
      summary: "önceki özet",
      history: [{ role: "user", content: "merhaba" }],
    });

    expect(body).toMatchObject({
      question: "yakıt limiti",
      conversationId: "c9",
      summary: "önceki özet",
      history: [{ role: "user", content: "merhaba" }],
    });
  });
});
