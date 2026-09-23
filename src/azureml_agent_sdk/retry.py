"""Exponential backoff + jitter retries for AOAI rate limits and transient
errors (P2-04).

Retries on the ``openai`` exception types that signal a rate limit (429),
a connection problem, or a transient server error (5xx) -- the set that is
generally safe to retry against Azure OpenAI. Delay grows as
``base_delay * 2 ** (attempt - 1)``, capped at ``max_delay``, plus a random
jitter term bounded by ``jitter`` (a fraction of the capped delay).
"""
from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

import openai

T = TypeVar("T")

DEFAULT_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.InternalServerError,
)


class RetryPolicy:
    """Calls a function, retrying on transient AOAI errors with backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: float = 0.1,
        retryable_exceptions: tuple[type[BaseException], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
        sleep: Callable[[float], None] = time.sleep,
        random_func: Callable[[], float] = random.random,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if base_delay <= 0:
            raise ValueError("base_delay must be > 0")
        if max_delay < base_delay:
            raise ValueError("max_delay must be >= base_delay")
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self._sleep = sleep
        self._random = random_func

    def compute_delay(self, attempt: int) -> float:
        """Return the delay (seconds) before retry number ``attempt`` (1-indexed)."""
        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        return delay + delay * self.jitter * self._random()

    def call(self, fn: Callable[..., T], *args: object, **kwargs: object) -> T:
        """Call ``fn(*args, **kwargs)``, retrying on retryable_exceptions."""
        attempt = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except self.retryable_exceptions:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                self._sleep(self.compute_delay(attempt))
