"""Tests for PipelineEvents (P2-05): on_batch_start, on_batch_complete,
on_agent_start, on_agent_complete, and on_error hooks, with both sync and
async hook support."""

from __future__ import annotations

import pytest

from azureml_agent_sdk.events import PipelineEvents


def test_registers_and_calls_a_sync_hook_with_kwargs() -> None:
    events = PipelineEvents()
    received = {}

    events.on_agent_start(lambda **kw: received.update(kw))

    events.emit_sync("agent_start", agent="reviewer", row={"id": 1})

    assert received == {"agent": "reviewer", "row": {"id": 1}}


async def test_registers_and_awaits_an_async_hook() -> None:
    events = PipelineEvents()
    received = {}

    async def hook(**kw):
        received.update(kw)

    events.on_batch_complete(hook)

    await events.emit("batch_complete", job_name="job-1")

    assert received == {"job_name": "job-1"}


async def test_multiple_hooks_for_same_event_all_fire_in_registration_order() -> None:
    events = PipelineEvents()
    calls: list[str] = []

    events.on_agent_complete(lambda **kw: calls.append("first"))
    events.on_agent_complete(lambda **kw: calls.append("second"))

    await events.emit("agent_complete")

    assert calls == ["first", "second"]


async def test_mixed_sync_and_async_hooks_for_the_same_event_both_fire() -> None:
    events = PipelineEvents()
    calls: list[str] = []

    events.on_error(lambda **kw: calls.append("sync"))

    async def async_hook(**kw):
        calls.append("async")

    events.on_error(async_hook)

    await events.emit("error", exc=ValueError("boom"))

    assert calls == ["sync", "async"]


def test_decorator_style_registration_returns_the_hook_unchanged() -> None:
    events = PipelineEvents()

    @events.on_batch_start
    def hook(**kw):
        return "called"

    assert hook(job_name="job-1") == "called"


async def test_event_with_no_registered_hooks_is_a_noop() -> None:
    events = PipelineEvents()

    await events.emit("agent_start")  # must not raise


def test_emit_unknown_event_raises_value_error() -> None:
    events = PipelineEvents()

    with pytest.raises(ValueError):
        events.emit_sync("not_a_real_event")


def test_all_five_lifecycle_events_are_registerable() -> None:
    events = PipelineEvents()
    fired: list[str] = []

    events.on_batch_start(lambda **kw: fired.append("batch_start"))
    events.on_batch_complete(lambda **kw: fired.append("batch_complete"))
    events.on_agent_start(lambda **kw: fired.append("agent_start"))
    events.on_agent_complete(lambda **kw: fired.append("agent_complete"))
    events.on_error(lambda **kw: fired.append("error"))

    for event in ("batch_start", "batch_complete", "agent_start", "agent_complete", "error"):
        events.emit_sync(event)

    assert fired == ["batch_start", "batch_complete", "agent_start", "agent_complete", "error"]
