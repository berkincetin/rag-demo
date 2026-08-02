# Task 3: Token muhasebesi + Gemini istemcisi

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.4.
> **Önceki:** [Task 2](02-kimlik-deposu.md) · **Sonraki:** [Task 4](04-metrik-deposu.md)

**Dosyalar:** `src/rag/llm.py` (değişir) · **Test:** `tests/test_llm.py` (genişler)

**Üretir:** `TokenUsage`, `LLMResponse.usage`, `GeminiClient`,
`get_client(config, credentials=None)`

🚨 **Ölçülemeyen token `None`'dır.** `0` yazmak "ölçtük ve sıfır çıktı" demektir — yalan olur.

- [ ] **Adım 1: Kırmızı test**

```python
# tests/test_llm.py — mevcut dosyaya eklenir
from src.rag.credentials import SessionCredentialStore
from src.rag.llm import TokenUsage, parse_ollama_response


def test_ollama_usage_is_read_from_eval_counts():
    payload = {
        "message": {"content": "Merhaba", "tool_calls": []},
        "prompt_eval_count": 120,
        "eval_count": 45,
    }

    assert parse_ollama_response(payload).usage == TokenUsage(120, 45)


def test_missing_usage_fields_are_none_not_zero():
    payload = {"message": {"content": "Merhaba", "tool_calls": []}}

    usage = parse_ollama_response(payload).usage

    assert usage.input_tokens is None
    assert usage.output_tokens is None


def test_usage_defaults_to_empty_on_a_bare_response():
    assert LLMResponse(text="x").usage == TokenUsage(None, None)


def test_get_client_uses_the_session_key_for_anthropic(monkeypatch):
    pytest.importorskip("anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    store = SessionCredentialStore()
    store.set("anthropic", "sk-session-key")

    client = get_client(Config.load(), credentials=store)

    assert isinstance(client, AnthropicClient)


def test_get_client_routes_to_gemini(monkeypatch):
    pytest.importorskip("google.genai")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    assert isinstance(get_client(Config.load()), GeminiClient)


def test_gemini_is_in_the_routing_table(monkeypatch):
    # SDK olmasa da yönlendirme doğru constructor'a ulaşmalı.
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    try:
        get_client(Config.load())
    except ModuleNotFoundError:
        pass
    except ValueError as error:  # pragma: no cover
        pytest.fail(f"gemini yönlendirilmedi: {error}")
```

- [ ] **Adım 2: Kırmızıyı doğrula** — `ImportError: cannot import name 'TokenUsage'`

- [ ] **Adım 3: `llm.py`'yi genişlet**

```python
@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
```

`LLMResponse`'a `usage: TokenUsage = TokenUsage()` alanı eklenir. **Mevcut alanlar ve
protokol imzası değişmez** — `agent.py`, `cli.py`, `smoke_test.py` bozulmaz.

Her istemci kendi alanından okur (spec §4.4 tablosu). Alan yoksa `None`.

`GeminiClient`: `google-genai` SDK'sı, `google.genai.Client(api_key=...)`.
Tool şemaları Gemini'nin `function_declarations` biçimine dönüştürülür; yanıttaki
`function_call` blokları ortak `ToolCall` yapısına normalize edilir.

`get_client(config, credentials=None)` — anahtarı `resolve_key(provider, credentials)`
ile alır; `credentials=None` ise yalnız ortam değişkenine bakar (mevcut davranış).

⚠️ **`llm.py` kapsam dışıdır** (`pyproject.toml` omit listesi) — ağ sarmalayıcıları test
edilmez. Ama `parse_ollama_response`, `TokenUsage` ve yönlendirme **test edilir**;
gerekirse bunları kapsama dahil etmek için omit kuralı daraltılır.

- [ ] **Adım 4: Yeşili doğrula** — mevcut LLM testleri de geçmeli

- [ ] **Adım 5: `requirements.txt` güncelle** — `anthropic`, `openai`, `google-genai` eklenir (sürüm pinli)

- [ ] **Adım 6: Elle duman testi** — Ollama ile bir çağrı yapıp `usage`'ın dolduğunu gör:

```bash
python -c "from src.rag.llm import get_client; r=get_client().chat([{'role':'user','content':'Merhaba'}]); print(r.usage)"
```
Beklenen: `TokenUsage(input_tokens=<sayı>, output_tokens=<sayı>)` — ikisi de `None` değil.

- [ ] **Adım 7: Kalite kapısı ve commit**

```bash
git commit -m "feat(llm): add token usage accounting and Gemini provider"
```

## Definition of Done
- [ ] 6 yeni test yeşil; mevcut LLM testleri bozulmadı
- [ ] Ollama duman testinde `usage` gerçekten dolu
- [ ] Eksik alan `None` döndürüyor, `0` değil
- [ ] `requirements.txt` 15 çalışma zamanı bağımlılığında
