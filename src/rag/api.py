"""HTTP API behind the Next.js front-end.

Routing and wiring only — every JSON shape comes from `serialize.py`, which is
tested directly. Excluded from coverage for the same reason `gradio_app.py` is.

Session model: the browser sends an `X-Session-Id` header; each session gets a
plain dict held in memory, handed to the same `ui_state` helpers the Gradio app
uses. API keys therefore live only in this process's memory and never reach
disk (ADR-012), exactly as before.

Run with:  uvicorn src.rag.api:app --port 8000
"""

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.rag.catalog import providers
from src.rag.cli import build_agent
from src.rag.config import Config
from src.rag.evaluation import evaluate, load_eval_set
from src.rag.metrics import MetricsStore
from src.rag.ollama_admin import OllamaAdmin, OllamaUnavailable
from src.rag.pricing import estimate_cost
from src.rag.serialize import (
    answer_payload,
    evaluation_payload,
    model_payload,
    run_payload,
    summary_payload,
)
from src.rag.ui_state import (
    active_model,
    add_to_transcript,
    available_models,
    clear_chat,
    estimate_eval_cost,
    get_memory,
    get_store,
    get_user_name,
    provider_status,
    set_active_model,
    set_key,
    set_user_name,
)

app = FastAPI(title="RAG Agent API", version="1.0")

# The front-end is always a different origin (:3000 vs :8000), in Docker too —
# the browser talks to both from the host, so the container names never appear
# here. Override with CORS_ORIGINS when serving from somewhere else.
_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _ORIGINS if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

_SESSIONS: dict[str, dict[str, Any]] = {}
_AGENTS: dict[tuple[str, str], Any] = {}


def _session(session_id: str | None) -> dict[str, Any]:
    return _SESSIONS.setdefault(session_id or "default", {})


def _local_names() -> list[str]:
    try:
        return [model.name for model in OllamaAdmin().list_local()]
    except OllamaUnavailable:
        return []


def _agent_for(session: dict, model_id: str):
    # Cached per (model, which providers have keys) — rebuilding would reload
    # the 1.1 GB embedding model on every question.
    fingerprint = ",".join(get_store(session).providers_with_keys())
    key = (model_id, fingerprint)
    if key not in _AGENTS:
        _AGENTS[key] = build_agent(model_id=model_id, session=session)
    return _AGENTS[key]


def _store() -> MetricsStore:
    return MetricsStore(Config.load().storage_dir / "metrics.db")


# --- chat -------------------------------------------------------------------


class AskRequest(BaseModel):
    question: str
    userName: str | None = None


@app.post("/api/ask")
def ask(body: AskRequest, x_session_id: str | None = Header(default=None)):
    session = _session(x_session_id)
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")

    set_user_name(session, body.userName or "")
    model = active_model(session, _local_names(), preferred=Config.load().llm_model)
    if model is None:
        raise HTTPException(
            status_code=409,
            detail="Kullanılabilir model yok. Bir API anahtarı girin veya Ollama'yı başlatın.",
        )

    agent = _agent_for(session, model.id)
    answer = agent.answer(question, memory=get_memory(session), user_name=get_user_name(session))
    add_to_transcript(session, question, answer.text)

    cost = estimate_cost(model.id, answer.usage.input_tokens, answer.usage.output_tokens)
    payload = answer_payload(answer, cost)
    payload["modelId"] = model.id

    resources = getattr(agent, "_last_resources", None)
    payload["resources"] = (
        None
        if resources is None
        else {
            "peakCpuPercent": resources.peak_cpu_percent,
            "peakRamMb": resources.peak_ram_mb,
            "gpuVramMb": resources.gpu_vram_mb,
        }
    )
    return payload


@app.post("/api/chat/clear")
def clear(x_session_id: str | None = Header(default=None)):
    clear_chat(_session(x_session_id))
    return {"ok": True}


# --- providers and models ---------------------------------------------------


@app.get("/api/models")
def models(x_session_id: str | None = Header(default=None)):
    session = _session(x_session_id)
    local = _local_names()
    current = active_model(session, local, preferred=Config.load().llm_model)
    return {
        "models": [model_payload(m) for m in available_models(session, local)],
        "activeId": current.id if current else None,
        "ollamaAvailable": bool(local),
    }


class KeyRequest(BaseModel):
    provider: str
    key: str


@app.post("/api/keys")
def save_key(body: KeyRequest, x_session_id: str | None = Header(default=None)):
    session = _session(x_session_id)
    if body.provider not in providers():
        raise HTTPException(status_code=400, detail=f"Bilinmeyen sağlayıcı: {body.provider}")
    set_key(session, body.provider, body.key)
    return provider_state(x_session_id)


@app.get("/api/keys")
def provider_state(x_session_id: str | None = Header(default=None)):
    session = _session(x_session_id)
    return {
        "providers": [
            {"provider": name, "configured": status.configured, "masked": status.masked}
            for name, status in provider_status(session).items()
        ]
    }


class ModelRequest(BaseModel):
    modelId: str


@app.post("/api/models/active")
def choose_model(body: ModelRequest, x_session_id: str | None = Header(default=None)):
    session = _session(x_session_id)
    try:
        set_active_model(session, body.modelId, local_models=_local_names())
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    # A model with no price is usable; the UI just cannot show a cost for it.
    return {
        "activeId": body.modelId,
        "priced": estimate_cost(body.modelId, 1000, 100) is not None,
    }


# --- local (Ollama) models --------------------------------------------------


@app.get("/api/ollama")
def ollama_models():
    admin = OllamaAdmin()
    if not admin.is_available():
        return {"available": False, "baseUrl": admin.base_url, "models": []}
    return {
        "available": True,
        "baseUrl": admin.base_url,
        "models": [{"name": m.name, "sizeBytes": m.size_bytes} for m in admin.list_local()],
    }


class PullRequest(BaseModel):
    name: str


@app.post("/api/ollama/pull")
def pull_model(body: PullRequest):
    try:
        OllamaAdmin().pull(body.name)
    except OllamaUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"ok": True, "name": body.name}


@app.post("/api/ollama/delete")
def delete_model(body: PullRequest):
    try:
        OllamaAdmin().delete(body.name)
    except OllamaUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"ok": True, "name": body.name}


# --- metrics ----------------------------------------------------------------


@app.get("/api/metrics")
def metrics():
    store = _store()
    return {
        "summaries": [summary_payload(s) for s in store.summary_by_model()],
        "runs": [run_payload(r) for r in store.recent()],
    }


@app.delete("/api/metrics")
def clear_metrics():
    _store().clear()
    return {"ok": True}


# --- evaluation -------------------------------------------------------------


@app.get("/api/evaluation/cases")
def eval_cases():
    cases = load_eval_set()
    return {"count": len(cases)}


class EvalRequest(BaseModel):
    modelIds: list[str]


@app.post("/api/evaluation/estimate")
def eval_estimate(body: EvalRequest):
    cases = len(load_eval_set())
    known, unknown = 0.0, []
    for model_id in body.modelIds:
        estimate = estimate_eval_cost(model_id, cases)
        if estimate is None:
            unknown.append(model_id)
        else:
            known += estimate
    return {"cases": cases, "knownCostUsd": known, "unpricedModels": unknown}


@app.post("/api/evaluation/run")
def run_evaluation(body: EvalRequest, x_session_id: str | None = Header(default=None)):
    session = _session(x_session_id)
    if not body.modelIds:
        raise HTTPException(status_code=400, detail="En az bir model seçin.")
    cases = load_eval_set()
    results = [
        evaluate(build_agent(Config.load(), model_id=model_id, session=session), cases)
        for model_id in body.modelIds
    ]
    return {"results": evaluation_payload(results)}


@app.get("/api/health")
def health():
    return {"ok": True}
