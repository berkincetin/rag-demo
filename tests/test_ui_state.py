import pytest

from src.rag.ui_state import (
    active_model,
    available_models,
    provider_status,
    set_active_model,
    set_key,
)


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


def test_a_local_model_needs_no_key():
    session: dict = {}

    set_active_model(session, "qwen2.5:7b", local_models=["qwen2.5:7b"])

    assert active_model(session, local_models=["qwen2.5:7b"]).id == "qwen2.5:7b"
