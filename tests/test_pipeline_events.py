"""Tests that AgentPipeline fires PipelineEvents hooks at the correct
lifecycle points (P2-05): batch_start -> batch_complete -> (agent_start ->
agent_complete) per agent, and error whenever the trigger or an agent
raises."""

from __future__ import annotations

import pytest

from azureml_agent_sdk.batch_trigger import BatchJobResult
from azureml_agent_sdk.events import PipelineEvents
from azureml_agent_sdk.pipeline import AgentPipeline


class _FakeTriggerConfig:
    def __init__(self, endpoint_name):
        self.endpoint_name = endpoint_name


class _FakeTrigger:
    def __init__(self, job_result=None, error=None):
        self._job_result = job_result
        self._error = error
        self.config = _FakeTriggerConfig(endpoint_name="fraud-scoring")

    def run(self):
        if self._error is not None:
            raise self._error
        return self._job_result


class _FakeAgentConfig:
    def __init__(self, name):
        self.name = name


class _FakeAgent:
    def __init__(self, name, error=None):
        self.config = _FakeAgentConfig(name=name)
        self._error = error

    def run(self, user_message, history=None):
        if self._error is not None:
            raise self._error
        from azureml_agent_sdk.agent import AgentResponse

        return AgentResponse(content=f"ok: {user_message}")


def _fake_output_parser(rows):
    def parser(_path):
        return rows

    return parser


def test_hooks_fire_in_order_for_a_successful_run() -> None:
    events = PipelineEvents()
    fired: list[str] = []
    events.on_batch_start(lambda **kw: fired.append("batch_start"))
    events.on_batch_complete(lambda **kw: fired.append("batch_complete"))
    events.on_agent_start(lambda **kw: fired.append("agent_start"))
    events.on_agent_complete(lambda **kw: fired.append("agent_complete"))

    job_result = BatchJobResult(job_name="job-1", status="Completed", output_path="path")
    trigger = _FakeTrigger(job_result=job_result)
    agent = _FakeAgent(name="reviewer")
    pipeline = AgentPipeline(
        name="fraud-check",
        trigger=trigger,
        agents=[agent],
        output_parser=_fake_output_parser([{"id": 1}]),
        events=events,
    )

    pipeline.run()

    assert fired == ["batch_start", "batch_complete", "agent_start", "agent_complete"]


def test_agent_start_and_complete_fire_once_per_agent() -> None:
    events = PipelineEvents()
    starts: list[str] = []
    completes: list[str] = []
    events.on_agent_start(lambda **kw: starts.append(kw["agent"]))
    events.on_agent_complete(lambda **kw: completes.append(kw["agent"]))

    job_result = BatchJobResult(job_name="job-1", status="Completed", output_path="path")
    trigger = _FakeTrigger(job_result=job_result)
    agent_a = _FakeAgent(name="reviewer")
    agent_b = _FakeAgent(name="summarizer")
    pipeline = AgentPipeline(
        name="fraud-check",
        trigger=trigger,
        agents=[agent_a, agent_b],
        output_parser=_fake_output_parser([{"id": 1}]),
        events=events,
    )

    pipeline.run()

    assert starts == ["reviewer", "summarizer"]
    assert completes == ["reviewer", "summarizer"]


def test_on_error_fires_and_exception_still_propagates_when_trigger_fails() -> None:
    events = PipelineEvents()
    errors: list[Exception] = []
    events.on_error(lambda **kw: errors.append(kw["error"]))

    boom = RuntimeError("batch job failed")
    trigger = _FakeTrigger(error=boom)
    agent = _FakeAgent(name="reviewer")
    pipeline = AgentPipeline(
        name="fraud-check",
        trigger=trigger,
        agents=[agent],
        events=events,
    )

    with pytest.raises(RuntimeError):
        pipeline.run()

    assert errors == [boom]


def test_on_error_fires_and_exception_still_propagates_when_agent_fails() -> None:
    events = PipelineEvents()
    errors: list[Exception] = []
    events.on_error(lambda **kw: errors.append(kw["error"]))

    job_result = BatchJobResult(job_name="job-1", status="Completed", output_path="path")
    trigger = _FakeTrigger(job_result=job_result)
    boom = RuntimeError("agent call failed")
    agent = _FakeAgent(name="reviewer", error=boom)
    pipeline = AgentPipeline(
        name="fraud-check",
        trigger=trigger,
        agents=[agent],
        output_parser=_fake_output_parser([{"id": 1}]),
        events=events,
    )

    with pytest.raises(RuntimeError):
        pipeline.run()

    assert errors == [boom]


def test_pipeline_without_events_still_runs_normally() -> None:
    job_result = BatchJobResult(job_name="job-1", status="Completed", output_path="path")
    trigger = _FakeTrigger(job_result=job_result)
    agent = _FakeAgent(name="reviewer")
    pipeline = AgentPipeline(
        name="fraud-check",
        trigger=trigger,
        agents=[agent],
        output_parser=_fake_output_parser([{"id": 1}]),
    )

    result = pipeline.run()

    assert result.job is job_result
