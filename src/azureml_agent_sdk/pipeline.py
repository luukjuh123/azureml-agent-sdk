"""Chains a BatchEndpointTrigger into one or more AzureOpenAIAgents, run sequentially (P1-05).

Batch output rows are parsed and fed into each agent's context window in turn
(P1-06), with structured JSON logging emitted at each step (P1-08).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from azureml_agent_sdk.agent import AgentResponse
from azureml_agent_sdk.batch_trigger import BatchJobResult
from azureml_agent_sdk.logging_utils import get_pipeline_logger, log_step
from azureml_agent_sdk.results import parse_batch_output, rows_to_messages


class _Trigger(Protocol):
    def run(self) -> BatchJobResult: ...


class _Agent(Protocol):
    config: Any

    def run(self, user_message: str, history: list[dict[str, str]] | None = None) -> AgentResponse: ...


@dataclass
class AgentRunResult:
    """All responses produced by a single agent across the batch output rows."""

    agent_name: str
    responses: list[AgentResponse]


@dataclass
class PipelineResult:
    """The full outcome of an AgentPipeline run."""

    job: BatchJobResult
    rows: list[dict[str, Any]]
    agent_runs: list[AgentRunResult]


class AgentPipeline:
    """Runs a batch endpoint trigger, then feeds each parsed output row to each
    agent in turn, in the order the agents were given."""

    def __init__(
        self,
        name: str,
        trigger: _Trigger,
        agents: list[_Agent],
        output_parser: Any = parse_batch_output,
    ) -> None:
        if not agents:
            raise ValueError("AgentPipeline requires at least one agent")
        self.name = name
        self.trigger = trigger
        self.agents = agents
        self._output_parser = output_parser
        self._logger = get_pipeline_logger()

    def run(self) -> PipelineResult:
        """Execute the batch trigger, then run every agent over every parsed row."""
        log_step(
            self._logger,
            "batch.start",
            pipeline=self.name,
            endpoint=self.trigger.config.endpoint_name,
        )
        job = self.trigger.run()
        log_step(
            self._logger,
            "batch.complete",
            pipeline=self.name,
            job_name=job.job_name,
            status=job.status,
        )

        rows = self._output_parser(job.output_path)
        messages = rows_to_messages(rows)

        agent_runs: list[AgentRunResult] = []
        for agent in self.agents:
            log_step(self._logger, "agent.start", pipeline=self.name, agent=agent.config.name)
            responses = [agent.run(message["content"]) for message in messages]
            log_step(
                self._logger,
                "agent.complete",
                pipeline=self.name,
                agent=agent.config.name,
                rows_processed=len(responses),
            )
            agent_runs.append(AgentRunResult(agent_name=agent.config.name, responses=responses))

        return PipelineResult(job=job, rows=rows, agent_runs=agent_runs)
