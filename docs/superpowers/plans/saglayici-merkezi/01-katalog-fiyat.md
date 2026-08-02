# Task 1: Model kataloğu ve fiyatlandırma

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.1, §4.2.
> **Sonraki:** [Task 2](02-kimlik-deposu.md)

**Dosyalar:** `src/rag/catalog.py`, `src/rag/pricing.py`, `config/model_prices.json`
**Test:** `tests/test_catalog.py`, `tests/test_pricing.py`

**Üretir:** `ModelInfo`, `list_models()`, `get_model()`, `providers()`,
`load_prices()`, `estimate_cost(model_id, input_tokens, output_tokens) -> float | None`

🚨 **Bu task'ın tek kritik kuralı:** doğrulanmamış fiyat **uydurulmaz**. Yalnız Anthropic
fiyatları yetkili kaynaktan (2026-06-24 tablosu) girilir; OpenAI ve Gemini `null` kalır.

- [ ] **Adım 1: Katalog için kırmızı test**

```python
# tests/test_catalog.py
from src.rag.catalog import ModelInfo, get_model, list_models, providers


def test_catalog_covers_the_four_providers():
    assert set(providers()) == {"ollama", "anthropic", "openai", "gemini"}


def test_models_can_be_filtered_by_provider():
    anthropic_models = list_models(provider="anthropic")

    assert anthropic_models
    assert all(m.provider == "anthropic" for m in anthropic_models)


def test_cloud_models_are_not_marked_local():
    assert get_model("claude-opus-5").local is False


def test_unknown_model_returns_none():
    assert get_model("model-yok") is None
```

- [ ] **Adım 2: Kırmızıyı doğrula** — `pytest tests/test_catalog.py -v --no-cov`
      Beklenen: `ModuleNotFoundError: No module named 'src.rag.catalog'`

- [ ] **Adım 3: `catalog.py` yaz**

`ModelInfo` donmuş dataclass (`id`, `provider`, `label`, `context_tokens`, `local`).
Bulut modelleri modül düzeyinde bir demet olarak sabit; yerel modeller **katalogda yok**
(çalışma zamanında Ollama'dan gelir, Task 7).

Kanonik model kimlikleri — tarih soneki **eklenmez**:
`claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5`, `gpt-4o-mini`, `gemini-2.0-flash`.

- [ ] **Adım 4: Yeşili doğrula** — 4 test geçmeli

- [ ] **Adım 5: Fiyatlandırma için kırmızı test**

```python
# tests/test_pricing.py
import pytest

from src.rag.pricing import estimate_cost, load_prices


def test_known_price_is_computed_per_million_tokens():
    # 1M giriş + 1M çıkış, Opus 5 = 5.00 + 25.00
    assert estimate_cost("claude-opus-5", 1_000_000, 1_000_000) == pytest.approx(30.0)


def test_local_models_cost_nothing():
    assert estimate_cost("qwen2.5:7b-instruct", 1000, 1000) == 0.0


def test_unpriced_model_returns_none_not_zero():
    # Fiyatı doğrulanmamış modeller null; 0 döndürmek "bedava" yalanı olurdu.
    assert estimate_cost("gpt-4o-mini", 1000, 1000) is None


def test_missing_token_count_returns_none():
    assert estimate_cost("claude-opus-5", None, 500) is None


def test_price_table_records_its_source():
    assert load_prices()["_kaynak"]
```

- [ ] **Adım 6: Kırmızıyı doğrula**

- [ ] **Adım 7: `pricing.py` + `config/model_prices.json` yaz**

JSON spec §4.2'deki gibi. `estimate_cost` sırası: token `None` → `None`;
yerel model (katalogda yok / `__local__`) → `0.0`; fiyat `null` → `None`; aksi halde
`(in/1e6)*input + (out/1e6)*output`. Dosya `encoding="utf-8"` ile okunur.

- [ ] **Adım 8: Yeşili doğrula** — 5 test geçmeli

- [ ] **Adım 9: Kalite kapısı ve commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/catalog.py src/rag/pricing.py config/model_prices.json tests/test_catalog.py tests/test_pricing.py
git commit -m "feat(catalog): add model catalog and price table with unpriced-model guard"
```

## Definition of Done
- [ ] 9 test yeşil, `catalog.py` ve `pricing.py` %100 kapsanmış
- [ ] `gpt-4o-mini` ve `gemini-2.0-flash` fiyatları `null` — **uydurulmamış**
- [ ] Anthropic fiyatları JSON'da kaynak+tarih notuyla
- [ ] Ruff temiz, kapsam ≥ %70
