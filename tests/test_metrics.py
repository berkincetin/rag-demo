from src.rag.metrics import MetricsStore, RunRecord


def _run(**overrides) -> RunRecord:
    base = dict(
        model_id="claude-opus-5",
        provider="anthropic",
        question="Yıllık izin talebimi nasıl yaparım?",
        latency_ms=1200,
        input_tokens=800,
        output_tokens=120,
        cost_usd=0.007,
        citation_count=2,
        gate_passed=True,
        tool_calls=1,
        repaired=False,
    )
    base.update(overrides)
    return RunRecord(**base)


def test_a_recorded_run_can_be_read_back(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run())

    rows = store.recent()

    assert len(rows) == 1
    assert rows[0].model_id == "claude-opus-5"


def test_unmeasured_tokens_and_cost_stay_null(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run(input_tokens=None, output_tokens=None, cost_usd=None))

    row = store.recent()[0]

    assert row.input_tokens is None
    assert row.cost_usd is None


def test_summary_groups_by_model_and_averages_latency(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run(latency_ms=1000))
    store.record(_run(latency_ms=2000))
    store.record(_run(model_id="qwen2.5:7b-instruct", provider="ollama", latency_ms=60000))

    summary = {row.model_id: row for row in store.summary_by_model()}

    assert summary["claude-opus-5"].runs == 2
    assert summary["claude-opus-5"].avg_latency_ms == 1500
    assert summary["qwen2.5:7b-instruct"].runs == 1


def test_summary_reports_how_many_runs_had_a_known_price(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run(cost_usd=0.01))
    store.record(_run(cost_usd=None))

    row = next(iter(store.summary_by_model()))

    assert row.total_cost_usd == 0.01
    assert row.priced_runs == 1
    assert row.runs == 2


def test_recent_returns_newest_first(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run(question="ilk"))
    store.record(_run(question="ikinci"))

    assert store.recent()[0].question == "ikinci"


def test_schema_is_created_on_first_use(tmp_path):
    path = tmp_path / "yok" / "m.db"

    MetricsStore(path).record(_run())

    assert path.exists()


def test_the_store_never_persists_a_credential(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run())

    columns = store.columns()

    assert not any("key" in column or "secret" in column for column in columns)


def test_gate_pass_rate_counts_refusals(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run(gate_passed=True))
    store.record(_run(gate_passed=False))

    assert next(iter(store.summary_by_model())).gate_pass_rate == 0.5


def test_clear_removes_every_row(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_run())

    store.clear()

    assert store.recent() == []
