import pytest

from src.rag.evaluation import EvalResult
from src.rag.metrics import ModelSummary
from src.rag.ui_state import (
    active_model,
    available_models,
    comparison_rows,
    estimate_eval_cost,
    format_cost,
    format_latency,
    format_size,
    provider_status,
    pull_label,
    set_active_model,
    set_key,
    suggested_models,
    summary_rows,
)


def _summary(**overrides) -> ModelSummary:
    base = dict(
        model_id="m",
        provider="p",
        runs=1,
        priced_runs=1,
        avg_latency_ms=1000.0,
        total_cost_usd=0.01,
        avg_citations=1.0,
        gate_pass_rate=1.0,
        total_input_tokens=100,
        total_output_tokens=10,
        peak_cpu_percent=None,
        peak_ram_mb=None,
    )
    base.update(overrides)
    return ModelSummary(**base)


def _result(**overrides) -> EvalResult:
    base = dict(
        model_id="m",
        cases=13,
        citation_rate=1.0,
        source_accuracy=1.0,
        evidence_hit=1.0,
        refusal_accuracy=1.0,
        avg_latency_ms=1000.0,
        total_cost_usd=0.01,
        unpriced_runs=0,
    )
    base.update(overrides)
    return EvalResult(**base)


def test_only_local_models_are_available_without_any_key():
    session: dict = {}

    models = available_models(session, local_models=["qwen2.5:7b"])

    assert [m.id for m in models] == ["qwen2.5:7b"]


def test_adding_a_key_unlocks_that_providers_models():
    session: dict = {}
    set_key(session, "anthropic", "sk-ant-test")

    ids = [m.id for m in available_models(session, local_models=[])]

    assert "claude-opus-5" in ids
    assert "gpt-4o-mini" not in ids  # no OpenAI key was entered


def test_provider_status_masks_the_key():
    session: dict = {}
    set_key(session, "openai", "sk-supersecretvalue")

    status = provider_status(session)["openai"]

    assert status.configured is True
    assert "supersecret" not in status.masked


def test_active_model_defaults_to_a_local_model():
    session: dict = {}

    assert active_model(session, local_models=["qwen2.5:7b"]).id == "qwen2.5:7b"


def test_selecting_a_model_without_its_key_is_rejected():
    session: dict = {}

    with pytest.raises(ValueError, match="anahtar"):
        set_active_model(session, "claude-opus-5")


def test_selecting_a_model_after_adding_its_key_succeeds():
    session: dict = {}
    set_key(session, "anthropic", "sk-ant-test")

    set_active_model(session, "claude-opus-5")

    assert active_model(session, local_models=[]).id == "claude-opus-5"


def test_removing_a_key_falls_back_to_a_local_model():
    session: dict = {}
    set_key(session, "anthropic", "sk-ant-test")
    set_active_model(session, "claude-opus-5")

    set_key(session, "anthropic", "")  # key cleared

    assert active_model(session, local_models=["qwen2.5:7b"]).id == "qwen2.5:7b"


def test_the_default_prefers_the_configured_chat_model():
    # `ollama list` also returns embedding models (bge-m3) that cannot chat.
    # Falling back to the first name alphabetically would pick one of those.
    session: dict = {}

    chosen = active_model(
        session,
        local_models=["bge-m3:latest", "qwen2.5:7b-instruct-q4_K_M"],
        preferred="qwen2.5:7b-instruct-q4_K_M",
    )

    assert chosen.id == "qwen2.5:7b-instruct-q4_K_M"


def test_the_default_falls_back_when_the_configured_model_is_absent():
    session: dict = {}

    chosen = active_model(session, local_models=["bge-m3:latest"], preferred="not-installed")

    assert chosen.id == "bge-m3:latest"


def test_a_local_model_needs_no_key():
    session: dict = {}

    set_active_model(session, "qwen2.5:7b", local_models=["qwen2.5:7b"])

    assert active_model(session, local_models=["qwen2.5:7b"]).id == "qwen2.5:7b"


# --- local model manager helpers -------------------------------------------


def test_sizes_are_shown_in_gigabytes():
    assert format_size(4_683_087_332) == "4,7 GB"


def test_small_sizes_use_megabytes():
    # Decimal units, same convention as `ollama list`.
    assert format_size(12_582_912) == "12,6 MB"


def test_unknown_size_is_reported_not_guessed():
    assert format_size(None) == "boyut bilinmiyor"


def test_suggested_models_exclude_already_installed_ones():
    assert "qwen2.5:7b-instruct" not in suggested_models(installed=["qwen2.5:7b-instruct"])


def test_pull_label_shows_percentage_when_total_is_known():
    assert pull_label(status="pulling", fraction=0.25) == "pulling — %25"


def test_pull_label_omits_percentage_when_total_is_unknown():
    # Ollama omits totals on some lines; no invented percentage.
    assert pull_label(status="manifest indiriliyor", fraction=None) == "manifest indiriliyor"


# --- metrics formatting ----------------------------------------------------


def test_cost_is_shown_with_four_decimals():
    assert format_cost(0.00723) == "$0,0072"


def test_unknown_cost_is_labelled_not_zeroed():
    # The single most important formatting rule in this project.
    assert format_cost(None) == "fiyat girilmedi"


def test_zero_cost_is_shown_as_a_number_for_local_models():
    assert format_cost(0.0) == "$0,0000"


def test_latency_switches_to_seconds_above_a_thousand_milliseconds():
    assert format_latency(850) == "850 ms"
    assert format_latency(61_400) == "61,4 sn"


def test_summary_rows_flag_a_model_with_no_known_price():
    rows = summary_rows(
        [
            _summary(model_id="gpt-4o-mini", runs=3, priced_runs=0, total_cost_usd=None),
            _summary(model_id="claude-opus-5", runs=2, priced_runs=2, total_cost_usd=0.05),
        ]
    )

    by_model = {row["model"]: row for row in rows}
    assert by_model["gpt-4o-mini"]["cost"] == "fiyat girilmedi"
    assert by_model["claude-opus-5"]["cost"] == "$0,0500"


def test_summary_rows_mark_incomplete_pricing():
    rows = summary_rows([_summary(runs=4, priced_runs=2, total_cost_usd=0.02)])

    assert "2/4" in rows[0]["cost"]


# --- evaluation page helpers -----------------------------------------------


def test_gpu_distinguishes_unmeasured_from_cpu_bound():
    # The single most important distinction on this page: "we could not measure"
    # and "measured, and it is not using the GPU" are different facts.
    from src.rag.ui_state import format_gpu

    assert format_gpu(None) == "ölçülmedi"
    assert "CPU" in format_gpu(0)
    assert "GB VRAM" in format_gpu(4096)


def test_ram_switches_to_gigabytes():
    from src.rag.ui_state import format_ram

    assert format_ram(512) == "512 MB"
    assert format_ram(9216) == "9,0 GB"
    assert format_ram(None) == "—"


def test_summary_rows_show_input_and_output_tokens_separately():
    rows = summary_rows([_summary(total_input_tokens=1500, total_output_tokens=150)])

    assert rows[0]["toplam giriş tk"] == "1.500"
    assert rows[0]["toplam çıkış tk"] == "150"


def test_unmeasured_token_totals_show_a_dash():
    rows = summary_rows([_summary(total_input_tokens=None, total_output_tokens=None)])

    assert rows[0]["toplam giriş tk"] == "—"


def test_the_session_remembers_a_user_name():
    from src.rag.ui_state import get_user_name, set_user_name

    session: dict = {}
    set_user_name(session, "  Berkin  ")

    assert get_user_name(session) == "Berkin"


def test_conversation_memory_is_created_once_per_session():
    from src.rag.ui_state import get_memory

    session: dict = {}

    assert get_memory(session) is get_memory(session)


def test_the_screen_transcript_keeps_what_the_model_memory_drops():
    # A refusal must not enter the model's memory — it would pollute the next
    # retrieval query — but the user should still see it on screen.
    from src.rag.ui_state import add_to_transcript, get_memory, get_transcript

    session: dict = {}
    add_to_transcript(session, "Bugün hava nasıl?", "Bu soru kapsamım dışında.")

    assert [question for question, _ in get_transcript(session)] == ["Bugün hava nasıl?"]
    assert len(get_memory(session)) == 0


def test_clearing_the_chat_empties_the_transcript_and_the_memory():
    from src.rag.ui_state import add_to_transcript, clear_chat, get_memory, get_transcript

    session: dict = {}
    get_memory(session).add("soru", "cevap")
    add_to_transcript(session, "soru", "cevap")

    clear_chat(session)

    assert get_transcript(session) == []
    assert len(get_memory(session)) == 0


def test_clearing_the_chat_keeps_the_user_name():
    # The name is an identity, not part of the conversation.
    from src.rag.ui_state import clear_chat, get_user_name, set_user_name

    session: dict = {}
    set_user_name(session, "Berkin")

    clear_chat(session)

    assert get_user_name(session) == "Berkin"


def test_cost_estimate_scales_with_the_case_count():
    assert estimate_eval_cost("claude-opus-5", cases=13) > 0


def test_estimate_is_none_for_an_unpriced_model():
    assert estimate_eval_cost("gpt-4o-mini", cases=13) is None


def test_local_models_are_estimated_as_free():
    assert estimate_eval_cost("qwen2.5:7b-instruct", cases=13) == 0.0


def test_comparison_orders_by_citation_rate_then_latency():
    rows = comparison_rows(
        [
            _result(model_id="a", citation_rate=0.8, avg_latency_ms=1000),
            _result(model_id="b", citation_rate=1.0, avg_latency_ms=5000),
            _result(model_id="c", citation_rate=1.0, avg_latency_ms=2000),
        ]
    )

    assert [row["model"] for row in rows] == ["c", "b", "a"]


def test_unmeasured_rates_are_shown_as_dash_not_zero():
    rows = comparison_rows([_result(model_id="a", citation_rate=None)])

    assert rows[0]["atıf oranı"] == "—"
