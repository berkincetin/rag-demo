# Task 5: LangGraph agent migrasyonu 🎯

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §2.1, §4.5.
> **Önceki:** [Task 4](04-metrik-deposu.md) · **Sonraki:** [Task 6](06-agent-metrik.md)

**Dosyalar:** `src/rag/graph.py` (yeni), `src/rag/agent.py` (cepheye dönüşür)
**Test:** `tests/test_graph.py` (yeni) — `tests/test_agent.py` **değişmez**

🚨 **Bu planın en riskli task'ı.** 3 katmanlı güvenlik ağı bir grafiğe taşınıyor.
Bozulursa sistem kaynaksız cevap vermeye başlar — yani case'in en kritik gereksinimi düşer.

## Davranış sözleşmesi (pazarlığa kapalı)

**`tests/test_agent.py` içindeki 7 test tek karakter değiştirilmeden geçmelidir.**
Bu testler mevcut davranışı kilitler:

| Test | Kilitlediği davranış |
|---|---|
| `off_topic_question_is_refused_without_calling_the_llm` | 1. katman: skor kapısı LLM'den **önce** |
| `tool_call_result_is_fed_back_and_the_final_answer_is_returned` | Tool sonucu bağlama giriyor |
| `an_uncited_answer_gets_one_repair_attempt_before_being_discarded` | Onarım turu **bir kez** |
| `answer_without_any_citation_is_replaced_by_the_no_info_template` | 3. katman: atıf post-check |
| `context_is_injected_when_the_model_skips_the_tool_call` | Enjeksiyon + `injected: True` izi |
| `tool_loop_stops_at_the_configured_turn_limit` | `max_tool_turns` bütçesi (onarım turu **saymaz**) |
| `extract_citations_*` (2 test) | Atıf eşleştirme |

Migrasyon sırasında bu testlerden biri kırmızıya dönerse: **grafiği düzelt, testi değil.**

- [ ] **Adım 1: Mevcut davranışı kilitle (yeşil taban çizgisi)**

```bash
pytest tests/test_agent.py -v --no-cov
```
Beklenen: **7 passed**. Bu çıktı migrasyondan önce kaydedilir; sonrasında birebir aynı olmalı.

- [ ] **Adım 2: Grafik için kırmızı test**

```python
# tests/test_graph.py
from src.rag.graph import build_graph, AgentState
from src.rag.llm import LLMResponse, ToolCall
# _StubRetriever / _StubToolBox / _ScriptedLLM tests/test_agent.py'den içe aktarılır
from tests.test_agent import _ScriptedLLM, _StubRetriever, _StubToolBox


def test_graph_refuses_before_any_llm_call():
    llm = _ScriptedLLM([])
    graph = build_graph(_StubRetriever(confident=False), _StubToolBox(), llm)

    state = graph.invoke({"question": "Bugün hava nasıl?"})

    assert llm.call_count == 0
    assert state["citations"] == []


def test_graph_exposes_its_node_names_for_visualisation():
    # Grafik seçilmesinin sebeplerinden biri akışın görünür olması.
    graph = build_graph(_StubRetriever(confident=True), _StubToolBox(), _ScriptedLLM([]))

    nodes = set(graph.get_graph().nodes)

    assert {"score_gate", "llm_turn", "run_tools", "citation_check", "repair"} <= nodes


def test_repair_node_runs_at_most_once():
    llm = _ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="atıfsız"),
            LLMResponse(text="yine atıfsız"),
        ]
    )
    graph = build_graph(_StubRetriever(confident=True), _StubToolBox(), llm)

    state = graph.invoke({"question": "kaç gün izin?"})

    assert state["repaired"] is True
    assert llm.call_count == 3  # 1 tool turu + 1 cevap + 1 onarım
```

- [ ] **Adım 3: Kırmızıyı doğrula**

- [ ] **Adım 4: `graph.py` yaz**

Durum: spec §4.5'teki `AgentState`. Düğümler:

| Düğüm | İş |
|---|---|
| `score_gate` | `retriever.search` + `is_confident`. Güvensizse `refuse`'a dallanır |
| `llm_turn` | `llm.chat(messages, TOOL_SCHEMAS)`; yanıtı duruma yazar |
| `run_tools` | Her `tool_call` için `toolbox.run`, çıktıyı + `CITATION_REMINDER`'ı mesajlara ekler, ize yazar |
| `inject_context` | Tool çağrılmadıysa ve hiç çıktı yoksa aramayı kendisi yapar (`injected: True`) |
| `citation_check` | `extract_citations`; boşsa `repair`'e, doluysa `finish`'e |
| `repair` | `CITATION_REPAIR` ile bir kez daha sorar; `repaired=True` |
| `refuse` / `no_info` / `finish` | Uç durumlar |

Koşullu kenarlar mevcut `if` mantığını birebir yansıtır. **Tur bütçesi:** `llm_turn` ↔
`run_tools` döngüsü `max_tool_turns` kez; onarım turu bu bütçeye **dahil değil**
(mevcut davranış — `final_text` doluysa tetiklenir, tur limiti dolduğunda tetiklenmez).

`extract_citations` `agent.py`'de kalır ve `graph.py` onu içe aktarır — testler onu
`src.rag.agent`'tan alıyor, o içe aktarım kırılmamalı.

- [ ] **Adım 5: `agent.py`'yi cepheye dönüştür**

```python
class Agent:
    def __init__(self, retriever, toolbox, llm, max_tool_turns: int = 3) -> None:
        ...  # imza aynı kalır
        self._graph = build_graph(retriever, toolbox, llm, max_tool_turns)

    def answer(self, question: str) -> Answer:
        state = self._graph.invoke({"question": question, ...})
        return Answer(text=..., citations=..., tool_trace=state["trace"])
```

`Agent`'ın **genel arayüzü değişmez** — `cli.py`, `app.py`, `scripts/smoke_test.py`,
`notebooks/demo.ipynb` hiçbir değişiklik gerektirmez.

- [ ] **Adım 6: Sözleşmeyi doğrula** ⚠️ **En önemli adım**

```bash
pytest tests/test_agent.py -v --no-cov     # 7 passed — Adım 1 ile birebir aynı
pytest tests/test_graph.py -v --no-cov     # 3 passed
```

Herhangi bir agent testi kırmızıysa **`systematic-debugging` çağır**, testi değiştirme.

- [ ] **Adım 7: Uçtan uca doğrulama (gerçek model)**

```bash
python scripts/smoke_test.py
```
Beklenen: **Başarısız kontrol sayısı: 0** — grafik gerçek LLM ile de aynı davranıyor.
Bu adım atlanamaz: birim testleri scripted LLM kullanıyor, Task 12'de öğrendiğimiz gibi
scripted testler yeşilken sistem uçtan uca bozuk olabilir.

- [ ] **Adım 8: Kalite kapısı ve commit**

```bash
git commit -m "refactor(agent): migrate the tool loop to a LangGraph state machine"
```

## Definition of Done
- [ ] `tests/test_agent.py` **7/7 yeşil, dosya değiştirilmemiş** (`git diff` boş)
- [ ] `tests/test_graph.py` 3/3 yeşil
- [ ] `scripts/smoke_test.py` → 0 başarısız kontrol (gerçek modelle)
- [ ] `Agent` genel arayüzü değişmemiş; CLI/Streamlit/notebook dokunulmamış
- [ ] Ruff temiz, kapsam ≥ %70
