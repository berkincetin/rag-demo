# Task 7: Agent, Tools and Prompts

**Goal:** Port the LangGraph agent loop, the three tools, the prompts, and the
wiring function that assembles them.

**Files:**
- Create: `azure/rag/tools.py`, `azure/rag/prompts.py`, `azure/rag/agent.py`
- Create: `azure/rag/build.py`
- Create: `azure/tests/test_agent.py`

**Interfaces:**
- Consumes: `Retriever` (Task 6), `AzureOpenAIClient` (Task 3), `Answer` (Task 4)
- Produces:
  ```python
  # azure/rag/tools.py
  TOOL_SCHEMAS: list[dict[str, Any]]

  class ToolBox:
      def __init__(self, retriever: Retriever) -> None: ...
      def search_documents(self, query: str, top_k: int = 5,
                           source_filter: str | None = None) -> str: ...
      def lookup_section(self, document: str, section: str) -> str: ...
      def list_documents(self) -> str: ...
      def run(self, name: str, arguments: dict[str, Any]) -> str: ...

  # azure/rag/agent.py
  def extract_citations(text: str, tool_outputs: list[str]) -> list[str]: ...

  class Agent:
      def __init__(self, retriever, toolbox, llm,
                   max_tool_turns: int = 3, metrics=None) -> None: ...
      def answer(self, question: str, memory=None,
                 user_name: str | None = None) -> Answer: ...

  # azure/rag/build.py
  def build_agent(config: AzureConfig | None = None) -> Agent: ...
  ```

---

## Method

`tools.py`, `prompts.py` and `agent.py` are copied with imports rewritten.
The agent's three-layer safety net — the confidence gate, the citation
repair pass, and context injection when no tool is called — is behaviour the
case is graded on. **Do not simplify any of it.**

`build.py` is new: it replaces `src/rag/cli.py`'s `build_agent`, minus the
provider resolution and session credential store (there is one provider now,
and its key comes from the environment).

- [ ] **Step 1: Write the failing tests**

Create `azure/tests/test_agent.py`:

```python
"""Agent control flow with a mocked LLM. Output text is never asserted on."""

from azure.rag.agent import Agent, extract_citations
from azure.rag.llm_client import LLMResponse, ToolCall
from azure.rag.models import Chunk, SearchHit, TokenUsage


class FakeLLM:
    """Returns queued responses and records the messages it received."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.calls: list[list[dict]] = []

    def chat(self, messages, tools=None) -> LLMResponse:
        self.calls.append(messages)
        return self.responses.pop(0)


class FakeRetriever:
    def __init__(self, confident: bool, hits=None) -> None:
        self.confident = confident
        self.hits = hits or []

    def search(self, query, top_k=5, source_filter=None):
        return self.hits

    def is_confident(self, hits) -> bool:
        return self.confident


class FakeToolBox:
    def __init__(self, output: str = "[1] belge.docx — Bölüm 1\nİçerik") -> None:
        self.output = output
        self.calls: list[tuple[str, dict]] = []

    def run(self, name, arguments) -> str:
        self.calls.append((name, arguments))
        return self.output


def _hit(cosine: float = 0.9, bm25: float = 9.0) -> SearchHit:
    chunk = Chunk(
        chunk_id="c1",
        text="Aylık yakıt limiti 1.500 TL/ay olarak belirlenmiştir.",
        search_text="aylik yakit limiti",
        citation_label="arac.docx — Bölüm 3",
        metadata={"source_file": "arac.docx"},
    )
    return SearchHit(chunk=chunk, score=1.0, cosine=cosine, bm25=bm25)


def test_refuses_when_retrieval_is_not_confident():
    """Off-topic questions must not reach the LLM as answerable."""
    llm = FakeLLM([LLMResponse(text="Bilmiyorum.")])
    agent = Agent(FakeRetriever(confident=False), FakeToolBox(), llm)

    answer = agent.answer("Bugün hava nasıl?")

    assert answer.citations == []


def test_runs_a_requested_tool_and_feeds_the_result_back():
    llm = FakeLLM(
        [
            LLMResponse(tool_calls=[ToolCall(id="1", name="search_documents",
                                             arguments={"query": "yakıt"})]),
            LLMResponse(text="Aylık yakıt limiti 1.500 TL/ay'dır [1]."),
        ]
    )
    toolbox = FakeToolBox()
    agent = Agent(FakeRetriever(confident=True, hits=[_hit()]), toolbox, llm)

    answer = agent.answer("Yakıt limiti nedir?")

    assert toolbox.calls[0][0] == "search_documents"
    assert answer.citations


def test_stops_at_max_tool_turns():
    """A model that only ever asks for tools must not loop forever."""
    always_tool = [
        LLMResponse(tool_calls=[ToolCall(id=str(n), name="search_documents",
                                         arguments={"query": "x"})])
        for n in range(10)
    ]
    llm = FakeLLM(always_tool)
    agent = Agent(FakeRetriever(confident=True, hits=[_hit()]), FakeToolBox(), llm,
                  max_tool_turns=2)

    agent.answer("soru")

    assert len(llm.calls) <= 3


def test_accumulates_token_usage_across_turns():
    llm = FakeLLM(
        [
            LLMResponse(
                tool_calls=[ToolCall(id="1", name="search_documents", arguments={"query": "x"})],
                usage=TokenUsage(100, 10),
            ),
            LLMResponse(text="Cevap [1].", usage=TokenUsage(200, 20)),
        ]
    )
    agent = Agent(FakeRetriever(confident=True, hits=[_hit()]), FakeToolBox(), llm)

    answer = agent.answer("soru")

    assert answer.usage.input_tokens == 300
    assert answer.usage.output_tokens == 30


def test_extract_citations_maps_markers_to_labels():
    outputs = ["[1] arac.docx — Bölüm 3\nİçerik"]

    citations = extract_citations("Limit 1.500 TL/ay [1].", outputs)

    assert citations == ["arac.docx — Bölüm 3"]


def test_extract_citations_ignores_unmatched_markers():
    citations = extract_citations("Cevap [7].", ["[1] arac.docx — Bölüm 3"])

    assert citations == []
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `pytest azure/tests/test_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'azure.rag.agent'`

- [ ] **Step 3: Copy tools, prompts and agent**

```bash
cp src/rag/tools.py   azure/rag/tools.py
cp src/rag/prompts.py azure/rag/prompts.py
cp src/rag/agent.py   azure/rag/agent.py
```

Then in all three:

- Rewrite `from src.rag.` → `from azure.rag.`
- In `agent.py`, change the LLM import to `from azure.rag.llm_client import ...`
- In `agent.py`, if `_provider_of` maps model ids to provider names, replace
  its body with `return "azure_openai"` — there is one provider now

Verify:

```bash
grep -rn "src\.rag" azure/rag/
```

Expected: no output.

- [ ] **Step 4: Run the tests and verify they pass**

Run: `pytest azure/tests/test_agent.py -v`
Expected: 6 passed

If `Agent.__init__` requires a `metrics` store that Task 9 has not created
yet, pass `metrics=None` — the signature already defaults it.

- [ ] **Step 5: Write the wiring module**

Create `azure/rag/build.py`:

```python
"""Assemble the agent from a built index.

Replaces src/rag/cli.py's build_agent. Two things it deliberately drops:
provider resolution (there is one provider) and the session credential store
(the key comes from a Container Apps secret via the environment).
"""

from azure.rag.agent import Agent
from azure.rag.config import AzureConfig
from azure.rag.embedder import AzureOpenAIEmbedder
from azure.rag.index import load_index
from azure.rag.llm_client import AzureOpenAIClient
from azure.rag.retriever import Retriever
from azure.rag.tools import ToolBox


def build_agent(config: AzureConfig | None = None) -> Agent:
    """Wire retriever, tools and LLM into an agent."""
    config = config or AzureConfig.load()

    embedder = AzureOpenAIEmbedder(config)
    index = load_index(config.storage_dir)
    retriever = Retriever(
        index=index,
        embedder=embedder,
        min_cosine=config.min_cosine,
        min_bm25=config.min_bm25,
    )
    return Agent(
        retriever,
        ToolBox(retriever),
        AzureOpenAIClient(config),
        config.max_tool_turns,
    )
```

Task 9 adds the metrics store to this function.

- [ ] **Step 6: Confirm the local path is untouched**

```bash
git status --short src/ tests/ gradio_app.py docker-compose.yml
```

Expected: no output.

- [ ] **Step 7: Quality gate**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 8: Commit**

```bash
git add azure/
git commit -m "feat(azure): add agent loop, tools and prompts"
```
