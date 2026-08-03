"""Streamlit front-end: answer, sources, tool trace, and per-query metrics."""

import streamlit as st

from src.rag.cli import build_agent
from src.rag.config import Config
from src.rag.ollama_admin import OllamaAdmin, OllamaUnavailable
from src.rag.pricing import estimate_cost
from src.rag.ui_state import (
    active_model,
    add_to_transcript,
    clear_chat,
    format_cost,
    format_gpu,
    format_latency,
    format_percent,
    format_ram,
    get_memory,
    get_transcript,
    get_user_name,
    set_user_name,
)

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
    st.subheader("Kim konuşuyor?")
    name = st.text_input("Adınız (isteğe bağlı)", value=get_user_name(st.session_state))
    if name != get_user_name(st.session_state):
        set_user_name(st.session_state, name)
    st.caption("Adınız modele iletilir; ölçüm veritabanına **yazılmaz**.")

    memory = get_memory(st.session_state)
    st.subheader(f"Sohbet belleği ({len(memory)} tur)")
    st.caption("Model son 5 turu görür. Reddedilen cevaplar belleğe girmez.")
    if st.button("Sohbeti temizle", use_container_width=True):
        clear_chat(st.session_state)
        st.session_state.pop("_last_answer", None)
        st.rerun()

    st.subheader("Örnek sorular")
    for example in EXAMPLES:
        if st.button(example, use_container_width=True):
            st.session_state["_pending_question"] = example

# `st.chat_input` returns the text once, on the run that follows submission, and
# is empty afterwards. A plain text_input keeps its value, so every unrelated
# rerun (a sidebar click) would answer the same question again and append a
# second copy of the turn.
question = st.chat_input("Sorunuz") or st.session_state.pop("_pending_question", None)

if question:
    with st.spinner("Belgeler taranıyor..."):
        answer = _agent(selected.id, _credential_fingerprint()).answer(
            question, memory=memory, user_name=get_user_name(st.session_state)
        )
    add_to_transcript(st.session_state, question, answer.text)
    st.session_state["_last_answer"] = answer

for asked, replied in get_transcript(st.session_state):
    with st.chat_message("user"):
        st.write(asked)
    with st.chat_message("assistant"):
        st.markdown(replied)

answer = st.session_state.get("_last_answer")
if answer is not None:
    cost = estimate_cost(selected.id, answer.usage.input_tokens, answer.usage.output_tokens)
    tokens = (
        f"↑{answer.usage.input_tokens} / ↓{answer.usage.output_tokens} token"
        if answer.usage.input_tokens is not None
        else "token ölçülmedi"
    )
    resources = getattr(_agent(selected.id, _credential_fingerprint()), "_last_resources", None)
    parts = [
        f"⏱ {format_latency(answer.latency_ms)}",
        f"🔤 {tokens}",
        f"💵 {format_cost(cost)}",
    ]
    if resources is not None and resources.peak_cpu_percent is not None:
        parts.append(f"🖥 CPU {format_percent(resources.peak_cpu_percent)}")
        parts.append(f"🧠 RAM {format_ram(resources.peak_ram_mb)}")
        if selected.local:
            parts.append(f"🎮 {format_gpu(resources.gpu_vram_mb)}")
    st.caption(" · ".join(parts))

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
