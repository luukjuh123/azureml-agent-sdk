"""Tests for AgentPipeline: BatchEndpointTrigger -> AzureOpenAIAgent(s) (P1-05)."""

from __future__ import annotations

import pytest

from azureml_agent_sdk.agent import AgentResponse
from azureml_agent_sdk.batch_trigger import BatchJobResult
from azureml_agent_sdk.pipeline import AgentPipeline, AgentRunResult, PipelineResult


class _FakeConfig:
    def __init__(self, endpoint_name):
        self.endpoint_name = endpoint_name


class _FakeTrigger:
    def __init__(self, job_result):
        self._job_result = job_result
        self.config = _FakeConfig(endpoint_name="fraud-scoring")
        self.run_calls = 0

    def run(self):
        self.run_calls += 1
        return self._job_result


class _FakeAgentConfig:
    def __init__(self, name):
        self.name = name


class _FakeAgent:
    def __init__(self, name, reply_prefix):
        self.config = _FakeAgentConfig(name=name)
        self._reply_prefix = reply_prefix
        self.run_calls: list[str] = []

    def run(self, user_message, history=None):
        self.run_calls.append(user_message)
        return AgentResponse(content=f"{self._reply_prefix}: {user_message}", raw=None)


def _fake_output_parser(rows):
    def parser(_path):
        return rows

    return parser


class TestAgentPipelineRun:
    def test_runs_trigger_then_feeds_each_row_to_each_agent(self):
        job_result = BatchJobResult(
            job_name="job-1", status="Completed", output_path="azureml://jobs/job-1/outputs/score"
        )
        trigger = _FakeTrigger(job_result)
        rows = [{"id": 1}, {"id": 2}]
        agent_a = _FakeAgent(name="reviewer", reply_prefix="A")
        agent_b = _FakeAgent(name="summarizer", reply_prefix="B")

        pipeline = AgentPipeline(
            name="fraud-check",
            trigger=trigger,
            agents=[agent_a, agent_b],
            output_parser=_fake_output_parser(rows),
        )

        result = pipeline.run()

        assert trigger.run_calls == 1
        assert isinstance(result, PipelineResult)
        assert result.job is job_result
        assert result.rows == rows
        assert len(agent_a.run_calls) == 2
        assert len(agent_b.run_calls) == 2

    def test_result_contains_per_agent_responses_in_agent_order(self):
        job_result = BatchJobResult(job_name="job-1", status="Completed", output_path="path")
        trigger = _FakeTrigger(job_result)
        rows = [{"id": 1}]
        agent_a = _FakeAgent(name="reviewer", reply_prefix="A")
        agent_b = _FakeAgent(name="summarizer", reply_prefix="B")

        pipeline = AgentPipeline(
            name="fraud-check",
            trigger=trigger,
            agents=[agent_a, agent_b],
            output_parser=_fake_output_parser(rows),
        )

        result = pipeline.run()

        assert [run.agent_name for run in result.agent_runs] == ["reviewer", "summarizer"]
        assert isinstance(result.agent_runs[0], AgentRunResult)
        assert result.agent_runs[0].responses[0].content.startswith("A:")
        assert result.agent_runs[1].responses[0].content.startswith("B:")

    def test_requires_at_least_one_agent(self):
        job_result = BatchJobResult(job_name="job-1", status="Completed", output_path="path")
        trigger = _FakeTrigger(job_result)

        with pytest.raises(ValueError):
            AgentPipeline(name="fraud-check", trigger=trigger, agents=[])

    def test_agent_receives_row_json_as_user_message(self):
        job_result = BatchJobResult(job_name="job-1", status="Completed", output_path="path")
        trigger = _FakeTrigger(job_result)
        rows = [{"id": 1, "amount": 100}]
        agent = _FakeAgent(name="reviewer", reply_prefix="A")

        pipeline = AgentPipeline(
            name="fraud-check",
            trigger=trigger,
            agents=[agent],
            output_parser=_fake_output_parser(rows),
        )

        pipeline.run()

        assert '"id": 1' in agent.run_calls[0]
        assert '"amount": 100' in agent.run_calls[0]
