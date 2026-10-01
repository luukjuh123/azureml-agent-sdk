"""Route batch output rows to different agents based on a rule or classifier (P2-02).

Rules are ``(matcher, agent)`` pairs evaluated in order; the first matcher
that returns ``True`` for a row wins. A matcher is any callable taking a row
dict and returning a bool -- field-equality and regex matchers are provided
as convenience builders, but arbitrary classifier callables work too. An
optional ``default_agent`` is used when no rule matches.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from azureml_agent_sdk.agent import AgentResponse

RowMatcher = Callable[[dict[str, Any]], bool]


class _Agent(Protocol):
    config: Any

    def run(
        self, user_message: str, history: list[dict[str, str]] | None = None
    ) -> AgentResponse: ...


class NoMatchingAgentError(Exception):
    """Raised when no rule matches a row and no default_agent is configured."""


@dataclass
class _Rule:
    matcher: RowMatcher
    agent: _Agent


class AgentRouter:
    """Selects (and optionally runs) an agent for a batch output row."""

    def __init__(
        self,
        rules: list[tuple[RowMatcher, _Agent]],
        default_agent: _Agent | None = None,
    ) -> None:
        self.rules = [_Rule(matcher=matcher, agent=agent) for matcher, agent in rules]
        self.default_agent = default_agent

    def select_agent(self, row: dict[str, Any]) -> _Agent:
        """Return the first agent whose rule matches ``row``, else the default agent."""
        for rule in self.rules:
            if rule.matcher(row):
                return rule.agent
        if self.default_agent is not None:
            return self.default_agent
        raise NoMatchingAgentError(f"no rule matched row and no default_agent configured: {row!r}")

    def run(
        self, row: dict[str, Any], user_message: str, history: list[dict[str, str]] | None = None
    ) -> AgentResponse:
        """Select an agent for ``row`` and run it against ``user_message``."""
        agent = self.select_agent(row)
        return agent.run(user_message, history)

    @staticmethod
    def field_equals(field: str, value: Any) -> RowMatcher:
        """Build a matcher that checks ``row[field] == value``."""
        return lambda row: row.get(field) == value

    @staticmethod
    def field_matches(field: str, pattern: str) -> RowMatcher:
        """Build a matcher that checks ``pattern`` against ``str(row[field])``."""
        compiled = re.compile(pattern)

        def _matcher(row: dict[str, Any]) -> bool:
            if field not in row:
                return False
            return bool(compiled.search(str(row[field])))

        return _matcher
