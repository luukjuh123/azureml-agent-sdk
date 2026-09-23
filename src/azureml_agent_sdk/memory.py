"""Per-agent conversation history with a configurable max-token window (P2-03).

The window is enforced on every ``add()`` by evicting the oldest messages
first until the running total is within budget, matching how a chat
completion context window fills up over a long-running pipeline. The most
recently added message is always kept, even if it alone exceeds the budget,
so a single call never silently loses its own input.
"""
from __future__ import annotations

from collections.abc import Callable


def _default_token_counter(content: str) -> int:
    """Approximate token count as whitespace-separated word count."""
    return len(content.split())


class AgentMemory:
    """Holds one agent's conversation turns, bounded by a max-token window."""

    def __init__(
        self,
        max_tokens: int,
        token_counter: Callable[[str], int] | None = None,
    ) -> None:
        if max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer")
        self.max_tokens = max_tokens
        self._token_counter = token_counter or _default_token_counter
        self._messages: list[dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        """Append a turn and evict the oldest messages until back in budget."""
        self._messages.append({"role": role, "content": content})
        while len(self._messages) > 1 and self.total_tokens() > self.max_tokens:
            self._messages.pop(0)

    def history(self) -> list[dict[str, str]]:
        """Return the current window as a list of ``{"role", "content"}`` dicts."""
        return list(self._messages)

    def total_tokens(self) -> int:
        """Return the token count of every message currently in the window."""
        return sum(self._token_counter(message["content"]) for message in self._messages)
