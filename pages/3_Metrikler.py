"""Token, süre ve maliyet geçmişi."""

import pandas as pd
import streamlit as st

from src.rag.config import Config
from src.rag.metrics import MetricsStore
from src.rag.ui_state import (
    format_cost,
    format_gpu,
    format_latency,
    format_percent,
    format_ram,
    summary_rows,
)

st.set_page_config(page_title="Metrikler", page_icon="📊")
st.title("📊 Metrikler")

store = MetricsStore(Config.load().storage_dir / "metrics.db")
summaries = list(store.summary_by_model())
runs = store.recent()

if not runs:
    st.info("Henüz ölçüm yok. Sohbet sayfasından bir soru sorun.")
    st.stop()

st.caption(
    "ℹ️ Sorular ölçüm veritabanına kaydedilir. Gerçek bir dağıtımda bu kişisel veri " "içerebilir."
)

st.subheader("Model karşılaştırması")
st.dataframe(pd.DataFrame(summary_rows(summaries)), use_container_width=True, hide_index=True)

st.subheader("Ortalama süre (ms)")
st.bar_chart(
    pd.DataFrame(
        {"model": [s.model_id for s in summaries], "ms": [s.avg_latency_ms for s in summaries]}
    ).set_index("model")
)

priced = [s for s in summaries if s.total_cost_usd is not None]
if priced:
    st.subheader("Toplam maliyet (USD)")
    st.bar_chart(
        pd.DataFrame(
            {"model": [s.model_id for s in priced], "usd": [s.total_cost_usd for s in priced]}
        ).set_index("model")
    )
    skipped = len(summaries) - len(priced)
    if skipped:
        st.caption(f"{skipped} model fiyatı girilmediği için grafikte yok.")
else:
    st.info("Hiçbir modelin fiyatı girilmemiş; maliyet grafiği gösterilemiyor.")

st.subheader("Son koşular")
st.dataframe(
    pd.DataFrame(
        [
            {
                "zaman": run.ts,
                "model": run.model_id,
                "soru": run.question[:60],
                "tur": run.turn_index,
                "süre": format_latency(run.latency_ms),
                "giriş tk": "—" if run.input_tokens is None else run.input_tokens,
                "çıkış tk": "—" if run.output_tokens is None else run.output_tokens,
                "tepe CPU": format_percent(run.peak_cpu_percent),
                "tepe RAM": format_ram(run.peak_ram_mb),
                "GPU": format_gpu(run.gpu_vram_mb),
                "maliyet": format_cost(run.cost_usd),
                "atıf": run.citation_count,
                "kapı": "✓" if run.gate_passed else "✗",
                "onarım": "✓" if run.repaired else "",
            }
            for run in runs
        ]
    ),
    use_container_width=True,
    hide_index=True,
)

st.divider()
if st.button("Geçmişi temizle"):
    st.session_state["_confirm_clear"] = True
if st.session_state.get("_confirm_clear"):
    st.warning("Tüm ölçüm geçmişi silinecek.")
    if st.button("Evet, sil", type="primary"):
        store.clear()
        st.session_state.pop("_confirm_clear")
        st.rerun()
