"""SSE event generation for one agent run.

The streamed text is a *candidate*: the citation gate can substitute a repaired
answer, a "no information" template, or a refusal that never called the LLM.
These tests pin the `replace` contract that lets the browser correct itself.
"""

import json

from azure.rag.streaming import answer_events, format_sse


def _drain(run, on_meta):
    return list(answer_events(run, on_meta=on_meta))


def _citations(result):
    return {"citations": result.get("citations", [])}


def test_format_sse_frames_one_json_object_per_event():
    frame = format_sse({"type": "token", "content": "a"})

    assert frame.startswith("data: ")
    assert frame.endswith("\n\n")
    assert json.loads(frame[len("data: ") :]) == {"type": "token", "content": "a"}


def test_format_sse_keeps_turkish_characters_unescaped():
    frame = format_sse({"type": "token", "content": "Yıllık izin"})

    assert "Yıllık izin" in frame


def test_streamed_text_is_emitted_as_tokens_then_meta():
    def run(emit):
        emit("Yıllık ")
        emit("izin")
        return {"text": "Yıllık izin", "citations": ["a.pdf"]}

    events = _drain(run, _citations)

    assert [event["type"] for event in events] == ["start", "token", "token", "meta"]
    assert "".join(e["content"] for e in events if e["type"] == "token") == "Yıllık izin"
    assert events[-1]["citations"] == ["a.pdf"]


def test_replace_is_emitted_when_the_final_text_differs_from_what_streamed():
    def run(emit):
        emit("uydurma cevap")
        return {"text": "Bu konuda bilgi bulamadım.", "citations": []}

    events = _drain(run, _citations)

    types = [event["type"] for event in events]
    assert "replace" in types
    assert events[types.index("replace")]["content"] == "Bu konuda bilgi bulamadım."


def test_no_replace_when_the_final_text_matches_the_stream():
    def run(emit):
        emit("aynı")
        return {"text": "aynı", "citations": ["x"]}

    events = _drain(run, _citations)

    assert "replace" not in [event["type"] for event in events]


def test_a_refusal_that_never_streamed_still_produces_the_text():
    """score_gate refuses before any LLM call, so no token is ever emitted."""

    def run(emit):
        return {"text": "Bu soru bilgi tabanının dışında.", "citations": []}

    events = _drain(run, _citations)

    replace = [event for event in events if event["type"] == "replace"]
    assert replace and replace[0]["content"] == "Bu soru bilgi tabanının dışında."


def test_meta_is_always_last():
    def run(emit):
        emit("kısmi")
        return {"text": "düzeltilmiş", "citations": []}

    events = _drain(run, _citations)

    assert events[-1]["type"] == "meta"


def test_an_exception_becomes_an_error_event():
    def run(emit):
        raise RuntimeError("patladı")

    events = _drain(run, _citations)

    assert events[-1]["type"] == "error"
    assert "patladı" in events[-1]["detail"]


def test_no_meta_is_emitted_after_an_error():
    def run(emit):
        emit("yarım")
        raise RuntimeError("koptu")

    events = _drain(run, _citations)

    assert "meta" not in [event["type"] for event in events]


def test_events_are_json_serialisable():
    def run(emit):
        emit("a")
        return {"text": "a", "citations": []}

    for event in _drain(run, _citations):
        json.loads(format_sse(event)[len("data: ") :])
