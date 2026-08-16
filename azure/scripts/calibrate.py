"""Measure the retrieval gate thresholds for text-embedding-3-small.

The e5 thresholds (0.80 / 5.0) are invalid for a different embedding model.
This prints the cosine and BM25 distributions for known-valid and known
off-topic questions so a separating threshold can be chosen from data.

Run from the repository root:  python -m azure.scripts.calibrate
"""

import sys

from azure.rag.config import AzureConfig
from azure.rag.embedder import AzureOpenAIEmbedder
from azure.rag.index import load_index
from azure.rag.retriever import Retriever

# Questions the corpus demonstrably answers.
VALID_QUESTIONS = [
    "Yıllık izin talebimi nasıl yaparım?",
    "Araç yakıt limiti ne kadar?",
    "OPS-PRO-003 prosedürü nedir?",
    "Vitatin95 nedir?",
    "Şirket aracı kimlere tahsis edilir?",
    "İzin talebi kaç gün önce yapılmalı?",
    "Masraf beyanı nasıl yapılır?",
]

# Questions the corpus does not answer. The gate must reject all of them.
OFF_TOPIC_QUESTIONS = [
    "Bugün hava nasıl?",
    "İstanbul'un nüfusu kaç?",
    "Python'da liste nasıl sıralanır?",
    "En iyi futbol takımı hangisi?",
    "Pizza tarifi verir misin?",
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    config = AzureConfig.load()

    retriever = Retriever(
        index=load_index(config.storage_dir),
        embedder=AzureOpenAIEmbedder(config),
        min_cosine=-1.0,
        min_bm25=-1.0,
    )

    def measure(label: str, questions: list[str]) -> list[tuple[float, float]]:
        print(f"\n=== {label} ===")
        rows = []
        for question in questions:
            hits = retriever.search(question, top_k=config.top_k)
            if not hits:
                print(f"  {question[:42]:<42}    ---     ---   (sonuc yok)")
                rows.append((0.0, 0.0))
                continue
            best = hits[0]
            print(
                f"  {question[:42]:<42} {best.cosine:.3f}  {best.bm25:6.2f}  "
                f"{best.chunk.citation_label[:38]}"
            )
            rows.append((best.cosine, best.bm25))
        return rows

    valid = measure("GECERLI SORULAR", VALID_QUESTIONS)
    off_topic = measure("KONU DISI SORULAR", OFF_TOPIC_QUESTIONS)

    min_valid_cosine = min(r[0] for r in valid)
    max_off_cosine = max(r[0] for r in off_topic)
    min_valid_bm25 = min(r[1] for r in valid)
    max_off_bm25 = max(r[1] for r in off_topic)

    print("\n=== OZET ===")
    print(f"  Gecerli en dusuk kosinus : {min_valid_cosine:.3f}")
    print(f"  Konu disi en yuksek      : {max_off_cosine:.3f}")
    print(f"  Gecerli en dusuk BM25    : {min_valid_bm25:.2f}")
    print(f"  Konu disi en yuksek BM25 : {max_off_bm25:.2f}")

    cos_sep = min_valid_cosine > max_off_cosine
    bm_sep = min_valid_bm25 > max_off_bm25
    print(f"\n  Kosinus tek basina ayiriyor mu? {cos_sep}")
    print(f"  BM25 tek basina ayiriyor mu?    {bm_sep}")
    if cos_sep:
        print(f"  -> MIN_COSINE onerisi: {(min_valid_cosine + max_off_cosine) / 2:.3f}")
    if bm_sep:
        print(f"  -> MIN_BM25 onerisi:   {(min_valid_bm25 + max_off_bm25) / 2:.2f}")
    if not cos_sep and not bm_sep:
        print("  UYARI: hicbir sinyal tek basina ayirmiyor - VE kapisini incele.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
