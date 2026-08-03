"""Short conversational memory, held in the session only.

Adding memory to a retrieval system has a trap: the score gate runs on the
user's text, and a follow-up like "peki ya müdür seviyesinde?" resembles no
document, so the gate would refuse a perfectly reasonable question. The fix is
`retrieval_query` — the *search* is enriched with the previous question while
the conversation the model sees keeps the user's words untouched.

Conversation content is never written to disk, for the same reason API keys
are not: it belongs to the session, not to the machine.
"""

from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Turn:
    question: str
    answer: str


class ConversationMemory:
    """The last few question/answer pairs of one session."""

    def __init__(self, max_turns: int = 5) -> None:
        self.max_turns = max_turns
        self._turns: deque[Turn] = deque(maxlen=max_turns)

    def add(self, question: str, answer: str) -> None:
        self._turns.append(Turn(question=question, answer=answer))

    def recent_turns(self) -> list[Turn]:
        return list(self._turns)

    def last_turn(self) -> Turn | None:
        return self._turns[-1] if self._turns else None

    def clear(self) -> None:
        self._turns.clear()

    def as_messages(self) -> list[dict[str, Any]]:
        """History rendered as chat messages, oldest first."""
        messages: list[dict[str, Any]] = []
        for turn in self._turns:
            messages.append({"role": "user", "content": turn.question})
            messages.append({"role": "assistant", "content": turn.answer})
        return messages

    def __len__(self) -> int:
        return len(self._turns)


def retrieval_query(question: str, memory: ConversationMemory | None) -> str:
    """What to search for — the question, widened by the previous one.

    Only the previous question is used: pulling in the whole history would
    drown the terms that actually matter for this turn.
    """
    if memory is None:
        return question
    previous = memory.last_turn()
    if previous is None:
        return question
    return f"{previous.question} {question}"
