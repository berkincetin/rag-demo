import inspect

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
    # If the store lands in a traceback or a log line, the key must not ride along.
    store = SessionCredentialStore()
    store.set("anthropic", "sk-ant-supersecret")

    assert "supersecret" not in repr(store)


def test_mask_shows_only_a_short_tail():
    masked = mask_key("sk-ant-supersecretvalue")

    assert "supersecret" not in masked
    assert masked.endswith("alue")


def test_mask_handles_short_and_empty_keys():
    assert mask_key("") == ""
    assert "abc" not in mask_key("abc")


def test_environment_variable_is_the_fallback(monkeypatch):
    # CLI and Docker paths have no session store; they must still authenticate.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")

    assert resolve_key("anthropic", SessionCredentialStore()) == "sk-env"


def test_session_key_wins_over_environment(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    store = SessionCredentialStore()
    store.set("anthropic", "sk-session")

    assert resolve_key("anthropic", store) == "sk-session"


def test_store_module_performs_no_file_io():
    # The user's decision: keys live in memory only. There must be no path to disk.
    source = inspect.getsource(inspect.getmodule(SessionCredentialStore))

    for forbidden in ("open(", "Path(", "json.dump", "write_text", "keyring"):
        assert forbidden not in source
