"""Rolling conversation summary.

The threshold and bookkeeping live on the client, which owns conversation
state; this module only produces the merged summary text.
"""

import pytest

from azure.rag.summarize import build_transcript, summarize_messages


class _StubLLM:
    def __init__(self, text="özet metni"):
        self.text = text
        self.messages = None
        self.tools = "unset"

    def chat(self, messages, tools=None):
        self.messages = messages
        self.tools = tools
        return type("R", (), {"text": self.text})()


# --- transcript rendering ---------------------------------------------------


def test_build_transcript_labels_each_speaker_in_turkish():
    transcript = build_transcript(
        [
            {"role": "user", "content": "İzin nasıl alınır?"},
            {"role": "assistant", "content": "Formu doldurun."},
        ]
    )

    assert transcript == "Kullanıcı: İzin nasıl alınır?\nAsistan: Formu doldurun."


def test_build_transcript_skips_unknown_roles():
    transcript = build_transcript(
        [{"role": "system", "content": "gizli"}, {"role": "user", "content": "soru"}]
    )

    assert "gizli" not in transcript


def test_build_transcript_tolerates_a_missing_content_key():
    assert build_transcript([{"role": "user"}]) == "Kullanıcı: "


# --- summarising ------------------------------------------------------------


def test_summarize_returns_the_model_text():
    result = summarize_messages(_StubLLM("kısa özet"), "", [{"role": "user", "content": "a"}])

    assert result == "kısa özet"


def test_summarize_sends_no_tools():
    """Summarising must never trigger a document search."""
    llm = _StubLLM()

    summarize_messages(llm, "", [{"role": "user", "content": "a"}])

    assert llm.tools is None


def test_summarize_includes_the_previous_summary():
    llm = _StubLLM()

    summarize_messages(llm, "önceki özet burada", [{"role": "user", "content": "a"}])

    assert "önceki özet burada" in llm.messages[-1]["content"]


def test_summarize_says_so_when_there_is_no_previous_summary():
    llm = _StubLLM()

    summarize_messages(llm, "", [{"role": "user", "content": "a"}])

    assert "(Henüz özet yok)" in llm.messages[-1]["content"]


def test_summarize_includes_the_new_messages():
    llm = _StubLLM()

    summarize_messages(llm, "", [{"role": "user", "content": "yemek kartı"}])

    assert "yemek kartı" in llm.messages[-1]["content"]


def test_summarize_rejects_an_empty_message_list():
    with pytest.raises(ValueError):
        summarize_messages(_StubLLM(), "", [])


def test_summarize_returns_an_empty_string_when_the_model_says_nothing():
    assert summarize_messages(_StubLLM(None), "", [{"role": "user", "content": "a"}]) == ""
