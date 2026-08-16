# Task 9: Support Modules

**Goal:** Port metrics, pricing, catalog, session state, serialization and
chat memory — reduced to what a single-provider, authenticated deployment
needs.

**Files:**
- Create: `azure/rag/metrics.py`, `azure/rag/pricing.py`, `azure/rag/catalog.py`
- Create: `azure/rag/ui_state.py`, `azure/rag/serialize.py`, `azure/rag/memory.py`
- Create: `azure/config/model_prices.json`
- Modify: `azure/rag/build.py` (attach the metrics store)
- Create: `azure/tests/test_support_modules.py`

**Interfaces:**
- Consumes: `AzureConfig` (Task 1), `Answer` / `TokenUsage` (Task 4)
- Produces:
  ```python
  # azure/rag/catalog.py
  AZURE_MODEL_ID = "gpt-4.1-mini"
  def list_models() -> list[ModelInfo]: ...
  def get_model(model_id: str) -> ModelInfo | None: ...

  # azure/rag/pricing.py
  def estimate_cost(model_id: str, input_tokens: int | None,
                    output_tokens: int | None) -> float | None: ...

  # azure/rag/metrics.py
  class MetricsStore:
      def __init__(self, path: Path) -> None: ...
      def record(self, **fields) -> None: ...
      def recent(self) -> list[RunRecord]: ...
      def summary_by_model(self) -> list[ModelSummary]: ...

  # azure/rag/ui_state.py  ← session helpers live HERE, mirroring the original
  def get_memory(session: MutableMapping) -> ConversationMemory: ...
  def get_transcript(session: MutableMapping) -> list[tuple[str, str]]: ...
  def add_to_transcript(session: MutableMapping, question: str, answer: str) -> None: ...
  def clear_chat(session: MutableMapping) -> None: ...
  def get_user_name(session: MutableMapping) -> str: ...
  def set_user_name(session: MutableMapping, name: str) -> None: ...

  # azure/rag/memory.py  ← conversation memory only
  class Turn: ...
  class ConversationMemory: ...
  def retrieval_query(question: str, memory: ConversationMemory | None) -> str: ...

  # azure/rag/serialize.py
  def answer_payload(answer: Answer, cost: float | None) -> dict: ...
  def model_payload(model: ModelInfo) -> dict: ...
  def run_payload(record: RunRecord) -> dict: ...
  def summary_payload(summary: ModelSummary) -> dict: ...
  ```

Read the originals for the exact `RunRecord` / `ModelSummary` field lists and
`MetricsStore.record` keyword names, and keep them identical — the front-end
in Task 13 consumes these shapes unchanged.

---

## What gets dropped

| Original | Azure version |
|---|---|
| `catalog.py` — 5 cloud models, 4 providers | one model, one provider |
| `pricing.py` | unchanged logic, new price table |
| `ui_state.py` — key store, model switching, Ollama | transcript + user name only |
| `serialize.py` — includes key and evaluation shapes | those two payloads removed |
| `metrics.py` | unchanged, minus the `resources` columns |
| `evaluation.py`, `credentials.py`, `ollama_admin.py`, `resources.py` | **not copied** |

Resource measurement (`resources.py`) is dropped because peak CPU/RAM of a
container that only makes HTTP calls measures nothing meaningful.

- [ ] **Step 1: Write the failing tests**

Create `azure/tests/test_support_modules.py`:

```python
"""Support modules: catalog, pricing, memory, serialization."""

import pytest

from azure.rag.catalog import AZURE_MODEL_ID, get_model, list_models
from azure.rag.models import Answer, TokenUsage
from azure.rag.pricing import estimate_cost
from azure.rag.serialize import answer_payload
from azure.rag.ui_state import add_to_transcript, clear_chat, get_user_name, set_user_name


def test_catalog_exposes_only_the_azure_model():
    models = list_models()

    assert [model.id for model in models] == [AZURE_MODEL_ID]
    assert models[0].provider == "azure_openai"


def test_get_model_returns_none_for_unknown():
    assert get_model("gpt-4o-mini") is None


def test_estimate_cost_is_none_when_price_is_unknown():
    """The price table must never invent a number (CLAUDE.md §10)."""
    assert estimate_cost(AZURE_MODEL_ID, 1000, 100) is None


def test_estimate_cost_is_none_for_unreported_tokens():
    assert estimate_cost(AZURE_MODEL_ID, None, None) is None


def test_transcript_round_trips():
    session: dict = {}

    add_to_transcript(session, "soru", "cevap")

    assert get_user_name(session) == ""
    clear_chat(session)


def test_user_name_is_session_scoped():
    session: dict = {}

    set_user_name(session, "Berkin")

    assert get_user_name(session) == "Berkin"


def test_answer_payload_keeps_camel_case_keys():
    """The Next.js client consumes these names verbatim."""
    answer = Answer(text="cevap", citations=["a.docx — Bölüm 1"],
                    usage=TokenUsage(10, 5), latency_ms=42)

    payload = answer_payload(answer, cost=None)

    assert payload["text"] == "cevap"
    assert payload["citations"] == ["a.docx — Bölüm 1"]
    assert payload["latencyMs"] == 42
    assert payload["inputTokens"] == 10
    assert payload["costUsd"] is None
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `pytest azure/tests/test_support_modules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'azure.rag.catalog'`

- [ ] **Step 3: Write the catalog**

Create `azure/rag/catalog.py`:

```python
"""The single model this deployment can use.

Unlike src/rag/catalog.py there is no provider choice: the deployment talks to
one Azure OpenAI deployment, named by configuration.
"""

from dataclasses import dataclass

AZURE_MODEL_ID = "gpt-4.1-mini"
PROVIDER = "azure_openai"


@dataclass(frozen=True)
class ModelInfo:
    id: str
    provider: str
    label: str
    context_tokens: int | None = None
    local: bool = False


_MODELS = (ModelInfo(AZURE_MODEL_ID, PROVIDER, "GPT-4.1 mini (Azure)", 128_000),)


def list_models() -> list[ModelInfo]:
    return list(_MODELS)


def get_model(model_id: str) -> ModelInfo | None:
    return next((model for model in _MODELS if model.id == model_id), None)
```

- [ ] **Step 4: Write the price table**

Create `azure/config/model_prices.json`:

```json
{
  "_kaynak": "Azure OpenAI fiyatlandirmasi bolgeye ve katmana gore degisir ve DOGRULANMADIGI icin null birakilmistir. Arayuz 'fiyat girilmedi' gosterir. Uydurma fiyat girmeyin.",
  "_guncelleme": "2026-08-16",
  "gpt-4.1-mini": {"input": null, "output": null}
}
```

Copy `src/rag/pricing.py` to `azure/rag/pricing.py`, rewrite imports, and
point its price-table path at `azure/config/model_prices.json`.

> The `null` prices are deliberate. Azure pricing differs from the OpenAI API's
> and varies by region — inventing a number would violate CLAUDE.md §10. Token
> counts are still recorded and displayed; only the money figure is withheld.

- [ ] **Step 5: Copy metrics, serialize and memory**

```bash
cp src/rag/metrics.py   azure/rag/metrics.py
cp src/rag/serialize.py azure/rag/serialize.py
cp src/rag/memory.py    azure/rag/memory.py
```

Then:

- Rewrite `from src.rag.` → `from azure.rag.`
- In `metrics.py`, drop the `peak_cpu_percent`, `peak_ram_mb` and `gpu_vram_mb`
  columns and their `record()` parameters
- In `serialize.py`, delete `evaluation_payload` and any key/provider payload
  helper; drop the `resources` key from `answer_payload`
- Keep every remaining JSON key **exactly** as it is — Task 13's client
  depends on the camelCase names

`memory.py` is copied unchanged apart from imports: it holds `Turn`,
`ConversationMemory` and `retrieval_query`, and none of that is
provider-specific.

- [ ] **Step 6: Write the reduced session state**

> ⚠️ **Controller ruling (pre-flight scan).** The session helpers live in
> `ui_state.py`, **not** `memory.py` — verified against
> `src/rag/ui_state.py`, which defines `get_memory`, `set_user_name`,
> `get_user_name`, `get_transcript`, `add_to_transcript` and `clear_chat`.
> An earlier draft of this plan placed them in `memory.py`. Task 10 imports
> them from `azure.rag.ui_state`.

Copy `src/rag/ui_state.py` to `azure/rag/ui_state.py`, rewrite its imports,
and **keep only** these six functions:

```
get_memory, get_transcript, add_to_transcript, clear_chat,
get_user_name, set_user_name
```

Delete everything else — the credential store (`get_store`, `set_key`,
`provider_status`, `ProviderStatus`), model switching (`available_models`,
`set_active_model`, `active_model`), the Ollama helpers (`format_size`,
`suggested_models`, `pull_label`), evaluation (`estimate_eval_cost`,
`comparison_rows`), and the resource formatters (`format_ram`, `format_gpu`,
`format_percent`).

Keep any display formatter that `serialize.py` still imports. Verify with:

```bash
python -c "
from azure.rag.ui_state import (
    get_memory, get_transcript, add_to_transcript,
    clear_chat, get_user_name, set_user_name,
)
import azure.rag.serialize, azure.rag.api  # noqa: F401 — import-time check
print('ok')
"
```

(The `azure.rag.api` import only works after Task 10; before then, drop it
from the check.)

- [ ] **Step 7: Run the tests and verify they pass**

Run: `pytest azure/tests/test_support_modules.py -v`
Expected: 7 passed

- [ ] **Step 8: Attach the metrics store to the agent**

In `azure/rag/build.py`, add the import and pass the store:

```python
from azure.rag.metrics import MetricsStore
```

```python
    return Agent(
        retriever,
        ToolBox(retriever),
        AzureOpenAIClient(config),
        config.max_tool_turns,
        metrics=MetricsStore(config.storage_dir / "metrics.db"),
    )
```

- [ ] **Step 9: Verify the agent still builds end to end**

```bash
python -c "
import sys
sys.stdout.reconfigure(encoding='utf-8')
from azure.rag.build import build_agent
answer = build_agent().answer('Araç yakıt limiti ne kadar?')
print('citations:', answer.citations)
print('tokens:', answer.usage.input_tokens, answer.usage.output_tokens)
print('has table value:', '1.500' in answer.text)
"
```

Expected: at least one citation and a non-empty answer. This is the first
full-stack run against Azure OpenAI — record the output in the commit message.

- [ ] **Step 10: Confirm the local path is untouched**

```bash
git status --short src/ tests/ gradio_app.py docker-compose.yml
```

Expected: no output.

- [ ] **Step 11: Quality gate**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 12: Commit**

```bash
git add azure/
git commit -m "feat(azure): add metrics, pricing, catalog and session state"
```
