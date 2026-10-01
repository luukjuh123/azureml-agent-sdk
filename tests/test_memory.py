"""Tests for AgentMemory (P2-03): per-agent conversation history with a
configurable max-token window that truncates the oldest messages first."""

from __future__ import annotations

from azureml_agent_sdk.memory import AgentMemory


def test_add_appends_messages_in_order() -> None:
    memory = AgentMemory(max_tokens=100)

    memory.add("user", "hello there")
    memory.add("assistant", "hi, how can I help")

    assert memory.history() == [
        {"role": "user", "content": "hello there"},
        {"role": "assistant", "content": "hi, how can I help"},
    ]


def test_default_token_counter_counts_whitespace_separated_words() -> None:
    memory = AgentMemory(max_tokens=100)

    memory.add("user", "one two three four")

    assert memory.total_tokens() == 4


def test_window_overflow_drops_oldest_messages_first() -> None:
    # Each message is 3 tokens; max_tokens=7 allows two messages (6 tokens)
    # but not three (9 tokens), so the oldest must be evicted.
    memory = AgentMemory(max_tokens=7)

    memory.add("user", "aaa bbb ccc")  # oldest -- should be evicted
    memory.add("assistant", "ddd eee fff")
    memory.add("user", "ggg hhh iii")

    history = memory.history()

    assert history == [
        {"role": "assistant", "content": "ddd eee fff"},
        {"role": "user", "content": "ggg hhh iii"},
    ]
    assert memory.total_tokens() <= 7


def test_always_keeps_the_most_recently_added_message_even_if_it_alone_exceeds_budget() -> None:
    memory = AgentMemory(max_tokens=2)

    memory.add("user", "one two three four five")

    assert memory.history() == [{"role": "user", "content": "one two three four five"}]


def test_custom_token_counter_is_used_for_truncation_decisions() -> None:
    # Character-based counter: budget of 8 chars fits "hi" (2) + "world" (5) = 7,
    # but adding "hey" (3 more, total 10) must evict "hi" to get back to 8.
    memory = AgentMemory(max_tokens=8, token_counter=len)

    memory.add("user", "hi")
    memory.add("assistant", "world")
    memory.add("user", "hey")

    assert memory.history() == [
        {"role": "assistant", "content": "world"},
        {"role": "user", "content": "hey"},
    ]


def test_empty_memory_has_zero_tokens_and_empty_history() -> None:
    memory = AgentMemory(max_tokens=50)

    assert memory.history() == []
    assert memory.total_tokens() == 0


def test_max_tokens_must_be_positive() -> None:
    import pytest

    with pytest.raises(ValueError):
        AgentMemory(max_tokens=0)
