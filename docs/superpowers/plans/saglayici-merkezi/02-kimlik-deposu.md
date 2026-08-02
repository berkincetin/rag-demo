# Task 2: Oturum kapsamlı anahtar deposu

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.3.
> **Önceki:** [Task 1](01-katalog-fiyat.md) · **Sonraki:** [Task 3](03-token-ve-gemini.md)

**Dosyalar:** `src/rag/credentials.py` · **Test:** `tests/test_credentials.py`

**Üretir:** `CredentialStore` protokolü, `SessionCredentialStore`, `mask_key()`,
`resolve_key(provider, store) -> str | None`

🚨 **Bu task güvenlik kritik.** Anahtar diske yazılmaz, loglanmaz, `__repr__`'de görünmez.

- [ ] **Adım 1: Kırmızı test**

```python
# tests/test_credentials.py
import pytest

from src.rag.credentials import SessionCredentialStore, mask_key, resolve_key


def test_key_can_be_set_and_read_back():
    store = SessionCredentialStore()
    store.set("anthropic", "sk-ant-1234567890abcd")

    assert store.get("anthropic") == "sk-ant-1234567890abcd"


def test_missing_provider_returns_none():
    assert SessionCredentialStore().get("openai") is None


def test_providers_with_keys_lists_only_configured_ones():
    store = SessionCredentialStore()
    store.set("openai", "sk-test")

    assert store.providers_with_keys() == ["openai"]


def test_repr_never_leaks_the_key():
    # Bir istisna izinde ya da logda store yazdırılırsa anahtar sızmamalı.
    store = SessionCredentialStore()
    store.set("anthropic", "sk-ant-supersecret")

    assert "supersecret" not in repr(store)


def test_mask_shows_only_a_short_tail():
    masked = mask_key("sk-ant-supersecretvalue")

    assert "supersecret" not in masked
    assert masked.endswith("alue")


def test_mask_handles_short_and_empty_keys():
    assert mask_key("") == ""
    assert "abc" not in mask_key("abc") or mask_key("abc") == "…"


def test_environment_variable_is_the_fallback(monkeypatch):
    # CLI ve Docker akışları oturum deposu olmadan da çalışmalı.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")

    assert resolve_key("anthropic", SessionCredentialStore()) == "sk-env"


def test_session_key_wins_over_environment(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    store = SessionCredentialStore()
    store.set("anthropic", "sk-session")

    assert resolve_key("anthropic", store) == "sk-session"


def test_store_module_performs_no_file_io():
    # Kullanıcı kararı: anahtarlar yalnız bellekte. Diske yazan bir yol olmamalı.
    import inspect

    import src.rag.credentials as module

    source = inspect.getsource(module)
    for forbidden in ("open(", "Path(", "json.dump", "write_text", "keyring"):
        assert forbidden not in source
```

- [ ] **Adım 2: Kırmızıyı doğrula** — `ModuleNotFoundError`

- [ ] **Adım 3: `credentials.py` yaz**

- `CredentialStore` = `typing.Protocol` (`set`, `get`, `providers_with_keys`)
- `SessionCredentialStore` — içeride basit `dict`. `__repr__` yalnız sağlayıcı adlarını
  yazar, değerleri **hiç** yazmaz.
- `mask_key(key)` — 8 karakterden kısa ise `"…"`, değilse `"…" + key[-4:]`
- `resolve_key(provider, store)` — önce store, sonra `{PROVIDER}_API_KEY` ortam değişkeni
- Ortam değişkeni adları: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`

> Streamlit'e bağımlılık **yok** — depo saf Python. Arayüz katmanı (Task 9) örneği
> `st.session_state` içinde tutar. Bu, deponun Streamlit olmadan test edilmesini sağlar.

- [ ] **Adım 4: Yeşili doğrula** — 9 test geçmeli

- [ ] **Adım 5: Kalite kapısı ve commit**

```bash
git commit -m "feat(credentials): add session-scoped API key store with masking"
```

## Definition of Done
- [ ] 9 test yeşil, `credentials.py` %100 kapsanmış
- [ ] Kaynak kodda dosya G/Ç'si yok (test ile korunuyor)
- [ ] `repr` anahtarı sızdırmıyor
- [ ] Ortam değişkeni yedeği çalışıyor, oturum anahtarı önceliği var
