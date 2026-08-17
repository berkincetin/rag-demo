/**
 * Tema tercihi iki sayfa arasında paylaşılıyor.
 *
 * Sohbet sayfası temayı `<html>` üzerindeki `dark` sınıfıyla uyguluyor ve
 * `localStorage`'a yazıyor. Analiz sayfası ayrı bir rota olduğu için aynı
 * mantığı kendi başına uygulamak zorunda; etmezse koyu temadaki bir kullanıcı
 * "Satış analizi"ne tıkladığında sayfa açık temaya düşer.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { readStoredTheme, THEME_KEY } from "@/lib/theme";

function stubWindow(stored: string | null, prefersDark: boolean) {
  const store = new Map<string, string>();
  if (stored !== null) store.set(THEME_KEY, stored);

  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => void store.set(key, value),
  });
  vi.stubGlobal("window", {
    matchMedia: () => ({ matches: prefersDark }),
    localStorage: { getItem: (key: string) => store.get(key) ?? null },
  });
}

describe("readStoredTheme", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("kaydedilmiş koyu tercihi okur", () => {
    stubWindow("dark", false);

    expect(readStoredTheme()).toBe(true);
  });

  it("kaydedilmiş açık tercih işletim sistemini geçersiz kılar", () => {
    stubWindow("light", true);

    expect(readStoredTheme()).toBe(false);
  });

  it("kayıt yoksa işletim sistemi tercihine düşer", () => {
    stubWindow(null, true);

    expect(readStoredTheme()).toBe(true);
  });

  it("sunucuda render edilirken açık temaya düşer", () => {
    vi.stubGlobal("window", undefined);

    expect(readStoredTheme()).toBe(false);
  });
});
