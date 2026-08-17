"""API contract and security. The internal token is the tier boundary.

The agent is stubbed so these tests exercise routing and auth without calling
Azure OpenAI. Nothing here asserts on model output text.
"""

import json

import pytest
from fastapi.testclient import TestClient

from azure.rag.models import Answer, TokenUsage

AUTH = {"X-Internal-Token": "secret-token", "X-Session-Id": "s1"}


class StubAgent:
    """Stands in for the real agent; records what it was asked."""

    def __init__(self) -> None:
        self.questions: list[str] = []

    def answer(self, question, memory=None, user_name=None) -> Answer:
        self.questions.append(question)
        return Answer(
            text="Aylık yakıt limiti 1.500 TL/ay'dır [1].",
            citations=["arac.docx — 3. ARAC TAHSIS POLITIKASI"],
            usage=TokenUsage(100, 20),
            latency_ms=12,
        )


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("INTERNAL_TOKEN", "secret-token")
    monkeypatch.setenv("AZURE_STORAGE_DIR", str(tmp_path))

    from azure.rag import api

    api._SESSIONS.clear()
    api._REQUEST_LOG.clear()
    monkeypatch.setattr(api, "_AGENT", StubAgent())
    return TestClient(api.app)


# --- health ------------------------------------------------------------------


def test_health_needs_no_token(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_health_leaks_no_configuration(client):
    """A probe endpoint must not describe the deployment."""
    assert set(client.get("/api/health").json()) == {"ok"}


# --- the tier boundary -------------------------------------------------------


def test_ask_without_a_token_is_rejected(client):
    response = client.post("/api/ask", json={"question": "soru"})

    assert response.status_code == 401


def test_ask_with_the_wrong_token_is_rejected(client):
    response = client.post(
        "/api/ask", json={"question": "soru"}, headers={"X-Internal-Token": "wrong"}
    )

    assert response.status_code == 401


def test_every_data_endpoint_requires_the_token(client):
    assert client.get("/api/metrics").status_code == 401
    assert client.get("/api/models").status_code == 401
    assert client.post("/api/chat/clear").status_code == 401


def test_rejection_happens_before_the_agent_runs(client, monkeypatch):
    """An unauthenticated request must not reach the model — that would bill."""
    from azure.rag import api

    stub = StubAgent()
    monkeypatch.setattr(api, "_AGENT", stub)

    client.post("/api/ask", json={"question": "soru"})

    assert stub.questions == []


# --- removed attack surface --------------------------------------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/keys"),
        ("get", "/api/keys"),
        ("get", "/api/ollama"),
        ("post", "/api/ollama/pull"),
        ("post", "/api/ollama/delete"),
        ("get", "/api/evaluation/cases"),
        ("post", "/api/evaluation/run"),
        ("delete", "/api/metrics"),
    ],
)
def test_removed_endpoints_do_not_exist(client, method, path):
    """Key entry, local models, evaluation and metrics deletion are all gone."""
    response = getattr(client, method)(path, headers=AUTH)

    assert response.status_code in (404, 405)


# --- behaviour ---------------------------------------------------------------


def test_ask_returns_the_answer_payload(client):
    response = client.post("/api/ask", json={"question": "Yakıt limiti?"}, headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["citations"] == ["arac.docx — 3. ARAC TAHSIS POLITIKASI"]
    assert body["modelId"] == "gpt-4.1-mini"
    # Unverified Azure pricing stays null rather than being reported as free.
    assert body["costUsd"] is None


def test_empty_question_is_rejected(client):
    response = client.post("/api/ask", json={"question": "   "}, headers=AUTH)

    assert response.status_code == 400


def test_models_lists_every_deployed_model_with_the_default_active(client):
    body = client.get("/api/models", headers=AUTH).json()

    assert [m["id"] for m in body["models"]] == [
        "gpt-4.1-mini",
        "gpt-5-mini",
        "Phi-4-mini-instruct",
    ]
    assert body["activeId"] == "gpt-4.1-mini"


def test_sessions_are_isolated_by_header(client):
    client.post(
        "/api/ask",
        json={"question": "birinci"},
        headers={"X-Internal-Token": "secret-token", "X-Session-Id": "a"},
    )

    from azure.rag import api

    assert "a" in api._SESSIONS
    assert "b" not in api._SESSIONS


def test_rate_limit_returns_429(client, monkeypatch):
    from azure.rag import api

    monkeypatch.setattr(api, "_RATE_LIMIT_REQUESTS", 2)
    api._REQUEST_LOG.clear()

    for _ in range(2):
        client.post("/api/ask", json={"question": "soru"}, headers=AUTH)
    response = client.post("/api/ask", json={"question": "soru"}, headers=AUTH)

    assert response.status_code == 429


def test_rate_limit_runs_before_validation(client, monkeypatch):
    """429 must win over 400: a blank question should not buy extra attempts."""
    from azure.rag import api

    monkeypatch.setattr(api, "_RATE_LIMIT_REQUESTS", 1)
    api._REQUEST_LOG.clear()

    client.post("/api/ask", json={"question": "  "}, headers=AUTH)
    response = client.post("/api/ask", json={"question": "  "}, headers=AUTH)

    assert response.status_code == 429


# --- streaming ---------------------------------------------------------------


def test_ask_stream_emits_sse_frames(client):
    response = client.post(
        "/api/ask/stream", json={"question": "Yakıt limiti nedir?"}, headers=AUTH
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert '"type": "start"' in body
    assert '"type": "meta"' in body


def test_ask_stream_meta_carries_the_answer_payload(client):
    response = client.post("/api/ask/stream", json={"question": "soru"}, headers=AUTH)

    meta = [
        json.loads(line[len("data: ") :])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ][-1]

    assert meta["type"] == "meta"
    assert meta["citations"] == ["arac.docx — 3. ARAC TAHSIS POLITIKASI"]
    assert meta["grounded"] is True
    assert meta["modelId"] == "gpt-4.1-mini"


def test_ask_stream_replaces_text_that_never_streamed(client):
    """The stub never emits deltas, so the whole answer arrives as a replace."""
    response = client.post("/api/ask/stream", json={"question": "soru"}, headers=AUTH)

    events = [
        json.loads(line[len("data: ") :])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    replace = [event for event in events if event["type"] == "replace"]

    assert replace and replace[0]["content"] == "Aylık yakıt limiti 1.500 TL/ay'dır [1]."


def test_ask_stream_rejects_an_empty_question(client):
    response = client.post("/api/ask/stream", json={"question": "   "}, headers=AUTH)

    assert response.status_code == 400


def test_ask_stream_requires_the_internal_token(client):
    response = client.post("/api/ask/stream", json={"question": "x"})

    assert response.status_code == 401


def test_ask_stream_rebuilds_memory_from_client_history(client):
    from azure.rag import api

    memory = api._memory_from_client(
        "önceki özet",
        [
            {"role": "user", "content": "İzin nasıl alınır?"},
            {"role": "assistant", "content": "Formu doldurun."},
            {"role": "user", "content": "Peki müdür seviyesinde?"},
        ],
    )

    # Only completed pairs become turns; the dangling question is not a turn.
    assert len(memory) == 1
    assert memory.last_turn().question == "İzin nasıl alınır?"


# --- uploads -----------------------------------------------------------------


class _FakeEmbedder:
    """Deterministic stand-in: no network, no Azure credentials in tests."""

    def encode(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


@pytest.fixture
def upload_client(client, monkeypatch):
    from azure.rag import api

    api._UPLOADS.clear("s1:c1")
    monkeypatch.setattr(api, "_EMBEDDER", _FakeEmbedder())
    return client


def _upload(
    client, name=b"notlar.txt", content=b"Yillik izin 14 gundur.", conversation="c1", session="s1"
):
    return client.post(
        "/api/documents/upload",
        files={"file": (name.decode() if isinstance(name, bytes) else name, content, "text/plain")},
        data={"conversation_id": conversation},
        headers={"X-Internal-Token": "secret-token", "X-Session-Id": session},
    )


def test_upload_accepts_a_text_file_and_lists_it(upload_client):
    response = _upload(upload_client)

    assert response.status_code == 200
    assert response.json()["filename"] == "notlar.txt"
    assert response.json()["chunkCount"] >= 1

    listed = upload_client.get("/api/documents?conversation_id=c1", headers=AUTH)
    assert [d["filename"] for d in listed.json()["documents"]] == ["notlar.txt"]


def test_upload_rejects_an_unsupported_type(upload_client):
    response = upload_client.post(
        "/api/documents/upload",
        files={"file": ("virus.exe", b"\x00", "application/octet-stream")},
        data={"conversation_id": "c1"},
        headers=AUTH,
    )

    assert response.status_code == 400


def test_upload_rejects_an_empty_file(upload_client):
    response = _upload(upload_client, name="bos.txt", content=b"")

    assert response.status_code == 400


def test_upload_rejects_a_file_over_the_size_limit(upload_client):
    from azure.rag.uploads import MAX_FILE_BYTES

    response = _upload(upload_client, name="buyuk.txt", content=b"x" * (MAX_FILE_BYTES + 1))

    assert response.status_code == 413


def test_documents_are_scoped_to_the_session(upload_client):
    _upload(upload_client, name="gizli.txt", content=b"gizli metin", session="sA")

    other = upload_client.get(
        "/api/documents?conversation_id=c1",
        headers={"X-Internal-Token": "secret-token", "X-Session-Id": "sB"},
    )

    assert other.json()["documents"] == []


def test_delete_removes_the_named_document(upload_client):
    _upload(upload_client, name="a.txt", conversation="c9")

    response = upload_client.request(
        "DELETE", "/api/documents?conversation_id=c9&filename=a.txt", headers=AUTH
    )

    assert response.json()["documents"] == []


def test_delete_without_a_filename_clears_the_whole_conversation(upload_client):
    """What the front-end calls when a conversation is deleted."""
    _upload(upload_client, name="a.txt", conversation="c7")
    _upload(upload_client, name="b.txt", conversation="c7")

    response = upload_client.request("DELETE", "/api/documents?conversation_id=c7", headers=AUTH)

    assert response.json()["documents"] == []
    listed = upload_client.get("/api/documents?conversation_id=c7", headers=AUTH)
    assert listed.json()["documents"] == []


def test_documents_endpoint_requires_the_internal_token(client):
    assert client.get("/api/documents?conversation_id=c1").status_code == 401


def test_upload_endpoint_requires_the_internal_token(client):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("a.txt", b"x", "text/plain")},
        data={"conversation_id": "c1"},
    )

    assert response.status_code == 401


def test_streaming_widens_retrieval_when_the_conversation_has_uploads(upload_client, monkeypatch):
    """The agent must be rebuilt around an upload-aware retriever, not the bare one."""
    from azure.rag import api

    seen = {}

    class _RecordingAgent(StubAgent):
        retriever = type(
            "R", (), {"index": None, "embedder": None, "min_cosine": 0.25, "min_bm25": 4.22}
        )()
        llm = object()
        max_tool_turns = 3
        metrics = None

    recording = _RecordingAgent()
    monkeypatch.setattr(api, "_AGENT", recording)

    def _fake_agent_class(retriever, toolbox, llm, max_tool_turns, metrics=None):
        seen["retriever"] = retriever
        return recording

    monkeypatch.setattr("azure.rag.agent.Agent", _fake_agent_class)
    _upload(upload_client, name="a.txt", conversation="cX")

    upload_client.post(
        "/api/ask/stream",
        json={"question": "soru", "conversationId": "cX"},
        headers=AUTH,
    )

    assert isinstance(seen.get("retriever"), api.UploadAwareRetriever)


def test_streaming_uses_the_bare_agent_without_uploads(upload_client, monkeypatch):
    called = {"wrapped": False}
    monkeypatch.setattr(
        "azure.rag.agent.Agent",
        lambda *a, **k: called.__setitem__("wrapped", True),
    )

    upload_client.post(
        "/api/ask/stream",
        json={"question": "soru", "conversationId": "bos-sohbet"},
        headers=AUTH,
    )

    assert called["wrapped"] is False


# --- summarization -----------------------------------------------------------


def test_summarize_returns_a_summary(client, monkeypatch):
    from azure.rag import api

    class _StubLLM:
        def chat(self, messages, tools=None):
            return type("R", (), {"text": "birleşik özet"})()

    monkeypatch.setattr(api, "_summary_llm", lambda: _StubLLM())

    response = client.post(
        "/api/summarize",
        json={"previousSummary": "", "messages": [{"role": "user", "content": "a"}]},
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "birleşik özet"


def test_summarize_rejects_an_empty_message_list(client):
    response = client.post(
        "/api/summarize", json={"previousSummary": "", "messages": []}, headers=AUTH
    )

    assert response.status_code == 400


def test_summarize_requires_the_internal_token(client):
    response = client.post("/api/summarize", json={"previousSummary": "", "messages": []})

    assert response.status_code == 401


# --- model seçimi ------------------------------------------------------------


def test_a_selected_model_is_carried_into_the_answer(client, monkeypatch):
    """Seçim isteğe kadar taşınıyor mu — ajan hangi modelle kurulduğunu bildiriyor."""
    from azure.rag import api

    built: list[str | None] = []

    def fake_build(model_id=None):
        built.append(model_id)
        return StubAgent()

    monkeypatch.setattr(api, "_agent_for", fake_build)

    client.post(
        "/api/ask", json={"question": "yakıt limiti", "modelId": "gpt-5-mini"}, headers=AUTH
    )

    assert built == ["gpt-5-mini"]


def test_an_unknown_model_is_rejected_with_400(client):
    response = client.post(
        "/api/ask",
        json={"question": "yakıt limiti", "modelId": "../gizli-model"},
        headers=AUTH,
    )

    assert response.status_code == 400


def test_an_undeployed_model_is_rejected_with_400(client):
    """Kotası olmayan model katalogda var ama seçilemez."""
    response = client.post(
        "/api/ask",
        json={"question": "yakıt limiti", "modelId": "cohere-command-a"},
        headers=AUTH,
    )

    assert response.status_code == 400


def test_omitting_the_model_uses_the_calibrated_default(client):
    body = client.post("/api/ask", json={"question": "yakıt limiti"}, headers=AUTH).json()

    assert body["modelId"] == "gpt-4.1-mini"


def test_the_models_endpoint_reports_why_a_model_cannot_be_used(client):
    body = client.get("/api/models", headers=AUTH).json()

    assert "unavailable" in body
    reasons = {m["id"]: m["reason"] for m in body["unavailable"]}
    assert "cohere-command-a" in reasons
    assert reasons["cohere-command-a"]


def test_streaming_also_honours_the_model_selection(client, monkeypatch):
    from azure.rag import api

    built: list[str | None] = []

    def fake_build(model_id=None):
        built.append(model_id)
        return StubAgent()

    monkeypatch.setattr(api, "_agent_for", fake_build)

    with client.stream(
        "POST",
        "/api/ask/stream",
        json={"question": "yakıt limiti", "modelId": "Phi-4-mini-instruct"},
        headers=AUTH,
    ) as response:
        for _ in response.iter_lines():
            pass

    assert built == ["Phi-4-mini-instruct"]


def test_agent_for_reuses_the_real_agents_wiring(monkeypatch):
    """`_agent_for` gerçek `Agent` alanlarını kullanmalı.

    Diğer testler ajanı stub'ladığı için yanlış bir öznitelik adı (`tools` vs
    `toolbox`) fark edilmeden geçebiliyordu; bu test gerçek sınıfın alanlarına
    bakarak onu yakalar.
    """
    from azure.rag import api
    from azure.rag.agent import Agent

    class _Llm:
        model = "gpt-4.1-mini"

    base = Agent.__new__(Agent)
    base.retriever = object()
    base.toolbox = object()
    base.llm = _Llm()
    base.max_tool_turns = 3
    base.metrics = None

    built = {}

    def fake_agent_cls(retriever, toolbox, llm, max_tool_turns, metrics=None):
        built.update(retriever=retriever, toolbox=toolbox, llm=llm)
        return "yeni-ajan"

    monkeypatch.setattr(api, "_AGENT", base)
    monkeypatch.setattr("azure.rag.agent.Agent", fake_agent_cls)
    monkeypatch.setattr(api, "AzureOpenAIClient", lambda model_id: f"llm:{model_id}")

    result = api._agent_for("gpt-5-mini")

    assert result == "yeni-ajan"
    assert built["retriever"] is base.retriever
    assert built["toolbox"] is base.toolbox
    assert built["llm"] == "llm:gpt-5-mini"


def test_the_models_endpoint_reports_measured_quality_warnings(client):
    """Ölçümde atıflı cevap üretemeyen modeller menüde uyarıyla görünür."""
    body = client.get("/api/models", headers=AUTH).json()

    warnings = body["warnings"]
    assert "gpt-5-mini" in warnings
    assert "Phi-4-mini-instruct" in warnings
    assert "gpt-4.1-mini" not in warnings
