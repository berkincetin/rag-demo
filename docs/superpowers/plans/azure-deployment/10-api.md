# Task 10: FastAPI Backend

**Goal:** The HTTP API with a reduced endpoint surface, internal-token
authentication, and per-session rate limiting.

**Files:**
- Create: `azure/rag/api.py`
- Create: `azure/tests/test_api.py`

**Interfaces:**
- Consumes: `build_agent` (Task 7/9), `serialize` helpers (Task 9)
- Produces: the HTTP contract Task 13's proxy calls
  ```
  POST   /api/ask          {question, userName} → answer payload
  POST   /api/chat/clear                        → {ok}
  GET    /api/models                            → {models, activeId}
  GET    /api/metrics                           → {summaries, runs}
  GET    /api/health                            → {ok}
  ```
  All except `/api/health` require `X-Internal-Token`.

---

## Security requirements

| Requirement | Implementation |
|---|---|
| Only the web tier may call this | `X-Internal-Token` compared in constant time |
| No key-entry surface | `/api/keys*` not defined |
| No local-model surface | `/api/ollama*` not defined |
| No cost amplification | `/api/evaluation/*` not defined |
| No destructive endpoint | `DELETE /api/metrics` not defined |
| No CORS | the browser never calls this directly |
| Bounded cost per session | rate limit on `/api/ask` |

`/api/health` is exempt from the token so Container Apps probes can reach it.
It returns only `{"ok": true}` — no version, no configuration, no build info.

- [ ] **Step 1: Write the failing security tests**

Create `azure/tests/test_api.py`:

```python
"""API contract and security. The token check is the tier boundary."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("INTERNAL_TOKEN", "secret-token")
    monkeypatch.setenv("MIN_COSINE", "0.5")
    monkeypatch.setenv("MIN_BM25", "5.0")

    from azure.rag import api

    return TestClient(api.app)


AUTH = {"X-Internal-Token": "secret-token", "X-Session-Id": "s1"}


def test_health_needs_no_token(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_health_leaks_no_configuration(client):
    """A probe endpoint must not describe the deployment."""
    body = client.get("/api/health").json()

    assert set(body) == {"ok"}


def test_ask_without_token_is_rejected(client):
    response = client.post("/api/ask", json={"question": "soru"})

    assert response.status_code == 401


def test_ask_with_wrong_token_is_rejected(client):
    response = client.post(
        "/api/ask", json={"question": "soru"}, headers={"X-Internal-Token": "wrong"}
    )

    assert response.status_code == 401


def test_metrics_without_token_is_rejected(client):
    assert client.get("/api/metrics").status_code == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/keys"),
        ("get", "/api/keys"),
        ("get", "/api/ollama"),
        ("post", "/api/ollama/pull"),
        ("post", "/api/evaluation/run"),
        ("delete", "/api/metrics"),
    ],
)
def test_removed_endpoints_do_not_exist(client, method, path):
    """These carried key-entry, local-model and cost-amplification surface."""
    response = getattr(client, method)(path, headers=AUTH)

    assert response.status_code in (404, 405)


def test_empty_question_is_rejected(client):
    response = client.post("/api/ask", json={"question": "   "}, headers=AUTH)

    assert response.status_code == 400
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `pytest azure/tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'azure.rag.api'`

- [ ] **Step 3: Write the API**

Create `azure/rag/api.py`:

```python
"""HTTP API behind the Next.js tier.

This app has no public route: Container Apps gives it internal ingress, so the
only caller is the web tier inside the environment. `X-Internal-Token` is the
second layer — network isolation alone would still trust every sibling
container in the environment.

No CORS middleware: the browser never talks to this service directly, so there
is no cross-origin request to permit.
"""

import hmac
import os
import time
from collections import defaultdict
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from azure.rag.build import build_agent
from azure.rag.catalog import list_models
from azure.rag.config import AzureConfig
from azure.rag.metrics import MetricsStore
from azure.rag.pricing import estimate_cost
from azure.rag.serialize import answer_payload, model_payload, run_payload, summary_payload

# Session helpers live in ui_state, mirroring src/rag/ui_state.py.
from azure.rag.ui_state import (
    add_to_transcript,
    clear_chat,
    get_memory,
    get_user_name,
    set_user_name,
)

app = FastAPI(title="Nobel RAG API", version="1.0", docs_url=None, redoc_url=None)

_SESSIONS: dict[str, dict[str, Any]] = {}
_AGENT: Any = None

# Per-session rate limit. In-memory, therefore per-replica: effective for this
# deployment's traffic, approximate under multi-replica scale.
_RATE_LIMIT_REQUESTS = 20
_RATE_LIMIT_WINDOW_SECONDS = 60
_REQUEST_LOG: dict[str, list[float]] = defaultdict(list)


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    """Reject anything that is not the web tier."""
    expected = os.environ.get("INTERNAL_TOKEN", "")
    if not expected or not x_internal_token:
        raise HTTPException(status_code=401, detail="Yetkisiz istek.")
    if not hmac.compare_digest(x_internal_token, expected):
        raise HTTPException(status_code=401, detail="Yetkisiz istek.")


def _session(session_id: str | None) -> dict[str, Any]:
    return _SESSIONS.setdefault(session_id or "default", {})


def _agent():
    """Built once: each build loads the index from disk."""
    global _AGENT
    if _AGENT is None:
        _AGENT = build_agent()
    return _AGENT


def _store() -> MetricsStore:
    return MetricsStore(AzureConfig.load().storage_dir / "metrics.db")


def _check_rate_limit(session_id: str) -> None:
    now = time.monotonic()
    recent = [t for t in _REQUEST_LOG[session_id] if now - t < _RATE_LIMIT_WINDOW_SECONDS]
    if len(recent) >= _RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail="Çok fazla istek. Biraz bekleyin.")
    recent.append(now)
    _REQUEST_LOG[session_id] = recent


class AskRequest(BaseModel):
    question: str
    userName: str | None = None


@app.post("/api/ask", dependencies=[Depends(require_internal_token)])
def ask(body: AskRequest, x_session_id: str | None = Header(default=None)):
    session_id = x_session_id or "default"
    _check_rate_limit(session_id)

    session = _session(session_id)
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")

    set_user_name(session, body.userName or "")
    agent = _agent()
    answer = agent.answer(
        question, memory=get_memory(session), user_name=get_user_name(session)
    )
    add_to_transcript(session, question, answer.text)

    model_id = list_models()[0].id
    cost = estimate_cost(model_id, answer.usage.input_tokens, answer.usage.output_tokens)
    payload = answer_payload(answer, cost)
    payload["modelId"] = model_id
    return payload


@app.post("/api/chat/clear", dependencies=[Depends(require_internal_token)])
def clear(x_session_id: str | None = Header(default=None)):
    clear_chat(_session(x_session_id))
    return {"ok": True}


@app.get("/api/models", dependencies=[Depends(require_internal_token)])
def models():
    available = list_models()
    return {
        "models": [model_payload(model) for model in available],
        "activeId": available[0].id,
    }


@app.get("/api/metrics", dependencies=[Depends(require_internal_token)])
def metrics():
    store = _store()
    return {
        "summaries": [summary_payload(s) for s in store.summary_by_model()],
        "runs": [run_payload(r) for r in store.recent()],
    }


@app.get("/api/health")
def health():
    """Probe endpoint. Deliberately reveals nothing about the deployment."""
    return {"ok": True}
```

- [ ] **Step 4: Run the tests and verify they pass**

Run: `pytest azure/tests/test_api.py -v`
Expected: 11 passed

If `/api/ask` fails because the index is missing, the test needs the Task 8
index present. Build it first; do not mock the agent away — the token checks
must run against the real routing.

- [ ] **Step 5: Verify the rate limiter**

Add and run this test in the same file:

```python
def test_rate_limit_returns_429(client, monkeypatch):
    from azure.rag import api

    monkeypatch.setattr(api, "_RATE_LIMIT_REQUESTS", 2)
    api._REQUEST_LOG.clear()

    for _ in range(2):
        client.post("/api/ask", json={"question": "  "}, headers=AUTH)
    response = client.post("/api/ask", json={"question": "  "}, headers=AUTH)

    assert response.status_code == 429
```

Expected: PASS. Note it asserts 429 wins over the 400 for a blank question,
which confirms the limiter runs before request validation.

- [ ] **Step 6: Run the server and probe it manually**

```bash
INTERNAL_TOKEN=test uvicorn azure.rag.api:app --port 8001 &
sleep 3
curl -s localhost:8001/api/health
curl -s -o /dev/null -w "no token: %{http_code}\n" -X POST localhost:8001/api/ask \
  -H "Content-Type: application/json" -d '{"question":"test"}'
curl -s -X POST localhost:8001/api/ask -H "X-Internal-Token: test" \
  -H "X-Session-Id: s1" -H "Content-Type: application/json" \
  -d '{"question":"Araç yakıt limiti ne kadar?"}'
```

Expected: `{"ok":true}`, then `no token: 401`, then an answer with citations.

- [ ] **Step 7: Confirm the local path is untouched**

```bash
git status --short src/ tests/ gradio_app.py docker-compose.yml
```

Expected: no output.

- [ ] **Step 8: Quality gate**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 9: Commit**

```bash
git add azure/
git commit -m "feat(azure): add FastAPI backend with internal token auth and rate limiting"
```
