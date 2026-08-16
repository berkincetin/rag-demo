# Task 8: Ingest and Threshold Calibration

**🚦 This task is a gate. No deployment work proceeds until thresholds are
measured.**

**Goal:** Build the real index with Azure embeddings, then **measure**
`MIN_COSINE` and `MIN_BM25` instead of inheriting the invalid e5 values.

**Files:**
- Create: `azure/scripts/ingest.py`
- Create: `azure/scripts/calibrate.py`
- Create: `azure/tests/test_calibration.py`
- Modify: `azure/.env.example` (record the measured values)
- Create: `docs/superpowers/plans/azure-deployment/CALIBRATION.md` (evidence)

**Interfaces:**
- Consumes: `build_index` (Task 5), `Retriever` (Task 6), `load_all` +
  `chunk_sections` (Task 4)
- Produces: measured `MIN_COSINE` / `MIN_BM25`, consumed by every later task

---

## Why this cannot be skipped

`MIN_COSINE=0.80` and `MIN_BM25=5.0` were calibrated in Part 1 Task 9 against
`intfloat/multilingual-e5-base`. `text-embedding-3-small` has a different
similarity distribution — e5 compresses cosine into a narrow high band, most
OpenAI embedding models do not. Reusing 0.80 would most likely refuse
everything.

The "I don't know" behaviour is a graded case requirement. It has to be
measured, and the evidence has to be written down.

- [ ] **Step 1: Write the ingest script**

Create `azure/scripts/ingest.py`:

```python
"""Build the Azure index from the documents in data/.

Run from the repository root:  python -m azure.scripts.ingest
"""

import sys

from azure.rag.chunker import chunk_sections
from azure.rag.config import AzureConfig
from azure.rag.embedder import AzureOpenAIEmbedder
from azure.rag.index import build_index
from azure.rag.loaders import load_all


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    config = AzureConfig.load()

    sections = load_all(config.data_dir)
    chunks = chunk_sections(sections)
    report = build_index(chunks, config.storage_dir, AzureOpenAIEmbedder(config))

    print(f"{len(sections)} bölüm → {report.chunk_count} parça, {report.seconds:.1f} sn")
    for source_file, count in sorted(report.per_file.items()):
        print(f"  {source_file}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run ingest against the real corpus**

```bash
python -m azure.scripts.ingest
```

Expected: `219 bölüm → 276 parça` (matching PROGRESSION.md) and a per-file
breakdown. If the chunk count differs from 276, a Task 4 copy drifted — stop
and fix that before calibrating.

- [ ] **Step 3: Write the calibration script**

Create `azure/scripts/calibrate.py`:

```python
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

# Questions the corpus demonstrably answers. Taken from the Part 1 probe set.
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
        # Wide open: we are measuring, not gating.
        min_cosine=-1.0,
        min_bm25=-1.0,
    )

    def measure(label: str, questions: list[str]) -> list[tuple[float, float]]:
        print(f"\n=== {label} ===")
        rows = []
        for question in questions:
            hits = retriever.search(question, top_k=config.top_k)
            if not hits:
                print(f"  {question[:45]:<45} —      —      (sonuç yok)")
                rows.append((0.0, 0.0))
                continue
            best = hits[0]
            print(
                f"  {question[:45]:<45} {best.cosine:.3f}  {best.bm25:6.2f}  "
                f"{best.chunk.citation_label[:40]}"
            )
            rows.append((best.cosine, best.bm25))
        return rows

    valid = measure("GEÇERLİ SORULAR", VALID_QUESTIONS)
    off_topic = measure("KONU DIŞI SORULAR", OFF_TOPIC_QUESTIONS)

    min_valid_cosine = min(row[0] for row in valid)
    max_off_cosine = max(row[0] for row in off_topic)
    min_valid_bm25 = min(row[1] for row in valid)
    max_off_bm25 = max(row[1] for row in off_topic)

    print("\n=== ÖZET ===")
    print(f"  Geçerli en düşük kosinüs : {min_valid_cosine:.3f}")
    print(f"  Konu dışı en yüksek      : {max_off_cosine:.3f}")
    print(f"  Geçerli en düşük BM25    : {min_valid_bm25:.2f}")
    print(f"  Konu dışı en yüksek BM25 : {max_off_bm25:.2f}")

    cosine_separates = min_valid_cosine > max_off_cosine
    bm25_separates = min_valid_bm25 > max_off_bm25
    print(f"\n  Kosinüs tek başına ayırıyor mu? {cosine_separates}")
    print(f"  BM25 tek başına ayırıyor mu?    {bm25_separates}")

    if cosine_separates:
        print(f"  → MIN_COSINE önerisi: {(min_valid_cosine + max_off_cosine) / 2:.3f}")
    if bm25_separates:
        print(f"  → MIN_BM25 önerisi:   {(min_valid_bm25 + max_off_bm25) / 2:.2f}")
    if not cosine_separates and not bm25_separates:
        print("  ⚠️  Hiçbir sinyal tek başına ayırmıyor — VE kapısını incele.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the calibration and read the numbers**

```bash
python -m azure.scripts.calibrate
```

Read the actual output. Choose thresholds that separate the two groups with
the AND gate, leaving a margin on both sides.

**If the groups do not separate: stop and report it as a finding.** Do not
tune until the numbers look agreeable. Options to propose (not to implement
unilaterally): widen the probe set, reconsider the AND gate, or reconsider
`text-embedding-3-small`.

- [ ] **Step 5: Record the evidence**

Create `docs/superpowers/plans/azure-deployment/CALIBRATION.md` containing:

- The date and the exact command run
- The **full verbatim output** of the calibration script
- The chosen `MIN_COSINE` and `MIN_BM25`, with one sentence of justification
- The margin between the chosen value and the nearest counterexample

This file is the evidence for the "thresholds recalibrated" DoD line. Numbers
in it must be copied from real output, never typed from memory.

- [ ] **Step 6: Write the gate regression test**

Create `azure/tests/test_calibration.py`:

```python
"""The measured thresholds must gate the real corpus correctly.

Integration: needs a built index and a live Azure OpenAI endpoint.
"""

import pytest

from azure.rag.config import AzureConfig
from azure.rag.embedder import AzureOpenAIEmbedder
from azure.rag.index import load_index
from azure.rag.retriever import Retriever
from azure.scripts.calibrate import OFF_TOPIC_QUESTIONS, VALID_QUESTIONS


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    config = AzureConfig.load()
    assert config.min_cosine > 0, "MIN_COSINE not calibrated — run azure.scripts.calibrate"
    assert config.min_bm25 > 0, "MIN_BM25 not calibrated — run azure.scripts.calibrate"
    return Retriever(
        index=load_index(config.storage_dir),
        embedder=AzureOpenAIEmbedder(config),
        min_cosine=config.min_cosine,
        min_bm25=config.min_bm25,
    )


@pytest.mark.integration
@pytest.mark.parametrize("question", VALID_QUESTIONS)
def test_valid_questions_pass_the_gate(retriever, question):
    assert retriever.is_confident(retriever.search(question))


@pytest.mark.integration
@pytest.mark.parametrize("question", OFF_TOPIC_QUESTIONS)
def test_off_topic_questions_are_rejected(retriever, question):
    assert not retriever.is_confident(retriever.search(question))


@pytest.mark.integration
def test_docx_table_value_is_retrievable(retriever):
    """`1.500 TL/ay` lives only in a DOCX table."""
    hits = retriever.search("Araç yakıt limiti ne kadar?")

    assert retriever.is_confident(hits)
    assert any("1.500 TL/ay" in hit.chunk.text for hit in hits)
```

- [ ] **Step 7: Set the measured values and run the test**

Write the chosen values into `azure/.env` (and `azure/.env.example` as
documentation), then:

Run: `pytest azure/tests/test_calibration.py -v -m integration`
Expected: all 13 pass — 7 valid, 5 off-topic, 1 table lookup

If any fail, the thresholds are wrong. Re-measure; do not weaken the test.

- [ ] **Step 8: Confirm the local path is untouched**

```bash
git status --short src/ tests/ gradio_app.py docker-compose.yml
```

Expected: no output.

- [ ] **Step 9: Quality gate**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 10: Commit**

```bash
git add azure/ docs/superpowers/plans/azure-deployment/CALIBRATION.md
git commit -m "feat(azure): add ingest and calibrate retrieval thresholds"
```

Put the measured values in the commit body.
