# Task 13: CLI and Streamlit front-ends

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 12](12-agent.md)
**Next:** [Task 14](14-demo-docker-readme.md)

---

**Files:**
- Create: `src/rag/cli.py`, `app.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `Config`, `load_index`, `Retriever`, `ToolBox`, `get_client`, `Agent`
- Produces: `build_agent(config: Config | None = None) -> Agent`, `format_answer(answer: Answer) -> str`, `main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
from src.rag.cli import format_answer
from src.rag.models import Answer


def test_format_answer_appends_a_sources_block():
    answer = Answer(text="Cevap [1].", citations=["sss.xlsx — Genel SSS, satır 4"])

    output = format_answer(answer)

    assert "Cevap [1]." in output
    assert "Kaynaklar:" in output
    assert "sss.xlsx — Genel SSS, satır 4" in output


def test_format_answer_omits_the_sources_block_when_there_are_none():
    output = format_answer(Answer(text="Bilgi bulamadım."))

    assert "Kaynaklar:" not in output


def test_format_answer_numbers_multiple_sources():
    answer = Answer(text="x", citations=["a.pdf — Bölüm 1, s.1", "b.docx — 2. BÖLÜM"])

    output = format_answer(answer)

    assert "1. a.pdf — Bölüm 1, s.1" in output
    assert "2. b.docx — 2. BÖLÜM" in output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.cli'`

- [ ] **Step 3: Write minimal `src/rag/cli.py`**

```python
"""Terminal front-end for the RAG agent."""

import sys

from src.rag.agent import Agent
from src.rag.config import Config
from src.rag.index import load_index
from src.rag.llm import get_client
from src.rag.models import Answer
from src.rag.retriever import Retriever
from src.rag.tools import ToolBox

_EXIT_WORDS = {"çıkış", "cikis", "exit", "quit"}


def build_agent(config: Config | None = None) -> Agent:
    """Wire the agent from a previously built index."""
    config = config or Config.load()
    index = load_index(config.storage_dir, config.embedding_model)
    retriever = Retriever(index, min_cosine=config.min_cosine)
    return Agent(retriever, ToolBox(retriever), get_client(config), config.max_tool_turns)


def format_answer(answer: Answer) -> str:
    """Render an answer with its numbered source list."""
    if not answer.citations:
        return answer.text
    sources = "\n".join(
        f"  {position}. {label}" for position, label in enumerate(answer.citations, start=1)
    )
    return f"{answer.text}\n\nKaynaklar:\n{sources}"


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    agent = build_agent()

    if argv:
        print(format_answer(agent.answer(" ".join(argv))))
        return 0

    print("Soru sorun ('çıkış' ile bitirin).")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if not question or question.lower() in _EXIT_WORDS:
            return 0
        print("\n" + format_answer(agent.answer(question)))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v --no-cov`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the CLI against the real index**

Run: `python -m src.rag.cli "Yıllık izin talebimi nasıl yaparım?"`
Expected: a Turkish answer with a `Kaynaklar:` block naming a real file. Turkish characters render correctly in PowerShell.

- [ ] **Step 6: Write `app.py`**

```python
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
```

- [ ] **Step 7: Run the Streamlit app and check it by hand**

Run: `streamlit run app.py`
Expected: the page loads at `localhost:8501`; each of the four example questions returns an answer with a populated Kaynaklar panel; an off-topic question shows the refusal and an empty tool trace.

- [ ] **Step 8: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/cli.py app.py tests/test_cli.py
git commit -m "feat(cli): add terminal and Streamlit front-ends"
```
