/**
 * Dışa aktarılmış analizin tipleri ve gezinme yardımcıları.
 *
 * Veri `azure/scripts/export_analysis.py` tarafından derleme öncesi üretilir.
 * Notebook'u tarayıcıda çalıştırmak pandas, statsmodels ve LightGBM'i istemciye
 * taşımak olurdu; analiz zaten yapılmış, sayfanın işi onu göstermek.
 */

export type NarrativeBlock = { type: "narrative"; markdown: string };
export type CodeBlock = { type: "code"; source: string };
export type StreamBlock = { type: "stream"; text: string };
export type TableBlock = { type: "table"; headers: string[]; rows: string[][] };
export type FigureBlock = { type: "figure"; src: string; alt: string };

export type AnalysisBlock =
  | NarrativeBlock
  | CodeBlock
  | StreamBlock
  | TableBlock
  | FigureBlock;

export type AnalysisSection = {
  id: string;
  title: string;
  blocks: AnalysisBlock[];
};

export type AnalysisDocument = {
  sections: AnalysisSection[];
  figureCount: number;
};

export type SectionLink = { href: string; label: string };

/** Kenar çubuğunun çizdiği çapa bağlantıları, belgedeki sırayla. */
export function sectionLinks(document: AnalysisDocument): SectionLink[] {
  return document.sections.map((section) => ({
    href: `#${section.id}`,
    label: section.title,
  }));
}
