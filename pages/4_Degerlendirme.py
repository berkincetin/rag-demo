"""Modelleri sabit soru setiyle karşılaştır."""

import pandas as pd
import streamlit as st

from src.rag.evaluation import evaluate, load_eval_set
from src.rag.ollama_admin import OllamaAdmin, OllamaUnavailable
from src.rag.ui_state import available_models, comparison_rows, estimate_eval_cost, format_cost

st.set_page_config(page_title="Değerlendirme", page_icon="🎯")
st.title("🎯 Model Değerlendirmesi")

cases = load_eval_set()
st.caption(
    f"{len(cases)} soruluk sabit set: atıf oranı, kaynak isabeti, kanıt isabeti ve "
    "konu dışı red isabeti ölçülür. Cevabın üslubu **puanlanmaz**."
)

try:
    local_names = [model.name for model in OllamaAdmin().list_local()]
except OllamaUnavailable:
    local_names = []

choices = available_models(st.session_state, local_names)
if not choices:
    st.error("Kullanılabilir model yok. Sağlayıcılar sayfasından anahtar girin.")
    st.stop()

selected = st.multiselect(
    "Karşılaştırılacak modeller", [m.id for m in choices], default=[choices[0].id]
)

if selected:
    st.subheader("Çalıştırmadan önce")
    total_known = 0.0
    unknown = []
    for model_id in selected:
        estimate = estimate_eval_cost(model_id, len(cases))
        if estimate is None:
            unknown.append(model_id)
        else:
            total_known += estimate
    st.write(f"Tahmini maliyet (**yaklaşık, ±%50**): {format_cost(total_known)}")
    if unknown:
        st.warning(f"Fiyatı bilinmeyen model(ler): {', '.join(unknown)} — maliyet eksik.")
    st.write(
        f"Tahmini süre: {len(selected)} model × {len(cases)} soru. "
        "Yerel modelde soru başına 40–460 sn sürebilir."
    )
    st.caption("⚠️ Bu işlem dakikalar sürer ve bulut modellerinde **ücretlidir**.")

    consented = st.checkbox("Maliyeti ve süreyi anladım, çalıştır")

    if st.button("Değerlendirmeyi başlat", type="primary", disabled=not consented):
        from src.rag.cli import build_agent
        from src.rag.config import Config

        def _progress_reporter(bar):
            # Bound here rather than in the loop so each model gets its own bar.
            def report(done, total, _question):
                bar.progress(done / total)

            return report

        results = []
        for model_id in selected:
            with st.status(f"{model_id} değerlendiriliyor…", expanded=True) as status:
                bar = st.progress(0.0)
                agent = build_agent(Config.load(), model_id=model_id, session=st.session_state)
                results.append(evaluate(agent, cases, on_progress=_progress_reporter(bar)))
                status.update(label=f"{model_id} tamamlandı", state="complete")

        st.subheader("Sonuç")
        rows = comparison_rows(results)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.bar_chart(
            pd.DataFrame(
                {
                    "model": [r.model_id for r in results],
                    "atıf oranı": [(r.citation_rate or 0) for r in results],
                }
            ).set_index("model")
        )
