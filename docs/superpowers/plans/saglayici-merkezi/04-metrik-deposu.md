# Task 4: Metrik deposu (SQLite)

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.7.
> **Önceki:** [Task 3](03-token-ve-gemini.md) · **Sonraki:** [Task 5](05-langgraph-agent.md)

**Dosyalar:** `src/rag/metrics.py` · **Test:** `tests/test_metrics.py`

**Üretir:** `RunRecord` dataclass, `MetricsStore(path)` — `record()`, `recent()`,
`summary_by_model()`, `clear()`

Neden SQLite: stdlib'de var (yeni bağımlılık yok), tek dosya, eşzamanlı okuma yeterli.

- [ ] **Adım 1: Kırmızı test**

```python
# tests/test_metrics.py
from src.rag.metrics import MetricsStore, RunRecord


def _run(**overrides) -> RunRecord:
    base = dict(
        model_id="claude-opus-5",
        provider="anthropic",
        question="Yıllık izin talebimi nasıl yaparım?",
        latency_ms=1200,
        input_tokens=800,
        output_tokens=120,
        cost_usd=0.007,
        citation_count=2,
        gate_passed=True,
        tool_calls=1,
        repaired=False,
    )
    base.update(overrides)
    return RunRecord(**base)


def test_a_recorded_run_can_be_read_back(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run())

    rows = store.recent()

    assert len(rows) == 1
    assert rows[0].model_id == "claude-opus-5"


def test_unmeasured_tokens_and_cost_stay_null(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run(input_tokens=None, output_tokens=None, cost_usd=None))

    row = store.recent()[0]

    assert row.input_tokens is None
    assert row.cost_usd is None


def test_summary_groups_by_model_and_averages_latency(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run(latency_ms=1000))
    store.record(_run(latency_ms=2000))
    store.record(_run(model_id="qwen2.5:7b-instruct", provider="ollama", latency_ms=60000))

    summary = {row.model_id: row for row in store.summary_by_model()}

    assert summary["claude-opus-5"].runs == 2
    assert summary["claude-opus-5"].avg_latency_ms == 1500
    assert summary["qwen2.5:7b-instruct"].runs == 1


def test_summary_ignores_nulls_when_totalling_cost(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run(cost_usd=0.01))
    store.record(_run(cost_usd=None))

    row = next(iter(store.summary_by_model()))

    assert row.total_cost_usd == 0.01
    assert row.priced_runs == 1  # maliyeti bilinen koşu sayısı ayrıca raporlanır


def test_recent_returns_newest_first(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run(question="ilk"))
    store.record(_run(question="ikinci"))

    assert store.recent()[0].question == "ikinci"


def test_schema_is_created_on_first_use(tmp_path):
    path = tmp_path / "yok" / "m.db"

    MetricsStore(path).record(_run())

    assert path.exists()


def test_the_store_never_persists_a_credential(tmp_path):
    # Şemada anahtar için sütun olmamalı.
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run())

    columns = store.columns()

    assert not any("key" in c or "token_secret" in c for c in columns)
```

- [ ] **Adım 2: Kırmızıyı doğrula** — `ModuleNotFoundError`

- [ ] **Adım 3: `metrics.py` yaz**

- `RunRecord` — spec §4.7'deki alanlar; `ts` yazarken `datetime.now(UTC).isoformat()`
- `MetricsStore.__init__` — üst klasörü `mkdir(parents=True, exist_ok=True)`, tabloyu
  `CREATE TABLE IF NOT EXISTS` ile kurar
- `record()` parametreli sorgu kullanır (string birleştirme **yok**)
- `summary_by_model()` — `runs`, `avg_latency_ms`, `total_cost_usd`, `priced_runs`,
  `avg_citations`, `gate_pass_rate` döndürür. `AVG`/`SUM` NULL'ları zaten atlar;
  `priced_runs` `COUNT(cost_usd)` ile ayrıca raporlanır ki "toplam maliyet düşük"
  yanılgısı oluşmasın
- Bağlantı her çağrıda açılıp kapanır (Streamlit çok iş parçacıklı; tek bağlantı paylaşmak
  `check_same_thread` hatası verir)

- [ ] **Adım 4: Yeşili doğrula** — 7 test geçmeli

- [ ] **Adım 5: `.gitignore` kontrolü** — `storage/` zaten yoksayılıyor; `metrics.db` orada

- [ ] **Adım 6: Kalite kapısı ve commit**

```bash
git commit -m "feat(metrics): add SQLite run store with null-safe cost aggregation"
```

## Definition of Done
- [ ] 7 test yeşil, `metrics.py` ≥ %95 kapsanmış
- [ ] `None` token/maliyet NULL olarak saklanıyor, 0'a çevrilmiyor
- [ ] `priced_runs` ile "kaç koşunun fiyatı biliniyor" ayrı raporlanıyor
- [ ] Şemada kimlik bilgisi sütunu yok
