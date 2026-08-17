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
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from azure.rag.build import build_agent
from azure.rag.catalog import list_models
from azure.rag.config import AzureConfig
from azure.rag.embedder import AzureOpenAIEmbedder
from azure.rag.loaders import UPLOAD_SUFFIXES
from azure.rag.memory import ConversationMemory
from azure.rag.metrics import MetricsStore
from azure.rag.pricing import estimate_cost
from azure.rag.serialize import answer_payload, model_payload, run_payload, summary_payload
from azure.rag.streaming import answer_events, format_sse

# Session helpers live in ui_state, mirroring src/rag/ui_state.py.
from azure.rag.ui_state import (
    add_to_transcript,
    clear_chat,
    get_memory,
    get_user_name,
    set_user_name,
)
from azure.rag.upload_search import UploadAwareRetriever
from azure.rag.uploads import MAX_FILE_BYTES, UploadLimitError, UploadStore, build_uploaded_doc

# docs_url/redoc_url disabled: an internal service does not need to publish an
# interactive schema, and it is one less thing to reach if ingress is ever
# misconfigured.
app = FastAPI(title="Nobel RAG API", version="1.0", docs_url=None, redoc_url=None)

_SESSIONS: dict[str, dict[str, Any]] = {}
_AGENT: Any = None
_EMBEDDER: Any = None

# Uploaded documents live here and nowhere else: in memory, per replica, and
# only until the TTL expires. Nothing is written to disk.
_UPLOADS = UploadStore()

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


def _embedder():
    """Built once; the upload path is the only caller in this process."""
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = AzureOpenAIEmbedder(AzureConfig.load())
    return _EMBEDDER


def _upload_key(session_id: str, conversation_id: str) -> str:
    """Namespaced so one session can never read another's uploads."""
    return f"{session_id}:{conversation_id}"


def _document_list(docs) -> list[dict[str, Any]]:
    return [{"filename": doc.filename, "chunkCount": len(doc.chunks)} for doc in docs]


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


class StreamAskRequest(BaseModel):
    question: str
    userName: str | None = None
    conversationId: str | None = None
    # Client-owned conversation state: the browser holds N conversations per
    # session, so the server cannot key memory by session alone.
    summary: str | None = None
    history: list[dict[str, str]] | None = None


def _memory_from_client(
    summary: str | None, history: list[dict[str, str]] | None
) -> ConversationMemory:
    """Rebuild a ConversationMemory from what the browser sent.

    Only completed question/answer pairs become turns: a trailing user message
    with no answer yet is the question being asked right now, not history.
    """
    memory = ConversationMemory()
    question: str | None = None
    for message in history or []:
        role = message.get("role")
        if role == "user":
            question = message.get("content", "")
        elif role == "assistant" and question is not None:
            memory.add(question, message.get("content", ""))
            question = None
    return memory


def _answer_for(session_id, conversation_id, question, memory, session):
    """Answer, widening retrieval to this conversation's uploads when it has any.

    The graph itself is untouched: only the retriever it is built around
    changes. Recompiling the state machine is cheap — the loaded index and the
    LLM client are shared, not rebuilt.
    """
    agent = _agent()
    key = _upload_key(session_id, conversation_id or "default")
    if not _UPLOADS.get(key):
        return agent.answer(question, memory=memory, user_name=get_user_name(session))

    from azure.rag.agent import Agent
    from azure.rag.tools import ToolBox

    wrapped = UploadAwareRetriever(agent.retriever, key, _UPLOADS)
    scoped = Agent(
        wrapped,
        ToolBox(wrapped),
        agent.llm,
        agent.max_tool_turns,
        metrics=agent.metrics,
    )
    return scoped.answer(question, memory=memory, user_name=get_user_name(session))


@app.post("/api/ask/stream", dependencies=[Depends(require_internal_token)])
def ask_stream(body: StreamAskRequest, x_session_id: str | None = Header(default=None)):
    """Answer as a stream of SSE events.

    The agent graph is unchanged; `answer_events` runs it on a worker thread and
    turns the text deltas the LLM client publishes into `token` events.
    """
    session_id = x_session_id or "default"
    _check_rate_limit(session_id)

    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")

    session = _session(session_id)
    set_user_name(session, body.userName or "")
    memory = _memory_from_client(body.summary, body.history)
    model_id = list_models()[0].id

    def run(_emit):
        answer = _answer_for(session_id, body.conversationId, question, memory, session)
        return {"text": answer.text, "citations": list(answer.citations), "answer": answer}

    def on_meta(result):
        answer = result.get("answer")
        if answer is None:
            return {"citations": [], "grounded": False, "modelId": model_id}
        cost = estimate_cost(model_id, answer.usage.input_tokens, answer.usage.output_tokens)
        payload = answer_payload(answer, cost)
        payload["modelId"] = model_id
        return payload

    def body_stream():
        for event in answer_events(run, on_meta=on_meta):
            yield format_sse(event)

    return StreamingResponse(
        body_stream(),
        media_type="text/event-stream",
        # Without these an intermediary may buffer the whole body and the
        # stream arrives as one lump.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat/clear", dependencies=[Depends(require_internal_token)])
def clear(x_session_id: str | None = Header(default=None)):
    clear_chat(_session(x_session_id))
    return {"ok": True}


# --- uploaded documents ------------------------------------------------------


@app.post("/api/documents/upload", dependencies=[Depends(require_internal_token)])
async def upload_document(
    # Annotated form rather than `= File(...)`: a call in an argument default
    # trips ruff's B008.
    file: Annotated[UploadFile, File()],
    conversation_id: Annotated[str, Form()],
    x_session_id: str | None = Header(default=None),
):
    """Parse and embed one file, keeping only its chunks in memory.

    The bytes exist on disk for exactly as long as the parser needs a path, and
    are removed before this returns.
    """
    session_id = x_session_id or "default"
    _check_rate_limit(session_id)

    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail="Yalnızca .pdf, .docx, .xlsx ve .txt dosyaları yüklenebilir.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Dosya boş.")
    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Dosya 10 MB sınırını aşıyor.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(contents)
        temp_path = Path(handle.name)
    try:
        doc = build_uploaded_doc(temp_path, _embedder())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        os.remove(temp_path)

    # The temp file's generated name must not leak into citations.
    doc.filename = filename
    key = _upload_key(session_id, conversation_id)
    try:
        _UPLOADS.add(key, doc)
    except UploadLimitError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error

    return {
        "filename": filename,
        "chunkCount": len(doc.chunks),
        "documents": _document_list(_UPLOADS.get(key)),
    }


@app.get("/api/documents", dependencies=[Depends(require_internal_token)])
def list_uploaded(conversation_id: str, x_session_id: str | None = Header(default=None)):
    key = _upload_key(x_session_id or "default", conversation_id)
    return {"documents": _document_list(_UPLOADS.get(key))}


@app.delete("/api/documents", dependencies=[Depends(require_internal_token)])
def delete_uploaded(
    conversation_id: str,
    filename: str | None = None,
    x_session_id: str | None = Header(default=None),
):
    """Drop one document, or the whole conversation when no filename is given.

    The second form is what the front-end calls when a conversation is deleted:
    its uploads must not outlive it, TTL or no TTL.
    """
    key = _upload_key(x_session_id or "default", conversation_id)
    if filename is None:
        _UPLOADS.clear(key)
        return {"documents": []}
    return {"documents": _document_list(_UPLOADS.remove(key, filename))}


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
