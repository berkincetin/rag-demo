"""Core data structures shared across the Azure deployment.

Currently just `TokenUsage`, copied verbatim from `src/rag/models.py`. Task 4
appends the remaining dataclasses this module needs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenUsage:
    """Tokens a provider reported for one call.

    `None` means the provider did not report the number — which is not the same
    as reporting zero, so the fields are never defaulted to 0.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Sum across turns, treating unreported values as absent, not zero."""
        return TokenUsage(
            _add_optional(self.input_tokens, other.input_tokens),
            _add_optional(self.output_tokens, other.output_tokens),
        )


def _add_optional(left: int | None, right: int | None) -> int | None:
    if left is None:
        return right
    if right is None:
        return left
    return left + right
