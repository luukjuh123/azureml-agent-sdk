"""Run N agents concurrently over the same batch output (P2-01).

Agents in this SDK expose a synchronous ``run`` method (real AOAI calls are
blocking HTTP requests), so true concurrency comes from dispatching each
agent's call onto its own thread via ``asyncio.to_thread`` and awaiting them
together with ``asyncio.gather``. A ``max_concurrency`` semaphore caps how
many of those calls are in flight at once, which matters for AOAI rate
limits.
"""
from __future__ import annotations

import asyncio
from typing import Any, Protocol

from azureml_agent_sdk.agent import AgentResponse


class _Agent(Protocol):
    config: Any

    def run(self, user_message: str, history: list[dict[str, str]] | None = None) -> AgentResponse: ...


class ParallelAgentGroup:
    """Runs every agent in the group against the same input concurrently."""

    def __init__(self, agents: list[_Agent], max_concurrency: int | None = None) -> None:
        if max_concurrency is not None and max_concurrency < 1:
            raise ValueError("max_concurrency must be a positive integer")
        self.agents = agents
        self.max_concurrency = max_concurrency

    async def run(
        self, user_message: str, history: list[dict[str, str]] | None = None
    ) -> list[AgentResponse]:
        """Run every agent against ``user_message`` concurrently.

        Returns responses in the same order as ``self.agents``, regardless of
        which agent finishes first.
        """
        if not self.agents:
            raise ValueError("ParallelAgentGroup requires at least one agent")

        semaphore = asyncio.Semaphore(self.max_concurrency) if self.max_concurrency else None

        async def _run_one(agent: _Agent) -> AgentResponse:
            if semaphore is None:
                return await asyncio.to_thread(agent.run, user_message, history)
            async with semaphore:
                return await asyncio.to_thread(agent.run, user_message, history)

        return list(await asyncio.gather(*(_run_one(agent) for agent in self.agents)))

    async def run_batch(
        self, messages: list[str], history: list[dict[str, str]] | None = None
    ) -> list[list[AgentResponse]]:
        """Run every agent against every message, sequentially per message.

        Returns one list of per-agent responses (in agent order) for each
        message, in message order.
        """
        return [await self.run(message, history) for message in messages]
