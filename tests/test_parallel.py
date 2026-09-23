"""Tests for ParallelAgentGroup (P2-01): run N agents concurrently on the same
batch output via asyncio.gather, with a configurable concurrency limit."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import pytest

from azureml_agent_sdk.agent import AgentResponse
from azureml_agent_sdk.parallel import ParallelAgentGroup


@dataclass
class _FakeConfig:
    name: str


class _SleepingAgent:
    """A fake agent whose ``run`` blocks for ``delay`` seconds, like a real
    synchronous AOAI call would. Tracks concurrent-call high-water-mark via a
    shared counter so tests can assert on real overlap, not just wall time."""

    def __init__(self, name: str, delay: float, tracker: "_ConcurrencyTracker") -> None:
        self.config = _FakeConfig(name=name)
        self._delay = delay
        self._tracker = tracker

    def run(self, user_message: str, history: list[dict[str, str]] | None = None) -> AgentResponse:
        self._tracker.enter()
        try:
            time.sleep(self._delay)
        finally:
            self._tracker.exit()
        return AgentResponse(content=f"{self.config.name}:{user_message}")


class _ConcurrencyTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current = 0
        self.max_seen = 0

    def enter(self) -> None:
        with self._lock:
            self._current += 1
            self.max_seen = max(self.max_seen, self._current)

    def exit(self) -> None:
        with self._lock:
            self._current -= 1


async def test_runs_agents_concurrently_not_sequentially() -> None:
    tracker = _ConcurrencyTracker()
    agents = [_SleepingAgent(f"agent-{i}", delay=0.2, tracker=tracker) for i in range(4)]
    group = ParallelAgentGroup(agents)

    start = time.monotonic()
    await group.run("row-1")
    elapsed = time.monotonic() - start

    # Sequential execution would take ~0.8s; concurrent execution should be
    # close to a single 0.2s delay.
    assert elapsed < 0.6
    assert tracker.max_seen > 1


async def test_result_ordering_matches_agent_order_regardless_of_delay() -> None:
    tracker = _ConcurrencyTracker()
    # First agent sleeps longest, so if ordering depended on completion order
    # it would come last -- it must still be first in the results.
    agents = [
        _SleepingAgent("slow", delay=0.3, tracker=tracker),
        _SleepingAgent("medium", delay=0.15, tracker=tracker),
        _SleepingAgent("fast", delay=0.01, tracker=tracker),
    ]
    group = ParallelAgentGroup(agents)

    results = await group.run("row-1")

    assert [r.content for r in results] == [
        "slow:row-1",
        "medium:row-1",
        "fast:row-1",
    ]


async def test_max_concurrency_limits_overlap() -> None:
    tracker = _ConcurrencyTracker()
    agents = [_SleepingAgent(f"agent-{i}", delay=0.15, tracker=tracker) for i in range(4)]
    group = ParallelAgentGroup(agents, max_concurrency=1)

    await group.run("row-1")

    assert tracker.max_seen == 1


async def test_max_concurrency_must_be_positive() -> None:
    with pytest.raises(ValueError):
        ParallelAgentGroup([], max_concurrency=0)


async def test_run_batch_processes_every_row_for_every_agent() -> None:
    tracker = _ConcurrencyTracker()
    agents = [
        _SleepingAgent("a", delay=0.01, tracker=tracker),
        _SleepingAgent("b", delay=0.01, tracker=tracker),
    ]
    group = ParallelAgentGroup(agents)

    results = await group.run_batch(["row-1", "row-2"])

    assert [r.content for r in results[0]] == ["a:row-1", "b:row-1"]
    assert [r.content for r in results[1]] == ["a:row-2", "b:row-2"]


async def test_requires_at_least_one_agent_for_run() -> None:
    group = ParallelAgentGroup([])
    with pytest.raises(ValueError):
        await group.run("row-1")
