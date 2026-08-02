"""The question-answering agent: a tool-calling loop with three safety layers.

Layer 1 refuses off-topic questions on retrieval score alone, before any LLM
call. Layer 2 is the grounded system prompt. Layer 3 rejects any answer that
cites nothing. See docs/02-karar-kaydi.md ADR-008.
"""

import re
from typing import Any

from src.rag.models import Answer
from src.rag.prompts import (
    CITATION_REMINDER,
    CITATION_REPAIR,
    NO_INFO_TEMPLATE,
    REFUSAL_TEMPLATE,
    SYSTEM_PROMPT,
)
from src.rag.tools import TOOL_SCHEMAS

_CITATION_MARKER = re.compile(r"\[(\d+)\]")
_SOURCE_LINE = re.compile(r"^\[(\d+)\]\s+(.+)$", re.MULTILINE)


def extract_citations(text: str, tool_outputs: list[str]) -> list[str]:
    """Map [n] markers in the answer back to the citation labels the tools returned."""
    labels: dict[str, str] = {}
    for output in tool_outputs:
        for number, label in _SOURCE_LINE.findall(output):
            labels.setdefault(number, label.strip())
    seen: list[str] = []
    for number in _CITATION_MARKER.findall(text):
        label = labels.get(number)
        if label and label not in seen:
            seen.append(label)
    return seen


class Agent:
    def __init__(self, retriever, toolbox, llm, max_tool_turns: int = 3) -> None:
        self.retriever = retriever
        self.toolbox = toolbox
        self.llm = llm
        self.max_tool_turns = max_tool_turns

    def answer(self, question: str) -> Answer:
        """Answer a question, or refuse when the knowledge base cannot support one."""
        hits = self.retriever.search(question, top_k=5)
        if not self.retriever.is_confident(hits):
            return Answer(text=REFUSAL_TEMPLATE)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        trace: list[dict[str, Any]] = []
        outputs: list[str] = []
        final_text = ""

        for _ in range(self.max_tool_turns):
            response = self.llm.chat(messages, TOOL_SCHEMAS)

            if not response.tool_calls:
                if not outputs:
                    # The model answered without consulting the documents. Small
                    # local models skip the tool call unpredictably, so retrieve
                    # on its behalf rather than losing the answer to layer 3.
                    self._add_tool_result(
                        messages,
                        trace,
                        outputs,
                        name="search_documents",
                        arguments={"query": question},
                        injected=True,
                    )
                    continue
                final_text = response.text or ""
                break

            for call in response.tool_calls:
                self._add_tool_result(
                    messages, trace, outputs, name=call.name, arguments=call.arguments
                )

        citations = extract_citations(final_text, outputs)
        if not citations and outputs and final_text:
            # The passages were retrieved but the answer carries no [n] marker.
            # Sampling makes this intermittent, so ask once, explicitly, before
            # discarding an answer that may well be correct.
            messages.append({"role": "assistant", "content": final_text})
            messages.append({"role": "user", "content": CITATION_REPAIR})
            final_text = self.llm.chat(messages, TOOL_SCHEMAS).text or final_text
            citations = extract_citations(final_text, outputs)

        if not citations:
            return Answer(text=NO_INFO_TEMPLATE, tool_trace=trace)
        return Answer(text=final_text, citations=citations, tool_trace=trace)

    def _add_tool_result(
        self,
        messages: list[dict[str, Any]],
        trace: list[dict[str, Any]],
        outputs: list[str],
        *,
        name: str,
        arguments: dict[str, Any],
        injected: bool = False,
    ) -> None:
        """Run one tool and feed its output back into the conversation.

        The citation instruction rides on the tool result rather than the system
        prompt: measured on qwen2.5:7b-instruct, every extra sentence in the
        system prompt suppresses the initial tool call, but instructions that
        arrive after the tool has run do not.
        """
        output = self.toolbox.run(name, arguments)
        outputs.append(output)
        trace.append(
            {"name": name, "arguments": arguments, "chars": len(output), "injected": injected}
        )
        messages.append({"role": "assistant", "content": f"[tool: {name}]"})
        messages.append({"role": "user", "content": f"{output}\n\n{CITATION_REMINDER}"})
