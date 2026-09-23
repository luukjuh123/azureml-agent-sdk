"""Tests for RetryPolicy (P2-04): exponential backoff + jitter for AOAI
rate-limit (429) and transient errors, with configurable max retries, base
delay, and max delay. Uses real ``openai`` exception types with a mocked
httpx response so no live AOAI credentials or network calls are required."""
from __future__ import annotations

import httpx
import openai
import pytest

from azureml_agent_sdk.retry import RetryPolicy


def _rate_limit_error() -> openai.RateLimitError:
    request = httpx.Request("POST", "https://example.openai.azure.com/chat/completions")
    response = httpx.Response(429, request=request)
    return openai.RateLimitError("rate limited", response=response, body=None)


def _server_error() -> openai.InternalServerError:
    request = httpx.Request("POST", "https://example.openai.azure.com/chat/completions")
    response = httpx.Response(500, request=request)
    return openai.InternalServerError("internal error", response=response, body=None)


class _FakeClock:
    """Records requested delays instead of actually sleeping."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    def sleep(self, delay: float) -> None:
        self.delays.append(delay)


def test_retries_on_rate_limit_then_returns_success() -> None:
    clock = _FakeClock()
    policy = RetryPolicy(max_retries=3, base_delay=0.01, sleep=clock.sleep, random_func=lambda: 0.0)
    calls = {"count": 0}

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise _rate_limit_error()
        return "ok"

    result = policy.call(flaky)

    assert result == "ok"
    assert calls["count"] == 3
    assert len(clock.delays) == 2


def test_retries_on_transient_server_error() -> None:
    clock = _FakeClock()
    policy = RetryPolicy(max_retries=2, base_delay=0.01, sleep=clock.sleep, random_func=lambda: 0.0)
    calls = {"count": 0}

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] < 2:
            raise _server_error()
        return "ok"

    result = policy.call(flaky)

    assert result == "ok"
    assert calls["count"] == 2


def test_gives_up_after_max_retries_exhausted() -> None:
    clock = _FakeClock()
    policy = RetryPolicy(max_retries=2, base_delay=0.01, sleep=clock.sleep, random_func=lambda: 0.0)
    calls = {"count": 0}

    def always_fails() -> str:
        calls["count"] += 1
        raise _rate_limit_error()

    with pytest.raises(openai.RateLimitError):
        policy.call(always_fails)

    # 1 initial attempt + 2 retries = 3 calls, 2 sleeps between them.
    assert calls["count"] == 3
    assert len(clock.delays) == 2


def test_non_retryable_exception_propagates_without_retrying() -> None:
    clock = _FakeClock()
    policy = RetryPolicy(max_retries=3, base_delay=0.01, sleep=clock.sleep, random_func=lambda: 0.0)
    calls = {"count": 0}

    def raises_value_error() -> str:
        calls["count"] += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        policy.call(raises_value_error)

    assert calls["count"] == 1
    assert clock.delays == []


def test_delay_doubles_each_attempt_with_no_jitter() -> None:
    policy = RetryPolicy(max_retries=5, base_delay=1.0, max_delay=100.0, jitter=0.0)

    assert policy.compute_delay(1) == 1.0
    assert policy.compute_delay(2) == 2.0
    assert policy.compute_delay(3) == 4.0
    assert policy.compute_delay(4) == 8.0


def test_delay_is_capped_at_max_delay() -> None:
    policy = RetryPolicy(max_retries=10, base_delay=1.0, max_delay=5.0, jitter=0.0)

    assert policy.compute_delay(10) == 5.0


def test_jitter_adds_bounded_randomness_on_top_of_backoff() -> None:
    # jitter=0.5, random_func fixed at 1.0 (its max) -> delay = base * (1 + 0.5)
    policy = RetryPolicy(max_retries=1, base_delay=2.0, jitter=0.5, random_func=lambda: 1.0)

    assert policy.compute_delay(1) == 3.0


def test_max_retries_must_be_non_negative() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(max_retries=-1)


def test_max_delay_must_be_at_least_base_delay() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(base_delay=10.0, max_delay=1.0)


def test_base_delay_must_be_positive() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(base_delay=0.0)


def test_zero_max_retries_means_no_retrying() -> None:
    clock = _FakeClock()
    policy = RetryPolicy(max_retries=0, base_delay=0.01, sleep=clock.sleep)
    calls = {"count": 0}

    def always_fails() -> str:
        calls["count"] += 1
        raise _rate_limit_error()

    with pytest.raises(openai.RateLimitError):
        policy.call(always_fails)

    assert calls["count"] == 1
    assert clock.delays == []
