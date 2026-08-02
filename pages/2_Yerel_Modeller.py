"""Yerel (Ollama) modelleri listele, indir, sil."""

import streamlit as st

from src.rag.ollama_admin import OllamaAdmin, OllamaUnavailable
from src.rag.ui_state import format_size, pull_label, suggested_models

st.set_page_config(page_title="Yerel Modeller", page_icon="📦")
st.title("📦 Yerel Modeller")

admin = OllamaAdmin()

if not admin.is_available():
    st.error(
        "Ollama'ya ulaşılamıyor. Çalıştığından ve `OLLAMA_BASE_URL` ayarının doğru "
        f"olduğundan emin olun (şu an: `{admin.base_url}`)."
    )
    st.stop()

installed = admin.list_local()

st.subheader("Yüklü modeller")
if not installed:
    st.info("Henüz model yok. Aşağıdan indirebilirsiniz.")
for model in installed:
    col_name, col_size, col_action = st.columns([3, 1, 1])
    col_name.write(f"**{model.name}**")
    col_size.write(format_size(model.size_bytes))
    if col_action.button("Sil", key=f"del_{model.name}"):
        st.session_state["_confirm_delete"] = model.name
        st.rerun()

pending = st.session_state.get("_confirm_delete")
if pending:
    st.warning(f"**{pending}** silinecek. Emin misiniz?")
    col_yes, col_no = st.columns(2)
    if col_yes.button("Evet, sil", type="primary"):
        admin.delete(pending)
        st.session_state.pop("_confirm_delete")
        st.rerun()
    if col_no.button("Vazgeç"):
        st.session_state.pop("_confirm_delete")
        st.rerun()

st.divider()
st.subheader("Model indir")
st.caption("⚠️ Modeller birkaç GB olabilir; indirme dakikalar sürer. Bu sayfayı kapatmayın.")

suggestions = suggested_models([model.name for model in installed])
chosen = st.selectbox("Öneriler", ["(elle yaz)", *suggestions])
manual = st.text_input("Model adı", value="" if chosen == "(elle yaz)" else chosen)

if st.button("İndir", type="primary", disabled=not manual):
    progress = st.progress(0.0)
    status_line = st.empty()

    def _on_progress(update):
        status_line.write(pull_label(update.status, update.fraction))
        if update.fraction is not None:
            progress.progress(update.fraction)

    try:
        admin.pull(manual, on_progress=_on_progress)
    except OllamaUnavailable as error:
        st.error(str(error))
    else:
        progress.progress(1.0)
        st.success(f"{manual} indirildi. Sağlayıcılar sayfasından seçebilirsiniz.")
