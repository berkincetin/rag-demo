# Task 1: Provisioning and Configuration

**Goal:** Deploy `text-embedding-3-small`, confirm the API version empirically,
and create the Azure configuration module.

**Files:**
- Create: `azure/__init__.py`, `azure/rag/__init__.py`
- Create: `azure/rag/config.py`
- Create: `azure/tests/__init__.py`, `azure/tests/test_config.py`
- Create: `azure/.env.example`

**Interfaces:**
- Consumes: nothing (first task)
- Produces:
  ```python
  @dataclass(frozen=True)
  class AzureConfig:
      openai_endpoint: str
      openai_api_key: str | None
      api_version: str
      chat_deployment: str
      embedding_deployment: str
      storage_dir: Path
      data_dir: Path
      top_k: int
      min_cosine: float
      min_bm25: float
      max_tool_turns: int
      internal_token: str | None

      @classmethod
      def load(cls) -> "AzureConfig": ...
  ```

---

- [ ] **Step 1: Verify the embedding model is deployable**

```bash
az cognitiveservices account list-models \
  -n foundry-lab-hbc26 -g foundry-lab-rg \
  --query "[?name=='text-embedding-3-small'].{name:name,version:version,format:format}" -o table
```

Expected: one row, `text-embedding-3-small  1  OpenAI`.

If empty, stop and report — the rest of the plan depends on this model.

- [ ] **Step 2: Deploy the embedding model**

```bash
az cognitiveservices account deployment create \
  -n foundry-lab-hbc26 -g foundry-lab-rg \
  --deployment-name text-embedding-3-small \
  --model-name text-embedding-3-small \
  --model-version 1 \
  --model-format OpenAI \
  --sku-name Standard \
  --sku-capacity 50
```

If this fails with a quota error, report the exact message. Do not silently
fall back to a different model — the spec's §6 calibration assumes this one.

- [ ] **Step 3: Confirm both deployments exist**

```bash
az cognitiveservices account deployment list \
  -n foundry-lab-hbc26 -g foundry-lab-rg \
  --query "[].{name:name,model:properties.model.name}" -o table
```

Expected: two rows — `gpt-4.1-mini` and `text-embedding-3-small`.
The `gpt-4.1-mini` row must be unchanged.

- [ ] **Step 4: Determine the working API version empirically**

Do not guess this value. Fetch the key and probe:

```bash
KEY=$(az cognitiveservices account keys list -n foundry-lab-hbc26 -g foundry-lab-rg --query key1 -o tsv)

for V in 2024-10-21 2024-12-01-preview 2025-01-01-preview; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    "https://foundry-lab-hbc26.openai.azure.com/openai/deployments/text-embedding-3-small/embeddings?api-version=$V" \
    -H "api-key: $KEY" -H "Content-Type: application/json" \
    -d '{"input":"deneme"}')
  echo "$V -> $CODE"
done
```

Record the **oldest version that returns 200**. That is `API_VERSION` for the
rest of the plan. Write the observed output into the commit message.

- [ ] **Step 5: Write the failing config test**

Create `azure/tests/test_config.py`:

```python
"""Configuration loading for the Azure deployment."""

import pytest

from azure.rag.config import AzureConfig


def test_load_reads_endpoint_and_deployments(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "secret")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    config = AzureConfig.load()

    assert config.openai_endpoint == "https://example.openai.azure.com/"
    assert config.openai_api_key == "secret"
    assert config.chat_deployment == "gpt-4.1-mini"
    assert config.embedding_deployment == "text-embedding-3-small"


def test_thresholds_have_no_silent_default():
    """The e5 thresholds are invalid for text-embedding-3-small.

    Task 8 measures real values. Until then the defaults must be explicit
    placeholders that a reader cannot mistake for calibrated numbers.
    """
    assert AzureConfig.load().min_cosine != 0.80
```

- [ ] **Step 6: Run the tests and watch them fail**

Run: `pytest azure/tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'azure.rag'`

- [ ] **Step 7: Create the package files**

`azure/__init__.py` and `azure/rag/__init__.py` and `azure/tests/__init__.py`
are empty files.

> ⚠️ Naming note: the `azure` name shadows the PyPI `azure-*` namespace
> packages. This project does not install any `azure-*` SDK (it talks to
> Azure OpenAI over plain HTTP via the `openai` package), so there is no
> conflict. Do not add `azure-identity` or similar without revisiting this.

- [ ] **Step 8: Write the config module**

Create `azure/rag/config.py`:

```python
"""Environment-backed configuration for the Azure deployment.

Separate from src/rag/config.py on purpose: this deployment has no Ollama,
no local embedding model, and no session-scoped API keys. Its credentials
come from Container Apps secrets injected as environment variables.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Placeholder thresholds. Task 8 replaces these with measured values.
# They are deliberately NOT the e5 numbers (0.80 / 5.0): those were
# calibrated against a different embedding model and are invalid here.
_UNCALIBRATED_COSINE = -1.0
_UNCALIBRATED_BM25 = -1.0


@dataclass(frozen=True)
class AzureConfig:
    """Runtime settings for the cloud-only deployment."""

    openai_endpoint: str
    openai_api_key: str | None
    api_version: str
    chat_deployment: str
    embedding_deployment: str
    storage_dir: Path
    data_dir: Path
    top_k: int
    min_cosine: float
    min_bm25: float
    max_tool_turns: int
    internal_token: str | None

    @classmethod
    def load(cls) -> "AzureConfig":
        """Build a config from environment variables."""
        load_dotenv()
        return cls(
            openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY") or None,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            chat_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini"),
            embedding_deployment=os.getenv(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
            ),
            storage_dir=Path(os.getenv("STORAGE_DIR", "./azure/storage")),
            data_dir=Path(os.getenv("DATA_DIR", "./data")),
            top_k=int(os.getenv("TOP_K", "5")),
            min_cosine=float(os.getenv("MIN_COSINE", str(_UNCALIBRATED_COSINE))),
            min_bm25=float(os.getenv("MIN_BM25", str(_UNCALIBRATED_BM25))),
            max_tool_turns=int(os.getenv("MAX_TOOL_TURNS", "3")),
            internal_token=os.getenv("INTERNAL_TOKEN") or None,
        )
```

Replace `2024-10-21` with the version measured in Step 4 if it differs.

- [ ] **Step 9: Run the tests and verify they pass**

Run: `pytest azure/tests/test_config.py -v`
Expected: 2 passed

- [ ] **Step 10: Write `azure/.env.example`**

```bash
# Azure OpenAI — the key comes from a Container Apps secret in production
AZURE_OPENAI_ENDPOINT=https://foundry-lab-hbc26.openai.azure.com/
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small

# Retrieval gate — MEASURED in Task 8, do not invent values
MIN_COSINE=
MIN_BM25=

# Tier-to-tier authentication
INTERNAL_TOKEN=

DATA_DIR=./data
STORAGE_DIR=./azure/storage
```

- [ ] **Step 11: Confirm the local path is untouched**

```bash
git status --short src/ tests/ gradio_app.py docker-compose.yml
```

Expected: **no output**. If anything appears, revert it before committing.

- [ ] **Step 12: Quality gate**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 13: Commit**

```bash
git add azure/ docs/superpowers/plans/azure-deployment/ docs/superpowers/specs/
git commit -m "feat(azure): add cloud config module and deploy embedding model"
```
