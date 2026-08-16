"""Presentation logic behind the Gradio front-end.

`gradio_app.py` is excluded from coverage like `app.py` was, so everything with
a decision in it lives in `ui_state` and is tested here against plain dicts.
"""

from src.rag.models import Answer, TokenUsage
from src.rag.ui_state import (
    citation_markdown,
    metrics_line,
    tool_trace_rows,
)


def test_citation_markdown_numbers_each_source():
    answer = Answer(text="cevap", citations=["a.docx — Bölüm 1", "b.pdf — s.4"])

    rendered = citation_markdown(answer)

    assert "**1.** a.docx — Bölüm 1" in rendered
    assert "**2.** b.pdf — s.4" in rendered


def test_citation_markdown_says_so_when_there_are_no_sources():
    # A refusal has no citations. Rendering an empty list as blank would look
    # like a rendering bug; the demo has to state that no source was shown.
    rendered = citation_markdown(Answer(text="konu dışı", citations=[]))

    assert "kaynak" in rendered.lower()
    assert "**1.**" not in rendered


def test_tool_trace_rows_expose_the_injected_flag():
    # `injected=True` means the agent retrieved on the model's behalf rather
    # than the model choosing the tool — the demo must not hide that.
    answer = Answer(
        text="x",
        tool_trace=[
            {
                "name": "search_documents",
                "arguments": {"query": "izin"},
                "chars": 90,
                "injected": True,
            }
        ],
    )

    rows = tool_trace_rows(answer)

    assert rows == [["search_documents", "{'query': 'izin'}", 90, "otomatik"]]


def test_tool_trace_rows_marks_a_model_chosen_call():
    answer = Answer(
        text="x",
        tool_trace=[{"name": "lookup_section", "arguments": {}, "chars": 5, "injected": False}],
    )

    assert tool_trace_rows(answer)[0][3] == "model"


def test_metrics_line_reports_tokens_when_measured():
    answer = Answer(text="x", usage=TokenUsage(input_tokens=120, output_tokens=30), latency_ms=2500)

    line = metrics_line(answer, cost_usd=0.0012)

    assert "2,5 sn" in line
    assert "120" in line and "30" in line
    assert "$0,0012" in line


def test_metrics_line_does_not_invent_a_token_count():
    # Ollama does not always return token fields. Showing 0 would be a lie.
    answer = Answer(text="x", usage=TokenUsage(), latency_ms=100)

    line = metrics_line(answer, cost_usd=None)

    assert "ölçülmedi" in line
    assert "fiyat girilmedi" in line
