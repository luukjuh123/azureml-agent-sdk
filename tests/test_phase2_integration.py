"""Integration tests for Phase 2 (P2-08): the new primitives composed
together the way a real pipeline would use them, with every Azure ML/AOAI
call mocked out via fakes.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import openai
import httpx
import pytest

from azureml_agent_sdk.agent import AgentResponse
from azureml_agent_sdk.memory import AgentMemory
from azureml_agent_sdk.parallel import ParallelAgentGroup
from azureml_agent_sdk.retry import RetryPolicy
from azureml_agent_sdk.router import AgentRouter


@dataclass
class _FakeConfig:
    name: str


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


class _SleepingAgent:
    def __init__(self, name: str, delay: float, tracker: _ConcurrencyTracker) -> None:
        self.config = _FakeConfig(name=name)
        self._delay = delay
        self._tracker = tracker

    def run(self, user_message: str, history=None) -> AgentResponse:
        self._tracker.enter()
        try:
            time.sleep(self._delay)
        finally:
            self._tracker.exit()
        return AgentResponse(content=f"{self.config.name}:{user_message}")


async def test_router_selects_a_parallel_agent_group_and_runs_it_concurrently() -> None:
    """AgentRouter can route to a ParallelAgentGroup, not just a single agent --
    the group then fans the row out to its own agents concurrently."""
    tracker = _ConcurrencyTracker()
    fraud_group = ParallelAgentGroup(
        [
            _SleepingAgent("fraud-checker", delay=0.1, tracker=tracker),
            _SleepingAgent("fraud-summarizer", delay=0.1, tracker=tracker),
        ]
    )
    default_group = ParallelAgentGroup([_SleepingAgent("default", delay=0.0, tracker=tracker)])
    router = AgentRouter(
        rules=[(AgentRouter.field_equals("category", "fraud"), fraud_group)],
        default_agent=default_group,
    )

    selected = router.select_agent({"category": "fraud", "amount": 500})
    assert selected is fraud_group

    responses = await selected.run("row-1")

    assert [r.content for r in responses] == ["fraud-checker:row-1", "fraud-summarizer:row-1"]
    assert tracker.max_seen > 1  # the group's two agents actually overlapped


def test_router_falls_back_to_default_group_for_unmatched_rows() -> None:
    tracker = _ConcurrencyTracker()
    fraud_group = ParallelAgentGroup([_SleepingAgent("fraud", delay=0.0, tracker=tracker)])
    default_group = ParallelAgentGroup([_SleepingAgent("default", delay=0.0, tracker=tracker)])
    router = AgentRouter(
        rules=[(AgentRouter.field_equals("category", "fraud"), fraud_group)],
        default_agent=default_group,
    )

    selected = router.select_agent({"category": "benign"})

    assert selected is default_group


def _rate_limit_error() -> openai.RateLimitError:
    request = httpx.Request("POST", "https://example.openai.azure.com/chat/completions")
    response = httpx.Response(429, request=request)
    return openai.RateLimitError("rate limited", response=response, body=None)


def test_retry_policy_wraps_a_router_selected_agent_and_updates_memory() -> None:
    """RetryPolicy retries a flaky call to a router-selected agent; once it
    succeeds, the turn is recorded in that agent's AgentMemory."""

    class _FlakyAgent:
        def __init__(self) -> None:
            self.config = _FakeConfig(name="reviewer")
            self.attempts = 0

        def run(self, user_message: str, history=None) -> AgentResponse:
            self.attempts += 1
            if self.attempts < 2:
                raise _rate_limit_error()
            return AgentResponse(content=f"reviewed: {user_message}")

    agent = _FlakyAgent()
    router = AgentRouter(rules=[], default_agent=agent)
    memory = AgentMemory(max_tokens=100)
    policy = RetryPolicy(max_retries=2, base_delay=0.001, sleep=lambda _delay: None)

    selected = router.select_agent({"category": "anything"})
    user_message = "please review row 1"
    response = policy.call(selected.run, user_message)
    memory.add("user", user_message)
    memory.add("assistant", response.content)

    assert agent.attempts == 2
    assert response.content == "reviewed: please review row 1"
    assert memory.history() == [
        {"role": "user", "content": "please review row 1"},
        {"role": "assistant", "content": "reviewed: please review row 1"},
    ]
