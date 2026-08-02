"""Streamlit front-end: answer, sources, tool trace, and per-query metrics."""

import streamlit as st

from src.rag.cli import build_agent
from src.rag.config import Config
from src.rag.ollama_admin import OllamaAdmin, OllamaUnavailable
from src.rag.pricing import estimate_cost
from src.rag.ui_state import active_model, format_cost, format_latency

EXAMPLES = [
    "Yıllık izin talebimi nasıl yaparım?",
    "Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?",
    "Aksef 500 mg'ın kontrendikasyonları nelerdir?",
    "Vitatin95 ürününün ürün müdürü kim?",
]


@st.cache_resource(show_spinner=False)
def _agent(model_id: str, credential_fingerprint: str):
    # The fingerprint busts the cache when the user swaps model or enters a key.
    return build_agent(model_id=model_id, session=st.session_state)


def _credential_fingerprint() -> str:
    """Which providers currently have a key — never the keys themselves."""
    from src.rag.ui_state import get_store

    return ",".join(get_store(st.session_state).providers_with_keys())


def _local_names() -> list[str]:
    try:
        return [model.name for model in OllamaAdmin().list_local()]
    except OllamaUnavailable:
        return []


st.set_page_config(page_title="Şirket Bilgi Asistanı", page_icon="📚")
st.title("📚 Şirket Bilgi Asistanı")
st.caption("İK politikaları, araç prosedürü, çalışan SSS, ürün taksonomisi ve KÜB belgeleri")

selected = active_model(st.session_state, _local_names(), preferred=Config.load().llm_model)
if selected is None:
    st.error(
        "Kullanılabilir model yok. **Sağlayıcılar** sayfasından bir anahtar girin "
        "veya Ollama'yı başlatın."
    )
    st.stop()

icon = "🖥️" if selected.local else "🤖"
st.markdown(f"{icon} **Aktif model:** `{selected.id}` · {selected.provider}")

with st.sidebar:
    st.subheader("Örnek sorular")
    for example in EXAMPLES:
        if st.button(example, use_container_width=True):
            st.session_state["question"] = example

question = st.text_input("Sorunuz", key="question")

if question:
    with st.spinner("Belgeler taranıyor..."):
        answer = _agent(selected.id, _credential_fingerprint()).answer(question)

    st.markdown(answer.text)

    cost = estimate_cost(selected.id, answer.usage.input_tokens, answer.usage.output_tokens)
    tokens = (
        f"{answer.usage.input_tokens}→{answer.usage.output_tokens} token"
        if answer.usage.input_tokens is not None
        else "token ölçülmedi"
    )
    st.caption(f"⏱ {format_latency(answer.latency_ms)} · 🔤 {tokens} · 💵 {format_cost(cost)}")

    with st.expander(f"Kaynaklar ({len(answer.citations)})", expanded=bool(answer.citations)):
        if answer.citations:
            for position, label in enumerate(answer.citations, start=1):
                st.markdown(f"**{position}.** {label}")
        else:
            st.info("Bu cevap için kaynak gösterilmedi.")

    with st.expander(f"Araç çağrıları ({len(answer.tool_trace)})"):
        if answer.tool_trace:
            st.table(answer.tool_trace)
        else:
            st.info("Araç çağrısı yapılmadı (konu dışı filtresi devreye girdi).")
