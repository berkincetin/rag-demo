import pytest

from src.rag.ollama_admin import LocalModel, OllamaAdmin, OllamaUnavailable


class _FakeHttp:
    def __init__(self, get_payload=None, stream_lines=None, fail=False):
        self.get_payload = get_payload or {}
        self.stream_lines = stream_lines or []
        self.fail = fail
        self.deleted = None

    def get_json(self, url, timeout):
        if self.fail:
            raise ConnectionError("bağlanılamadı")
        return self.get_payload

    def post_stream(self, url, json, timeout):
        if self.fail:
            raise ConnectionError("bağlanılamadı")
        yield from self.stream_lines

    def delete(self, url, json, timeout):
        self.deleted = json["model"]


def test_local_models_are_listed_with_size():
    http = _FakeHttp(
        get_payload={"models": [{"name": "qwen2.5:7b-instruct-q4_K_M", "size": 4683087332}]}
    )

    models = OllamaAdmin(http=http).list_local()

    assert models == [LocalModel(name="qwen2.5:7b-instruct-q4_K_M", size_bytes=4683087332)]


def test_unreachable_ollama_raises_a_clear_error():
    # The UI must be able to show a message instead of crashing.
    with pytest.raises(OllamaUnavailable):
        OllamaAdmin(http=_FakeHttp(fail=True)).list_local()


def test_availability_check_does_not_raise():
    assert OllamaAdmin(http=_FakeHttp(fail=True)).is_available() is False


def test_pull_reports_progress_as_a_fraction():
    http = _FakeHttp(
        stream_lines=[
            {"status": "pulling", "completed": 50, "total": 200},
            {"status": "pulling", "completed": 200, "total": 200},
            {"status": "success"},
        ]
    )
    seen = []

    OllamaAdmin(http=http).pull("qwen2.5:7b-instruct", on_progress=seen.append)

    assert seen[0].fraction == pytest.approx(0.25)
    assert seen[1].fraction == pytest.approx(1.0)


def test_pull_tolerates_lines_without_totals():
    # Ollama omits `total` on some lines; no division, no invented percentage.
    http = _FakeHttp(stream_lines=[{"status": "manifest indiriliyor"}, {"status": "success"}])
    seen = []

    OllamaAdmin(http=http).pull("m", on_progress=seen.append)

    assert seen[0].fraction is None


def test_delete_passes_the_model_name():
    http = _FakeHttp()

    OllamaAdmin(http=http).delete("eski-model")

    assert http.deleted == "eski-model"
