"""HTTP API behind the Next.js tier.

This app has no public route: Container Apps gives it internal ingress, so the
only caller is the web tier inside the environment. `X-Internal-Token` is the
second layer — network isolation alone would still trust every sibling
container in the environment.

No CORS middleware: the browser never talks to this service directly, so there
is no cross-origin request to permit.

Deliberately absent, compared with src/rag/api.py:
  /api/keys*        — one server-held provider, so key entry is pure attack surface
  /api/ollama*      — no local models here
  /api/evaluation/* — 13 cases x N models per call is a cost-amplification endpoint
  DELETE /api/metrics — destructive and unnecessary for a demo

Run with:  uvicorn azure.rag.api:app --host 0.0.0.0 --port 8000
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

# docs_url/redoc_url disabled: an internal service does not need to publish an
# interactive schema, and it is one less thing to reach if ingress is ever
# misconfigured.
app = FastAPI(title="Nobel RAG API", version="1.0", docs_url=None, redoc_url=None)

_SESSIONS: dict[str, dict[str, Any]] = {}
_AGENT: Any = None

# Per-session rate limit. In-memory, therefore per-replica: effective for this
# deployment's traffic, approximate under multi-replica scale. A shared store
# would be required for a production guarantee.
_RATE_LIMIT_REQUESTS = 20
_RATE_LIMIT_WINDOW_SECONDS = 60
_REQUEST_LOG: dict[str, list[float]] = defaultdict(list)


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    """Reject anything that is not the web tier.

    Compared with `hmac.compare_digest` rather than `==` so the check does not
    leak the token's prefix through response timing.
    """
    expected = os.environ.get("INTERNAL_TOKEN", "")
    if not expected or not x_internal_token:
        raise HTTPException(status_code=401, detail="Yetkisiz istek.")
    if not hmac.compare_digest(x_internal_token, expected):
        raise HTTPException(status_code=401, detail="Yetkisiz istek.")


def _session(session_id: str | None) -> dict[str, Any]:
    return _SESSIONS.setdefault(session_id or "default", {})


def _agent():
    """Built once — each build loads the index from disk."""
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
    answer = _agent().answer(question, memory=get_memory(session), user_name=get_user_name(session))
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
    """Probe endpoint. Deliberately reveals nothing about the deployment.

    Exempt from the token so Container Apps health probes can reach it.
    """
    return {"ok": True}
