# Task 6: Agent → metrik entegrasyonu

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.7.
> **Önceki:** [Task 5](05-langgraph-agent.md) · **Sonraki:** [Task 7](07-ollama-yonetici.md)

**Dosyalar:** `src/rag/models.py`, `src/rag/graph.py`, `src/rag/agent.py`
**Test:** `tests/test_agent_metrics.py`

**Üretir:** `Answer.usage`, `Answer.latency_ms`, `Agent(..., metrics=None)` — her
cevaptan sonra bir `RunRecord` yazılır.

- [ ] **Adım 1: Kırmızı test**

```python
# tests/test_agent_metrics.py
from src.rag.agent import Agent
from src.rag.llm import LLMResponse, ToolCall, TokenUsage
from src.rag.metrics import MetricsStore
from tests.test_agent import _ScriptedLLM, _StubRetriever, _StubToolBox


def test_a_successful_answer_is_recorded(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    llm = _ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "izin"})]),
            LLMResponse(text="İzin HRPortal'dan alınır [1].", usage=TokenUsage(500, 40)),
        ]
    )
    agent = Agent(_StubRetriever(confident=True), _StubToolBox(), llm, metrics=store)

    agent.answer("Yıllık izin nasıl alınır?")

    row = store.recent()[0]
    assert row.citation_count == 1
    assert row.gate_passed is True
    assert row.tool_calls == 1


def test_a_refusal_is_recorded_too(tmp_path):
    # Konu dışı sorular da ölçülmeli; kapı isabetini ancak böyle raporlayabiliriz.
    store = MetricsStore(tmp_path / "m.db")
    agent = Agent(_StubRetriever(confident=False), _StubToolBox(), _ScriptedLLM([]), metrics=store)

    agent.answer("Bugün hava nasıl?")

    row = store.recent()[0]
    assert row.gate_passed is False
    assert row.citation_count == 0
    assert row.tool_calls == 0


def test_token_usage_is_summed_across_turns(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    llm = _ScriptedLLM(
        [
            LLMResponse(
                tool_calls=[ToolCall("1", "search_documents", {"query": "x"})],
                usage=TokenUsage(100, 10),
            ),
            LLMResponse(text="Cevap [1].", usage=TokenUsage(400, 30)),
        ]
    )
    Agent(_StubRetriever(confident=True), _StubToolBox(), llm, metrics=store).answer("s")

    row = store.recent()[0]
    assert row.input_tokens == 500
    assert row.output_tokens == 40


def test_unmeasured_usage_stays_null(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    llm = _ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="Cevap [1]."),
        ]
    )
    Agent(_StubRetriever(confident=True), _StubToolBox(), llm, metrics=store).answer("s")

    assert store.recent()[0].input_tokens is None


def test_metrics_are_optional(tmp_path):
    # metrics=None ile agent eskisi gibi çalışmalı — CLI ve testler bozulmasın.
    agent = Agent(_StubRetriever(confident=False), _StubToolBox(), _ScriptedLLM([]))

    assert agent.answer("Bugün hava nasıl?").text


def test_answer_exposes_latency_and_usage(tmp_path):
    llm = _ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="Cevap [1].", usage=TokenUsage(10, 5)),
        ]
    )
    answer = Agent(_StubRetriever(confident=True), _StubToolBox(), llm).answer("s")

    assert answer.latency_ms >= 0
    assert answer.usage.output_tokens == 5
```

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: Uygula**

- `Answer`'a `usage: TokenUsage = TokenUsage()` ve `latency_ms: int = 0` eklenir
  (varsayılanlı → mevcut `Answer(...)` çağrıları bozulmaz)
- Grafik durumu her `llm_turn`'de `usage`'ı **toplar**; her iki alan da `None` ise
  toplam `None` kalır (bir turda ölçülüp diğerinde ölçülmediyse ölçülenler toplanır)
- `Agent.answer` süreyi `time.perf_counter()` ile ölçer
- `metrics` verilmişse `RunRecord` yazılır; maliyet `estimate_cost(model_id, ...)` ile
- Model kimliği LLM istemcisinden okunur (`client.model`)
- 🚨 **Soru metni kaydediliyor** — bu bir demo; gerçek dağıtımda PII olabilir. README'ye not

- [ ] **Adım 4: Yeşili doğrula** — 6 test geçmeli, mevcut agent testleri hâlâ 7/7

- [ ] **Adım 5: Kalite kapısı ve commit**

```bash
git commit -m "feat(metrics): record every agent run with usage, latency and cost"
```

## Definition of Done
- [ ] 6 test yeşil; `tests/test_agent.py` hâlâ 7/7 ve değiştirilmemiş
- [ ] Red edilen sorular da kaydediliyor (kapı isabeti ölçülebilir)
- [ ] Ölçülmeyen token NULL kalıyor
- [ ] `metrics=None` ile agent eskisi gibi çalışıyor
