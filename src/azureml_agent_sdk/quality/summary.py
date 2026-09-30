"""SummaryAgent: AOAI-written natural-language summary of a batch run (P3-06)."""
from __future__ import annotations

import json
from typing import Any

from azureml_agent_sdk.quality.base import DataQualityAgent
from azureml_agent_sdk.quality.models import Finding, QualityReport

SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


class SummaryAgent(DataQualityAgent):
    """Summarises one or more :class:`QualityReport` objects with an AOAI agent."""

    def __init__(
        self,
        agent: Any,
        reports: list[QualityReport] | None = None,
        max_issues: int = 10,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.agent = agent
        self.reports = list(reports or [])
        self.max_issues = max_issues

    def _prompt(self, reports: list[QualityReport], total_rows: int) -> str:
        payload = {
            "total_rows": total_rows,
            "reports": [
                {
                    "agent_name": r.agent_name,
                    "total_rows": r.total_rows,
                    "aggregate": r.aggregate.model_dump(),
                    "top_issues": [
                        f.model_dump()
                        for f in sorted(r.findings, key=lambda f: SEVERITY_ORDER[f.severity])
                        if f.severity != "INFO"
                    ][: self.max_issues],
                }
                for r in reports
            ],
        }
        return (
            "Write a concise natural-language summary of this batch run (row count, finding "
            "counts, top issues):\n" + json.dumps(payload, default=str)
        )

    def summarize(self, report: QualityReport) -> str:
        """Return an AOAI-generated summary of ``report``."""
        return self.agent.run(self._prompt([report], report.total_rows)).content

    def check(self, rows: list[dict[str, Any]]) -> QualityReport:
        text = self.agent.run(self._prompt(self.reports, len(rows))).content
        return self.make_report(len(rows), [Finding(severity="INFO", message=text)])
