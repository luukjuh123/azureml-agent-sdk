"""Submit an Azure ML batch endpoint job, poll it to completion, and resolve its
output blob path (P1-03).

Polling is driven through injectable ``sleep``/``clock`` callables so tests run
instantly and deterministically, with no real waiting and no real Azure calls.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from azureml_agent_sdk.aml_client import AzureMLClientWrapper
from azureml_agent_sdk.config import BatchEndpointConfig

_SUCCESS_STATES = {"Completed"}
_FAILURE_STATES = {"Failed", "Canceled"}
_TERMINAL_STATES = _SUCCESS_STATES | _FAILURE_STATES


class BatchJobFailedError(RuntimeError):
    """Raised when a batch endpoint job ends in a failed/canceled state."""


class BatchJobTimeoutError(RuntimeError):
    """Raised when a batch endpoint job does not reach a terminal state before timeout."""


@dataclass
class BatchJobResult:
    """The outcome of a completed batch endpoint job."""

    job_name: str
    status: str
    output_path: str


class BatchEndpointTrigger:
    """Submits a batch endpoint job and polls it through to completion."""

    def __init__(
        self,
        config: BatchEndpointConfig,
        aml_client: AzureMLClientWrapper,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self._aml_client = aml_client
        self._sleep = sleep
        self._clock = clock

    def submit(self) -> str:
        """Invoke the batch endpoint and return the submitted job's name."""
        from azure.ai.ml import Input

        job = self._aml_client.client.batch_endpoints.invoke(
            endpoint_name=self.config.endpoint_name,
            deployment_name=self.config.deployment_name,
            input=Input(type="uri_folder", path=self.config.input_data_path),
        )
        return job.name

    def get_status(self, job_name: str) -> str:
        """Return the current status of the job."""
        job = self._aml_client.client.jobs.get(job_name)
        return job.status

    def get_output_path(self, job_name: str) -> str:
        """Resolve the output blob path for a completed job."""
        job = self._aml_client.client.jobs.get(job_name)
        outputs = getattr(job, "outputs", None) or {}
        output = outputs.get("score") or outputs.get("default")
        if output is not None:
            return getattr(output, "path", str(output))
        return f"azureml://jobs/{job_name}/outputs/score"

    def run(self) -> BatchJobResult:
        """Submit the job, poll until terminal, and return its result."""
        job_name = self.submit()
        start = self._clock()
        status = self.get_status(job_name)
        while status not in _TERMINAL_STATES:
            if self._clock() - start > self.config.timeout_seconds:
                raise BatchJobTimeoutError(
                    f"batch job {job_name!r} did not reach a terminal state within "
                    f"{self.config.timeout_seconds}s"
                )
            self._sleep(self.config.poll_interval_seconds)
            status = self.get_status(job_name)
        if status in _FAILURE_STATES:
            raise BatchJobFailedError(f"batch job {job_name!r} ended with status {status!r}")
        return BatchJobResult(
            job_name=job_name, status=status, output_path=self.get_output_path(job_name)
        )
