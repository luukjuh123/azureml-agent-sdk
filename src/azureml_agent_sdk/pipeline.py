"""Chains a BatchEndpointTrigger into one or more AzureOpenAIAgents, run sequentially (P1-05).

Batch output rows are parsed and fed into each agent's context window in turn
(P1-06), with structured JSON logging emitted at each step (P1-08).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from azureml_agent_sdk.agent import AgentResponse
from azureml_agent_sdk.batch_trigger import BatchJobResult
from azureml_agent_sdk.events import PipelineEvents
from azureml_agent_sdk.logging_utils import get_pipeline_logger, log_step
from azureml_agent_sdk.quality.base import DataQualityAgent
from azureml_agent_sdk.quality.models import QualityReport
from azureml_agent_sdk.results import parse_batch_output, rows_to_messages


class _Trigger(Protocol):
    config: Any

    def run(self) -> BatchJobResult: ...


class _Agent(Protocol):
    config: Any

    def run(
        self, user_message: str, history: list[dict[str, str]] | None = None
    ) -> AgentResponse: ...


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
    quality_reports: list[QualityReport] = field(default_factory=list)


class AgentPipeline:
    """Runs a batch endpoint trigger, then feeds each parsed output row to each
    agent in turn, in the order the agents were given."""

    def __init__(
        self,
        name: str,
        trigger: _Trigger,
        agents: Sequence[_Agent | DataQualityAgent],
        output_parser: Any = parse_batch_output,
        events: PipelineEvents | None = None,
    ) -> None:
        if not agents:
            raise ValueError("AgentPipeline requires at least one agent")
        self.name = name
        self.trigger = trigger
        self.agents = agents
        self._output_parser = output_parser
        self._logger = get_pipeline_logger()
        self.events = events or PipelineEvents()

    def run(self) -> PipelineResult:
        """Execute the batch trigger, then run every agent over every parsed row."""
        log_step(
            self._logger,
            "batch.start",
            pipeline=self.name,
            endpoint=self.trigger.config.endpoint_name,
        )
        self.events.emit_sync(
            "batch_start", pipeline=self.name, endpoint=self.trigger.config.endpoint_name
        )
        try:
            job = self.trigger.run()
        except Exception as exc:
            self.events.emit_sync("error", pipeline=self.name, stage="batch", error=exc)
            raise
        log_step(
            self._logger,
            "batch.complete",
            pipeline=self.name,
            job_name=job.job_name,
            status=job.status,
        )
        self.events.emit_sync(
            "batch_complete", pipeline=self.name, job_name=job.job_name, status=job.status
        )

        rows = self._output_parser(job.output_path)
        messages = rows_to_messages(rows)

        agent_runs: list[AgentRunResult] = []
        quality_reports: list[QualityReport] = []
        for agent in self.agents:
            if isinstance(agent, DataQualityAgent):
                quality_reports.append(self._run_quality_agent(agent, job, rows))
                continue
            log_step(self._logger, "agent.start", pipeline=self.name, agent=agent.config.name)
            self.events.emit_sync("agent_start", pipeline=self.name, agent=agent.config.name)
            try:
                responses = [agent.run(message["content"]) for message in messages]
            except Exception as exc:
                self.events.emit_sync(
                    "error", pipeline=self.name, stage="agent", agent=agent.config.name, error=exc
                )
                raise
            log_step(
                self._logger,
                "agent.complete",
                pipeline=self.name,
                agent=agent.config.name,
                rows_processed=len(responses),
            )
            self.events.emit_sync(
                "agent_complete",
                pipeline=self.name,
                agent=agent.config.name,
                rows_processed=len(responses),
            )
            agent_runs.append(AgentRunResult(agent_name=agent.config.name, responses=responses))

        return PipelineResult(
            job=job, rows=rows, agent_runs=agent_runs, quality_reports=quality_reports
        )

    def _run_quality_agent(
        self, agent: DataQualityAgent, job: BatchJobResult, rows: list[dict[str, Any]]
    ) -> QualityReport:
        """Run a DataQualityAgent once over all rows; the report is tagged with the job name."""
        log_step(self._logger, "agent.start", pipeline=self.name, agent=agent.name)
        self.events.emit_sync("agent_start", pipeline=self.name, agent=agent.name)
        try:
            report = agent.check(rows)
        except Exception as exc:
            self.events.emit_sync(
                "error", pipeline=self.name, stage="agent", agent=agent.name, error=exc
            )
            raise
        report = report.model_copy(update={"run_id": job.job_name})
        log_step(
            self._logger,
            "agent.complete",
            pipeline=self.name,
            agent=agent.name,
            rows_processed=len(rows),
        )
        self.events.emit_sync(
            "agent_complete", pipeline=self.name, agent=agent.name, rows_processed=len(rows)
        )
        return report
