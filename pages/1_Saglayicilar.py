"""Sağlayıcı anahtarları ve aktif model seçimi."""

import streamlit as st

from src.rag.catalog import providers
from src.rag.ollama_admin import OllamaAdmin, OllamaUnavailable
from src.rag.pricing import estimate_cost
from src.rag.ui_state import (
    active_model,
    available_models,
    provider_status,
    set_active_model,
    set_key,
)

st.set_page_config(page_title="Sağlayıcılar", page_icon="⚙️")
st.title("⚙️ Sağlayıcılar ve Model Seçimi")

st.info(
    "🔒 Girdiğiniz API anahtarları **yalnızca bu oturumun belleğinde** tutulur. "
    "Diske yazılmaz, log'a düşmez. Sekmeyi kapattığınızda silinirler."
)

LABELS = {"anthropic": "Anthropic (Claude)", "openai": "OpenAI (GPT)", "gemini": "Google Gemini"}

st.subheader("API anahtarları")
statuses = provider_status(st.session_state)
for provider in providers():
    if provider == "ollama":
        continue
    status = statuses[provider]
    col_input, col_state = st.columns([3, 1])
    with col_input:
        # A form so the field and the button submit together — a bare text_input
        # only sends its value on blur, so clicking Save straight after typing
        # would otherwise store an empty key.
        with st.form(key=f"form_{provider}", clear_on_submit=False):
            entered = st.text_input(
                LABELS[provider], type="password", key=f"key_input_{provider}", placeholder="sk-…"
            )
            if st.form_submit_button("Kaydet"):
                set_key(st.session_state, provider, entered)
                st.rerun()
    with col_state:
        st.write("")
        st.write("✅ " + status.masked if status.configured else "⬜ girilmedi")

st.divider()
st.subheader("Aktif model")

try:
    local_names = [model.name for model in OllamaAdmin().list_local()]
except OllamaUnavailable as error:
    local_names = []
    st.warning(f"Yerel modeller listelenemedi: {error}")

choices = available_models(st.session_state, local_names)
if not choices:
    st.error("Kullanılabilir model yok. Ollama'yı başlatın veya bir API anahtarı girin.")
else:
    current = active_model(st.session_state, local_names)
    ids = [model.id for model in choices]
    labels = {model.id: f"{model.label}  ·  {model.provider}" for model in choices}
    selected = st.selectbox(
        "Soruları hangi model cevaplasın?",
        ids,
        index=ids.index(current.id) if current and current.id in ids else 0,
        format_func=lambda model_id: labels[model_id],
    )
    if st.button("Bu modeli kullan", type="primary"):
        try:
            set_active_model(st.session_state, selected, local_models=local_names)
            st.success(f"Aktif model: {selected}")
        except ValueError as error:
            st.error(str(error))

    if estimate_cost(selected, 1000, 100) is None:
        st.warning(
            f"⚠️ **{selected}** için fiyat girilmedi; maliyet hesaplanmayacak. "
            "Fiyatı `config/model_prices.json` dosyasına ekleyebilirsiniz."
        )
