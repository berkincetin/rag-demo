"""Seçilebilir modellerin kataloğu.

Katalog tek doğruluk kaynağı: arayüz menüsünü de doldurur, sunucu tarafındaki
doğrulamayı da yapar. İstemciden gelen ad **doğrudan dağıtım adı olarak
kullanılmaz** — katalogdan geçer, yoksa 400 döner.

Parametre farkları burada bayrak olarak durur, istemcide `if model_id ==`
zinciri olarak değil. Ölçülmüş farklar (2026-08-17, canlı uçtan sondalandı):
  - gpt-5-mini `max_tokens` kabul etmiyor → `max_completion_tokens`
  - gpt-5-mini `temperature=0` kabul etmiyor → yalnızca varsayılan
"""

import pytest

from azure.rag.catalog import (
    DEFAULT_CHAT_MODEL,
    ChatModel,
    available_chat_models,
    resolve_chat_model,
)


def test_the_default_model_is_the_one_part_1_was_calibrated_on():
    assert DEFAULT_CHAT_MODEL == "gpt-4.1-mini"


def test_the_default_model_is_deployed():
    assert resolve_chat_model(DEFAULT_CHAT_MODEL).deployed is True


# --- çözümleme ve doğrulama --------------------------------------------------


def test_a_known_model_resolves_to_its_deployment():
    model = resolve_chat_model("gpt-5-mini")

    assert isinstance(model, ChatModel)
    assert model.deployment == "gpt-5-mini"


def test_an_unknown_model_is_rejected():
    """İstemciden gelen serbest metin dağıtım adı olarak kullanılamaz."""
    with pytest.raises(KeyError):
        resolve_chat_model("../../etc/passwd")


def test_an_empty_selection_falls_back_to_the_default():
    assert resolve_chat_model(None).id == DEFAULT_CHAT_MODEL
    assert resolve_chat_model("").id == DEFAULT_CHAT_MODEL


# --- ölçülmüş parametre farkları ---------------------------------------------


def test_gpt5_uses_max_completion_tokens_not_max_tokens():
    """Canlıda ölçüldü: `max_tokens` 400 döndürüyor."""
    model = resolve_chat_model("gpt-5-mini")

    assert model.max_tokens_param == "max_completion_tokens"


def test_gpt5_does_not_accept_a_custom_temperature():
    """Canlıda ölçüldü: `temperature=0` 400 döndürüyor, yalnız varsayılan geçerli."""
    model = resolve_chat_model("gpt-5-mini")

    assert model.supports_temperature is False


def test_the_default_model_still_pins_temperature_to_zero():
    """Bölüm 1'de ölçüldü: yüksek sıcaklıkta atıf işareti düşüyor."""
    model = resolve_chat_model(DEFAULT_CHAT_MODEL)

    assert model.supports_temperature is True
    assert model.max_tokens_param == "max_tokens"


def test_a_reasoning_model_gets_a_larger_token_budget():
    """gpt-5-mini tek cevapta 128 reasoning token harcadı; 1024 sınırı cevabı boş bırakırdı."""
    assert resolve_chat_model("gpt-5-mini").max_tokens > 1024


# --- menü --------------------------------------------------------------------


def test_every_catalog_entry_is_offered_to_the_menu():
    models = available_chat_models()

    assert {model.id for model in models} >= {"gpt-4.1-mini", "gpt-5-mini", "Phi-4-mini-instruct"}


def test_undeployed_models_are_listed_but_marked_with_a_reason():
    """Sessizce başarısız olan bir seçenek bırakılmaz — sebebi görünür."""
    models = {model.id: model for model in available_chat_models()}

    cohere = models["cohere-command-a"]
    assert cohere.deployed is False
    assert cohere.unavailable_reason


def test_deployed_models_carry_no_unavailable_reason():
    for model in available_chat_models():
        if model.deployed:
            assert model.unavailable_reason is None


# --- ölçülmüş cevap kalitesi -------------------------------------------------


def test_the_default_model_is_the_only_one_measured_to_answer_with_citations():
    """2026-08-17'de gerçek korpusta ölçüldü, tahmin değil.

    Aynı soru ("Yıllık izin talebimi nasıl yaparım?") üç modele soruldu:
      gpt-4.1-mini        2 tur, 1 arama, 2 atıf  -> doğru cevap
      gpt-5-mini          6 turda bile aynı aramayı tekrarladı, hiç cevap yazmadı
      Phi-4-mini-instruct doğru bağlamı aldı ama [n] işareti koymadı
    """
    assert resolve_chat_model("gpt-4.1-mini").answers_with_citations is True


def test_models_that_failed_the_citation_gate_are_flagged_with_a_warning():
    """Kalitesi ölçülüp yetersiz bulunan seçenek sessiz bırakılmaz."""
    for model_id in ("gpt-5-mini", "Phi-4-mini-instruct"):
        model = resolve_chat_model(model_id)
        assert model.answers_with_citations is False
        assert model.quality_warning, f"{model_id} için uyarı metni yok"
