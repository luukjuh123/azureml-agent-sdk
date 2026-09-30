"""Abstract base class for post-batch data quality agents (P3-01)."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import Any

from azureml_agent_sdk.quality.models import Finding, QualityReport


class DataQualityAgent(ABC):
    """Receives batch output rows and emits a structured :class:`QualityReport`.

    Instances can be passed to ``AgentPipeline`` as steps: the pipeline calls
    ``check`` once with all parsed rows and collects the report.
    """

    def __init__(self, name: str | None = None, run_id: str | None = None) -> None:
        self.name = name or type(self).__name__
        self.run_id = run_id or uuid.uuid4().hex
        # Mirrors AzureOpenAIAgent.config so pipeline logging can name the step.
        self.config = SimpleNamespace(name=self.name)

    @abstractmethod
    def check(self, rows: list[dict[str, Any]]) -> QualityReport:
        """Inspect ``rows`` and return a report."""

    def make_report(self, total_rows: int, findings: list[Finding]) -> QualityReport:
        return QualityReport.build(self.run_id, self.name, total_rows, findings)
