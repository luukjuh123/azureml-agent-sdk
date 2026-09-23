"""Lifecycle hooks for AgentPipeline (P2-05).

Five events cover a pipeline run end to end: ``batch_start``,
``batch_complete``, ``agent_start``, ``agent_complete``, and ``error``. Hooks
can be plain sync callables or ``async def`` coroutine functions -- ``emit``
awaits a hook's result if it's awaitable, and calls hooks for the same event
in registration order. ``emit_sync`` lets synchronous callers (like
``AgentPipeline.run``) fire an event without managing an event loop
themselves.
"""
from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from collections.abc import Callable
from typing import Any

Hook = Callable[..., Any]

_EVENTS = frozenset({"batch_start", "batch_complete", "agent_start", "agent_complete", "error"})


class PipelineEvents:
    """A registry of lifecycle hooks, fired by name with arbitrary kwargs."""

    def __init__(self) -> None:
        self._hooks: dict[str, list[Hook]] = defaultdict(list)

    def on_batch_start(self, hook: Hook) -> Hook:
        return self._register("batch_start", hook)

    def on_batch_complete(self, hook: Hook) -> Hook:
        return self._register("batch_complete", hook)

    def on_agent_start(self, hook: Hook) -> Hook:
        return self._register("agent_start", hook)

    def on_agent_complete(self, hook: Hook) -> Hook:
        return self._register("agent_complete", hook)

    def on_error(self, hook: Hook) -> Hook:
        return self._register("error", hook)

    def _register(self, event: str, hook: Hook) -> Hook:
        self._hooks[event].append(hook)
        return hook

    async def emit(self, event: str, **kwargs: Any) -> None:
        """Call every hook registered for ``event``, awaiting async hooks."""
        if event not in _EVENTS:
            raise ValueError(f"unknown pipeline event: {event!r}")
        for hook in self._hooks.get(event, []):
            result = hook(**kwargs)
            if inspect.isawaitable(result):
                await result

    def emit_sync(self, event: str, **kwargs: Any) -> None:
        """Fire ``event`` from synchronous code, e.g. ``AgentPipeline.run``."""
        asyncio.run(self.emit(event, **kwargs))
