"""Streamlit front-end: answer, sources, and tool trace."""

import streamlit as st

from src.rag.cli import build_agent

EXAMPLES = [
    "Yıllık izin talebimi nasıl yaparım?",
    "Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?",
    "Aksef 500 mg'ın kontrendikasyonları nelerdir?",
    "Vitatin95 ürününün ürün müdürü kim?",
]


@st.cache_resource
def _agent():
    return build_agent()


st.set_page_config(page_title="Şirket Bilgi Asistanı", page_icon="📚")
st.title("📚 Şirket Bilgi Asistanı")
st.caption("İK politikaları, araç prosedürü, çalışan SSS, ürün taksonomisi ve KÜB belgeleri")

with st.sidebar:
    st.subheader("Örnek sorular")
    for example in EXAMPLES:
        if st.button(example, use_container_width=True):
            st.session_state["question"] = example

question = st.text_input("Sorunuz", key="question")

if question:
    with st.spinner("Belgeler taranıyor..."):
        answer = _agent().answer(question)

    st.markdown(answer.text)

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
