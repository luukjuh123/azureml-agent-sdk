"""Tests for BatchEndpointTrigger: submit, poll, resolve output path (P1-03)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from azureml_agent_sdk.aml_client import AzureMLClientWrapper
from azureml_agent_sdk.batch_trigger import (
    BatchEndpointTrigger,
    BatchJobFailedError,
    BatchJobResult,
    BatchJobTimeoutError,
)
from azureml_agent_sdk.config import BatchEndpointConfig


@dataclass
class _FakeJob:
    name: str


@dataclass
class _FakeOutput:
    path: str


@dataclass
class _FakeJobDetails:
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)


class _FakeBatchEndpointsOperations:
    def __init__(self, job_name="job-123"):
        self.job_name = job_name
        self.invoke_calls: list[dict[str, Any]] = []

    def invoke(self, **kwargs):
        self.invoke_calls.append(kwargs)
        return _FakeJob(name=self.job_name)


class _FakeJobsOperations:
    def __init__(self, status_sequence, output_path="azureml://jobs/job-123/outputs/score"):
        self._status_sequence = list(status_sequence)
        self._output_path = output_path
        self.get_calls = 0

    def get(self, name):
        self.get_calls += 1
        status = self._status_sequence[min(self.get_calls - 1, len(self._status_sequence) - 1)]
        outputs = {"score": _FakeOutput(path=self._output_path)} if status == "Completed" else {}
        return _FakeJobDetails(status=status, outputs=outputs)


class _FakeMLClient:
    def __init__(self, status_sequence, job_name="job-123", output_path="azureml://jobs/job-123/outputs/score"):
        self.batch_endpoints = _FakeBatchEndpointsOperations(job_name=job_name)
        self.jobs = _FakeJobsOperations(status_sequence, output_path=output_path)


def _make_trigger(status_sequence, sleep_calls=None, poll_interval=1.0, timeout=60.0, clock=None):
    fake_client = _FakeMLClient(status_sequence)
    aml_client = AzureMLClientWrapper(
        subscription_id="sub",
        resource_group="rg",
        workspace_name="ws",
        ml_client_factory=lambda: fake_client,
    )
    config = BatchEndpointConfig(
        endpoint_name="fraud-scoring",
        input_data_path="azureml://datastores/blob/paths/input",
        poll_interval_seconds=poll_interval,
        timeout_seconds=timeout,
    )
    sleep_calls = sleep_calls if sleep_calls is not None else []
    trigger = BatchEndpointTrigger(
        config=config,
        aml_client=aml_client,
        sleep=lambda seconds: sleep_calls.append(seconds),
        clock=clock or (lambda: 0.0),
    )
    return trigger, fake_client


class TestSubmit:
    def test_submit_invokes_batch_endpoint_and_returns_job_name(self):
        trigger, fake_client = _make_trigger(["Completed"])
        job_name = trigger.submit()

        assert job_name == "job-123"
        assert fake_client.batch_endpoints.invoke_calls[0]["endpoint_name"] == "fraud-scoring"


class TestPolling:
    def test_run_polls_until_completed_and_returns_result(self):
        sleep_calls = []
        trigger, fake_client = _make_trigger(
            ["Running", "Running", "Completed"], sleep_calls=sleep_calls
        )

        result = trigger.run()

        assert isinstance(result, BatchJobResult)
        assert result.job_name == "job-123"
        assert result.status == "Completed"
        assert result.output_path == "azureml://jobs/job-123/outputs/score"
        assert len(sleep_calls) == 2  # polled twice before terminal state

    def test_run_raises_on_failed_job(self):
        trigger, _ = _make_trigger(["Running", "Failed"])

        with pytest.raises(BatchJobFailedError):
            trigger.run()

    def test_run_raises_timeout_when_never_reaches_terminal_state(self):
        clock_values = iter([0.0, 0.0, 100.0])
        trigger, _ = _make_trigger(
            ["Running", "Running", "Running"],
            poll_interval=1.0,
            timeout=10.0,
            clock=lambda: next(clock_values),
        )

        with pytest.raises(BatchJobTimeoutError):
            trigger.run()


class TestGetStatusAndOutputPath:
    def test_get_status_returns_current_status(self):
        trigger, _ = _make_trigger(["Running"])
        assert trigger.get_status("job-123") == "Running"

    def test_get_output_path_resolves_from_job_outputs(self):
        trigger, _ = _make_trigger(["Completed"])
        assert trigger.get_output_path("job-123") == "azureml://jobs/job-123/outputs/score"
