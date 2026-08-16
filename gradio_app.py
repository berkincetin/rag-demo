"""Gradio front-end: chat, providers, local models, metrics, evaluation.

Replaces the Streamlit app and its four pages. All decision logic lives in
`src.rag.ui_state`, which knows nothing about any UI framework — this file is
layout and wiring only, and is excluded from coverage for that reason.

Session state: Gradio has no `st.session_state`, so a plain dict per browser
session is held in a `gr.State` and handed to the same `ui_state` helpers the
Streamlit build used. Keys therefore stay in memory and never reach disk
(ADR-012), exactly as before.
"""

import gradio as gr
import pandas as pd

from src.rag.catalog import providers
from src.rag.cli import build_agent
from src.rag.config import Config
from src.rag.evaluation import evaluate, load_eval_set
from src.rag.metrics import MetricsStore
from src.rag.ollama_admin import OllamaAdmin, OllamaUnavailable
from src.rag.pricing import estimate_cost
from src.rag.ui_state import (
    active_model,
    add_to_transcript,
    available_models,
    citation_markdown,
    comparison_rows,
    estimate_eval_cost,
    format_cost,
    format_gpu,
    format_latency,
    format_percent,
    format_ram,
    format_size,
    get_memory,
    get_user_name,
    metrics_line,
    provider_status,
    pull_label,
    set_active_model,
    set_key,
    set_user_name,
    suggested_models,
    summary_rows,
    tool_trace_rows,
)

EXAMPLES = [
    "Yıllık izin talebimi nasıl yaparım?",
    "Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?",
    "Aksef 500 mg'ın kontrendikasyonları nelerdir?",
    "Vitatin95 ürününün ürün müdürü kim?",
]

PROVIDER_LABELS = {
    "anthropic": "Anthropic (Claude)",
    "openai": "OpenAI (GPT)",
    "gemini": "Google Gemini",
}

# One agent per (model, credential fingerprint). Rebuilding on every question
# would reload the 1.1 GB embedding model each time.
_AGENTS: dict[tuple[str, str], object] = {}

# Gradio injects the live tracker for any parameter defaulting to a Progress
# instance. Held as a module-level singleton so the default is not a call in the
# signature (ruff B008); Gradio replaces it per request either way.
_PROGRESS = gr.Progress()


def _local_names() -> list[str]:
    try:
        return [model.name for model in OllamaAdmin().list_local()]
    except OllamaUnavailable:
        return []


def _agent_for(session: dict, model_id: str):
    from src.rag.ui_state import get_store

    fingerprint = ",".join(get_store(session).providers_with_keys())
    cache_key = (model_id, fingerprint)
    if cache_key not in _AGENTS:
        _AGENTS[cache_key] = build_agent(model_id=model_id, session=session)
    return _AGENTS[cache_key]


def _selected_model(session: dict):
    return active_model(session, _local_names(), preferred=Config.load().llm_model)


def _model_banner(session: dict) -> str:
    model = _selected_model(session)
    if model is None:
        return (
            "### ⚠️ Kullanılabilir model yok\n"
            "**Sağlayıcılar** sekmesinden bir API anahtarı girin veya Ollama'yı başlatın."
        )
    icon = "🖥️" if model.local else "🤖"
    return f"### {icon} Aktif model: `{model.id}`\n{model.provider}"


# --- chat -------------------------------------------------------------------


def ask(question: str, history: list, session: dict, user_name: str):
    """Answer one question for `gr.ChatInterface`.

    ChatInterface owns the transcript, so this returns only the reply text plus
    the three `additional_outputs` panels (sources, tool trace, metrics) — it
    must not rebuild `history` itself.
    """
    question = (question or "").strip()
    if not question:
        return "", gr.skip(), gr.skip(), gr.skip()

    set_user_name(session, user_name)

    model = _selected_model(session)
    if model is None:
        return (
            "Kullanılabilir model yok — **Sağlayıcılar** sekmesinden bir API anahtarı "
            "girin veya Ollama'yı başlatın.",
            "_Model seçilmedi._",
            [],
            "",
        )

    agent = _agent_for(session, model.id)
    answer = agent.answer(question, memory=get_memory(session), user_name=get_user_name(session))
    add_to_transcript(session, question, answer.text)

    cost = estimate_cost(model.id, answer.usage.input_tokens, answer.usage.output_tokens)
    line = metrics_line(answer, cost)
    resources = getattr(agent, "_last_resources", None)
    if resources is not None and resources.peak_cpu_percent is not None:
        line += f"  ·  🖥 CPU {format_percent(resources.peak_cpu_percent)}"
        line += f"  ·  🧠 RAM {format_ram(resources.peak_ram_mb)}"
        if model.local:
            line += f"  ·  🎮 {format_gpu(resources.gpu_vram_mb)}"

    # Citation count in the panel label, so the user sees whether the answer was
    # grounded without having to open anything.
    return answer.text, citation_markdown(answer), tool_trace_rows(answer), line


# --- providers --------------------------------------------------------------


def save_key(provider: str, key: str, session: dict):
    set_key(session, provider, key)
    # Never echo the key back into the textbox.
    return (
        "",
        _key_status_markdown(session),
        _model_banner(session),
        gr.update(choices=_model_choices(session)),
    )


def _key_status_markdown(session: dict) -> str:
    lines = ["| Sağlayıcı | Durum |", "|---|---|"]
    for provider, status in provider_status(session).items():
        state = f"✅ `{status.masked}`" if status.configured else "⬜ girilmedi"
        lines.append(f"| {PROVIDER_LABELS.get(provider, provider)} | {state} |")
    return "\n".join(lines)


def _model_choices(session: dict) -> list[str]:
    return [model.id for model in available_models(session, _local_names())]


def choose_model(model_id: str, session: dict):
    if not model_id:
        return "Model seçilmedi.", _model_banner(session)
    try:
        set_active_model(session, model_id, local_models=_local_names())
    except ValueError as error:
        return f"❌ {error}", _model_banner(session)
    note = ""
    if estimate_cost(model_id, 1000, 100) is None:
        note = (
            f"\n\n⚠️ **{model_id}** için fiyat girilmedi; maliyet hesaplanmayacak "
            "(`config/model_prices.json`)."
        )
    return f"✅ Aktif model: `{model_id}`{note}", _model_banner(session)


# --- local models -----------------------------------------------------------


def refresh_local():
    admin = OllamaAdmin()
    if not admin.is_available():
        return [], f"❌ Ollama'ya ulaşılamıyor (`{admin.base_url}`)."
    rows = [[m.name, format_size(m.size_bytes)] for m in admin.list_local()]
    return rows, f"{len(rows)} model yüklü."


def pull_model(name: str, progress=_PROGRESS):
    name = (name or "").strip()
    if not name:
        return "Model adı girin."
    admin = OllamaAdmin()

    def _on_progress(update):
        # Ollama does not always report a total; never fabricate a percentage.
        progress(update.fraction or 0, desc=pull_label(update.status, update.fraction))

    try:
        admin.pull(name, on_progress=_on_progress)
    except OllamaUnavailable as error:
        return f"❌ {error}"
    return f"✅ `{name}` indirildi. **Sağlayıcılar** sekmesinden seçebilirsiniz."


def delete_model(name: str):
    name = (name or "").strip()
    if not name:
        return "Silinecek model adını yazın."
    try:
        OllamaAdmin().delete(name)
    except OllamaUnavailable as error:
        return f"❌ {error}"
    return f"🗑️ `{name}` silindi."


# --- metrics ----------------------------------------------------------------


def _store() -> MetricsStore:
    return MetricsStore(Config.load().storage_dir / "metrics.db")


def load_metrics():
    store = _store()
    summaries = list(store.summary_by_model())
    runs = store.recent()
    if not runs:
        return None, None, "Henüz ölçüm yok. **Sohbet** sekmesinden bir soru sorun."

    summary_df = pd.DataFrame(summary_rows(summaries))
    runs_df = pd.DataFrame(
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
    )
    return summary_df, runs_df, f"{len(runs)} koşu · {len(summaries)} model."


def clear_metrics():
    _store().clear()
    return None, None, "🗑️ Ölçüm geçmişi silindi."


# --- evaluation -------------------------------------------------------------


def run_evaluation(model_ids: list[str], consented: bool, session: dict, progress=_PROGRESS):
    if not consented:
        return None, "⚠️ Devam etmek için maliyet ve süre onayını işaretleyin."
    if not model_ids:
        return None, "En az bir model seçin."

    cases = load_eval_set()
    results = []
    for index, model_id in enumerate(model_ids, start=1):
        agent = build_agent(Config.load(), model_id=model_id, session=session)

        def report(done, total, _question, _i=index, _m=model_id):
            progress(
                (_i - 1 + done / total) / len(model_ids),
                desc=f"{_m} — {done}/{total} soru",
            )

        results.append(evaluate(agent, cases, on_progress=report))

    return pd.DataFrame(comparison_rows(results)), f"✅ {len(results)} model değerlendirildi."


def eval_estimate(model_ids: list[str]) -> str:
    if not model_ids:
        return ""
    cases = load_eval_set()
    known, unknown = 0.0, []
    for model_id in model_ids:
        estimate = estimate_eval_cost(model_id, len(cases))
        if estimate is None:
            unknown.append(model_id)
        else:
            known += estimate
    text = (
        f"Tahmini maliyet (**yaklaşık, ±%50**): {format_cost(known)}  ·  "
        f"{len(model_ids)} model × {len(cases)} soru."
    )
    if unknown:
        text += f"\n\n⚠️ Fiyatı bilinmeyen: {', '.join(unknown)} — maliyet eksik."
    text += "\n\n⚠️ Bu işlem **dakikalar** sürer ve bulut modellerinde **ücretlidir**."
    return text


# --- layout -----------------------------------------------------------------

CSS = """
.gradio-container { max-width: 900px !important; }
footer { display: none !important; }

/* Header: title and active model on one line, not two stacked blocks. */
#topbar { display: flex; align-items: baseline; justify-content: space-between;
          gap: 1rem; flex-wrap: wrap; margin-bottom: 0.2rem; }
#topbar h1 { margin: 0; font-size: 1.35rem; }
#topbar .sub { font-size: 0.8rem; opacity: 0.65; }
#banner { font-size: 0.85rem; opacity: 0.9; white-space: nowrap; }

/* Everything about the last answer sits in one bordered card directly under
   the chat, so sources / tools / cost read as belonging to that answer. */
#answer-card { border: 1px solid var(--border-color-primary); border-radius: 10px;
               padding: 0.35rem 0.75rem; margin-top: 0.5rem; }
#answer-card .label-wrap { font-size: 0.9rem !important; }
#metrics-line { font-size: 0.82rem; opacity: 0.75; text-align: right;
                margin: 0.15rem 0.2rem 0 0; }
#hint { font-size: 0.78rem; opacity: 0.6; margin-top: 0.35rem; }

/* Compact the example buttons — they were dominating the column. */
#examples button { font-size: 0.8rem !important; padding: 0.3rem 0.6rem !important; }
"""


def build_ui() -> gr.Blocks:
    with gr.Blocks(
        title="Şirket Bilgi Asistanı", theme=gr.themes.Soft(), css=CSS, fill_height=True
    ) as demo:
        session = gr.State({})

        with gr.Row(elem_id="topbar"):
            gr.HTML(
                "<div><h1>📚 Şirket Bilgi Asistanı</h1>"
                "<div class='sub'>İK · araç prosedürü · çalışan SSS · ürün taksonomisi · KÜB</div>"
                "</div>"
            )
            banner = gr.Markdown(elem_id="banner")

        with gr.Tabs():
            # ---- chat ----
            #
            # One column, top to bottom in the order the user actually needs it:
            # conversation → ask → what backed the answer. The sources and tool
            # trace used to sit in a separate right-hand column, which detached
            # them from the answer they describe; they are now a single card
            # directly under the input.
            with gr.Tab("💬 Sohbet"):
                # `gr.ChatInterface` is Gradio's purpose-built chat module: it
                # owns the transcript, input box, submit/stop buttons, examples,
                # autoscroll and retry/undo. The earlier hand-assembled
                # Chatbot + Textbox + Button had to reinvent each of those, and
                # the surrounding panels ended up wherever there was room.
                #
                # The three panels below are `additional_outputs`, so Gradio
                # refreshes them from the same call that produces the answer —
                # they update together, in place, instead of being separate
                # wiring the reader has to connect mentally.
                # Declared with render=False so they can be *defined* here (the
                # ChatInterface below needs the objects) but *placed* after it —
                # Gradio draws components where .render() is called.
                sources_md = gr.Markdown("_Henüz soru sorulmadı._", render=False)
                trace_table = gr.Dataframe(
                    headers=["araç", "argümanlar", "karakter", "kaynak"],
                    col_count=(4, "fixed"),
                    interactive=False,
                    wrap=True,
                    render=False,
                )
                metrics_md = gr.Markdown(elem_id="metrics-line", render=False)
                name_box = gr.Textbox(
                    label="Adınız (isteğe bağlı)",
                    info="Modele iletilir; ölçüm veritabanına yazılmaz.",
                    placeholder="Berkin",
                    render=False,
                )

                gr.ChatInterface(
                    fn=ask,
                    type="messages",
                    additional_inputs=[session, name_box],
                    additional_outputs=[sources_md, trace_table, metrics_md],
                    additional_inputs_accordion=gr.Accordion("⚙️ Oturum ayarları", open=False),
                    chatbot=gr.Chatbot(
                        type="messages",
                        height=420,
                        show_label=False,
                        show_copy_button=True,
                        avatar_images=(None, "📚"),
                        placeholder=(
                            "<div style='opacity:.6'>Belgeler hakkında bir soru sorun.<br>"
                            "<small>İK · araç prosedürü · çalışan SSS · taksonomi · KÜB</small>"
                            "</div>"
                        ),
                    ),
                    textbox=gr.Textbox(
                        placeholder="Sorunuz…", show_label=False, autofocus=True, scale=9
                    ),
                    # With additional_inputs, each example is a row: the message
                    # followed by a value per additional input (session, name).
                    # `None` leaves those untouched.
                    examples=[[question, None, None] for question in EXAMPLES],
                    example_labels=[
                        "🌴 Yıllık izin",
                        "⛽ Yakıt limiti (DOCX tablosu)",
                        "💊 Aksef kontrendikasyon (PDF)",
                        "🧬 Vitatin95 (XLSX)",
                    ],
                    save_history=True,
                    show_progress="minimal",
                )

                # "Where did this answer come from?" — placed directly under the
                # conversation, in one card, in the order a reviewer checks it.
                metrics_md.render()
                with gr.Column(elem_id="answer-card"):
                    with gr.Accordion("📎 Kaynaklar", open=True):
                        sources_md.render()
                    with gr.Accordion("🔧 Araç çağrıları", open=False):
                        trace_table.render()

            # ---- providers ----
            with gr.Tab("⚙️ Sağlayıcılar"):
                # Two steps, in order: give a key, then pick the model it unlocks.
                with gr.Group():
                    gr.Markdown("#### 1 · API anahtarı")
                    cloud = [p for p in providers() if p != "ollama"]
                    with gr.Row():
                        provider_dd = gr.Dropdown(
                            cloud, value=cloud[0], label="Sağlayıcı", filterable=False, scale=2
                        )
                        key_box = gr.Textbox(
                            label="Anahtar", type="password", placeholder="sk-…", scale=3
                        )
                        save_btn = gr.Button("Kaydet", variant="primary", scale=1, min_width=90)
                    key_status = gr.Markdown()
                    gr.Markdown(
                        "🔒 Anahtarlar **yalnızca bu oturumun belleğinde** tutulur — diske "
                        "yazılmaz, log'a düşmez, sekmeyi kapatınca silinir.",
                        elem_id="hint",
                    )

                with gr.Group():
                    gr.Markdown("#### 2 · Aktif model")
                    with gr.Row():
                        model_dd = gr.Dropdown(
                            label="Soruları hangi model cevaplasın?",
                            filterable=False,
                            scale=3,
                        )
                        use_btn = gr.Button("Kullan", variant="primary", scale=1, min_width=90)
                    model_note = gr.Markdown()

            # ---- local models ----
            with gr.Tab("📦 Yerel Modeller"):
                with gr.Group():
                    with gr.Row():
                        local_status = gr.Markdown()
                        refresh_btn = gr.Button("🔄 Yenile", scale=0, min_width=100)
                    local_table = gr.Dataframe(
                        headers=["model", "boyut"], col_count=(2, "fixed"), interactive=False
                    )
                with gr.Group():
                    with gr.Row():
                        pull_box = gr.Dropdown(
                            label="İndirilecek model",
                            choices=suggested_models([]),
                            allow_custom_value=True,
                            scale=3,
                        )
                        pull_btn = gr.Button("İndir", variant="primary", scale=1, min_width=90)
                    with gr.Row():
                        del_box = gr.Textbox(label="Silinecek model adı", scale=3)
                        del_btn = gr.Button("Sil", variant="stop", scale=1, min_width=90)
                    local_note = gr.Markdown()
                    gr.Markdown(
                        "⚠️ Modeller birkaç GB olabilir; indirme **dakikalar** sürer.",
                        elem_id="hint",
                    )

            # ---- metrics ----
            with gr.Tab("📊 Metrikler"):
                with gr.Row():
                    metrics_note = gr.Markdown()
                    load_btn = gr.Button("🔄 Yükle", variant="primary", scale=0, min_width=100)
                    wipe_btn = gr.Button("🗑️ Temizle", variant="stop", scale=0, min_width=100)
                with gr.Group():
                    gr.Markdown("#### Model karşılaştırması")
                    summary_table = gr.Dataframe(interactive=False, wrap=True)
                with gr.Group():
                    gr.Markdown("#### Son koşular")
                    runs_table = gr.Dataframe(interactive=False, wrap=True)
                gr.Markdown(
                    "ℹ️ Sorular ölçüm veritabanına kaydedilir. Gerçek bir dağıtımda bu "
                    "kişisel veri içerebilir.",
                    elem_id="hint",
                )

            # ---- evaluation ----
            with gr.Tab("🎯 Değerlendirme"):
                gr.Markdown(
                    f"{len(load_eval_set())} soruluk sabit set: atıf oranı, kaynak "
                    "isabeti, kanıt isabeti ve konu dışı red isabeti ölçülür. "
                    "Cevabın **üslubu puanlanmaz**."
                )
                with gr.Group():
                    eval_models = gr.Dropdown(label="Karşılaştırılacak modeller", multiselect=True)
                    eval_note = gr.Markdown()
                    with gr.Row():
                        eval_consent = gr.Checkbox(label="Maliyeti ve süreyi anladım", scale=3)
                        eval_btn = gr.Button("Başlat", variant="primary", scale=1, min_width=90)
                eval_status = gr.Markdown()
                eval_table = gr.Dataframe(interactive=False, wrap=True)

        # ---- wiring ----
        # The chat tab needs no wiring: ChatInterface binds submit, examples,
        # retry/undo/clear and the additional in/outputs itself.

        save_btn.click(
            save_key, [provider_dd, key_box, session], [key_box, key_status, banner, model_dd]
        )
        use_btn.click(choose_model, [model_dd, session], [model_note, banner])

        refresh_btn.click(refresh_local, None, [local_table, local_status])
        pull_btn.click(pull_model, [pull_box], [local_note])
        del_btn.click(delete_model, [del_box], [local_note])

        load_btn.click(load_metrics, None, [summary_table, runs_table, metrics_note])
        wipe_btn.click(clear_metrics, None, [summary_table, runs_table, metrics_note])

        eval_models.change(eval_estimate, [eval_models], [eval_note])
        eval_btn.click(
            run_evaluation, [eval_models, eval_consent, session], [eval_table, eval_status]
        )

        # Populate everything that depends on session state once, at load.
        def _on_load(session_state):
            choices = _model_choices(session_state)
            return (
                _model_banner(session_state),
                _key_status_markdown(session_state),
                gr.update(choices=choices),
                gr.update(choices=choices),
                *refresh_local(),
            )

        demo.load(
            _on_load,
            [session],
            [banner, key_status, model_dd, eval_models, local_table, local_status],
        )

    return demo


if __name__ == "__main__":
    build_ui().launch(server_name="0.0.0.0", server_port=7860, show_api=False)
