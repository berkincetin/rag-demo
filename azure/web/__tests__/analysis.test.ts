/**
 * Dışa aktarılmış analiz verisi ve gezinme yapısı.
 *
 * `analysis.json` derleme anında üretilir; sayfa onu doğrudan import eder.
 * Bu testler dosyanın sayfanın beklediği sözleşmeye uyduğunu doğrular — biçim
 * bozulursa derleme değil, bu testler kırılır ve sebebi okunur olur.
 */

import { describe, expect, it } from "vitest";

import analysis from "@/lib/analysis.json";
import { sectionLinks, type AnalysisDocument } from "@/lib/analysis";

const document = analysis as AnalysisDocument;

describe("analiz belgesi", () => {
  it("yönetici özetiyle başlayan bölümler taşır", () => {
    const ids = document.sections.map((section) => section.id);

    expect(ids).toContain("yonetici-ozeti");
    expect(ids).toContain("a1-son-2-yilin-satis-performansi-ve-urun-kirilimi");
    expect(ids).toContain("a7-bir-sonraki-ay-talep-tahmini");
  });

  it("case'in yedi analiz görevinin tamamını içerir", () => {
    const ids = document.sections.map((section) => section.id);

    for (const task of ["a1", "a2", "a3", "a4", "a5", "a6", "a7"]) {
      expect(ids.some((id) => id.startsWith(`${task}-`))).toBe(true);
    }
  });

  it("her bölümün benzersiz bir çapası vardır", () => {
    const ids = document.sections.map((section) => section.id);

    expect(new Set(ids).size).toBe(ids.length);
  });

  it("figürleri gömülü base64 değil dosya yolu olarak taşır", () => {
    const figures = document.sections
      .flatMap((section) => section.blocks)
      .filter((block) => block.type === "figure");

    expect(figures.length).toBe(10);
    for (const figure of figures) {
      expect(figure.src).toMatch(/^\/analiz\/figur-\d{2}\.png$/);
    }
  });

  it("tabloları başlık ve satır olarak taşır, ham HTML olarak değil", () => {
    const tables = document.sections
      .flatMap((section) => section.blocks)
      .filter((block) => block.type === "table");

    expect(tables.length).toBe(20);
    for (const table of tables) {
      expect(Array.isArray(table.rows)).toBe(true);
      expect(JSON.stringify(table)).not.toContain("<table");
    }
  });

  it("her satır o tablonun başlık sayısını aşmaz", () => {
    const tables = document.sections
      .flatMap((section) => section.blocks)
      .filter((block) => block.type === "table");

    for (const table of tables) {
      for (const row of table.rows) {
        expect(row.length).toBeLessThanOrEqual(table.headers.length);
      }
    }
  });
});

describe("sectionLinks", () => {
  it("her bölüm için bir çapa bağlantısı üretir", () => {
    const links = sectionLinks(document);

    expect(links.length).toBe(document.sections.length);
    expect(links[0]).toMatchObject({ href: `#${document.sections[0].id}` });
  });

  it("başlıkları bağlantı etiketi olarak korur", () => {
    const links = sectionLinks(document);

    expect(links.every((link) => link.label.length > 0)).toBe(true);
  });
});
