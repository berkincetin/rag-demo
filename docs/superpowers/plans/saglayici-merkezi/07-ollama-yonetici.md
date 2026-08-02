# Task 7: Ollama model yöneticisi

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.6.
> **Önceki:** [Task 6](06-agent-metrik.md) · **Sonraki:** [Task 8](08-degerlendirme.md)

**Dosyalar:** `src/rag/ollama_admin.py` · **Test:** `tests/test_ollama_admin.py`

**Üretir:** `LocalModel` dataclass, `list_local()`, `pull(model, on_progress)`,
`delete(model)`, `is_available()`

Ağ çağrıları `requests` ile; **testlerde gerçek ağ yok** — HTTP katmanı enjekte edilir.

- [ ] **Adım 1: Kırmızı test**

```python
# tests/test_ollama_admin.py
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
        for line in self.stream_lines:
            yield line

    def delete(self, url, json, timeout):
        self.deleted = json["model"]


def test_local_models_are_listed_with_size():
    http = _FakeHttp(
        get_payload={"models": [{"name": "qwen2.5:7b-instruct-q4_K_M", "size": 4683087332}]}
    )

    models = OllamaAdmin(http=http).list_local()

    assert models == [LocalModel(name="qwen2.5:7b-instruct-q4_K_M", size_bytes=4683087332)]


def test_unreachable_ollama_raises_a_clear_error():
    # Arayüz çökmemeli; kullanıcıya anlaşılır mesaj gösterilmeli.
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
    assert seen[-1].fraction == pytest.approx(1.0)


def test_pull_tolerates_lines_without_totals():
    # Ollama bazı satırlarda total göndermez; bölme hatası olmamalı.
    http = _FakeHttp(stream_lines=[{"status": "manifest indiriliyor"}, {"status": "success"}])
    seen = []

    OllamaAdmin(http=http).pull("m", on_progress=seen.append)

    assert seen[0].fraction is None


def test_delete_passes_the_model_name():
    http = _FakeHttp()

    OllamaAdmin(http=http).delete("eski-model")

    assert http.deleted == "eski-model"
```

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: `ollama_admin.py` yaz**

- `OllamaAdmin(base_url=None, http=None)` — `http` verilmezse `requests` tabanlı
  varsayılan kullanılır. Bu seam testleri ağdan bağımsız kılar (Task 3'teki `_post`
  deseninin aynısı)
- `PullProgress(status, completed, total, fraction)` — `total` yoksa `fraction=None`
- `list_local()` → `GET /api/tags`; `pull()` → `POST /api/pull` (akış, `stream=True`);
  `delete()` → `DELETE /api/delete`
- Bağlantı hatası → `OllamaUnavailable` (anlaşılır Türkçe mesajla)
- `pull` için zaman aşımı uzun (model 4,7 GB olabilir) — `LLM_TIMEOUT_SECONDS` değil,
  ayrı bir `OLLAMA_PULL_TIMEOUT` (varsayılan 3600)

- [ ] **Adım 4: Yeşili doğrula** — 6 test geçmeli

- [ ] **Adım 5: Gerçek Ollama ile elle doğrulama**

```bash
python -c "from src.rag.ollama_admin import OllamaAdmin; [print(m) for m in OllamaAdmin().list_local()]"
```
Beklenen: yüklü modeller listelenir (bu makinede en az `qwen2.5:7b-instruct-q4_K_M`).

- [ ] **Adım 6: Kalite kapısı ve commit**

```bash
git commit -m "feat(ollama): add local model list, pull with progress, and delete"
```

## Definition of Done
- [ ] 6 test yeşil, `ollama_admin.py` ≥ %90 kapsanmış
- [ ] Testlerde gerçek ağ çağrısı yok
- [ ] Ollama kapalıyken `OllamaUnavailable` — çökme yok
- [ ] Gerçek Ollama ile liste komutu çalıştırıldı
