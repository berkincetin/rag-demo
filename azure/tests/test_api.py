"""API contract and security. The internal token is the tier boundary.

The agent is stubbed so these tests exercise routing and auth without calling
Azure OpenAI. Nothing here asserts on model output text.
"""

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


def test_models_lists_only_the_azure_deployment(client):
    body = client.get("/api/models", headers=AUTH).json()

    assert [m["id"] for m in body["models"]] == ["gpt-4.1-mini"]
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
