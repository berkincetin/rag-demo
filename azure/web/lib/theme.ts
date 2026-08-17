/**
 * Tema tercihinin tek kaynağı.
 *
 * Sohbet ve analiz ayrı rotalar; her biri tercihi kendi mount'unda uygular.
 * Mantık burada tek yerde durmasaydı iki sayfa ayrışır ve rotalar arası geçişte
 * tema atlardı.
 */

export const THEME_KEY = "rag-theme";

/** Kaydedilmiş tercih, yoksa işletim sisteminin tercihi. */
export function readStoredTheme(): boolean {
  if (typeof window === "undefined") return false;
  const stored = localStorage.getItem(THEME_KEY);
  if (stored) return stored === "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** Tercihi `<html>` sınıfına uygular ve kalıcılaştırır. */
export function applyTheme(dark: boolean): void {
  document.documentElement.classList.toggle("dark", dark);
  localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
}
