"""NullCheckAgent: flag columns/rows with null or missing values (P3-02)."""
from __future__ import annotations

from typing import Any

from azureml_agent_sdk.quality.base import DataQualityAgent
from azureml_agent_sdk.quality.models import Finding, QualityReport

ERROR_RATE = 0.5


def _is_null(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


class NullCheckAgent(DataQualityAgent):
    """WARN when a column's null rate exceeds ``threshold``, ERROR above 0.5."""

    def __init__(self, threshold: float = 0.1, **kwargs: Any) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        super().__init__(**kwargs)
        self.threshold = threshold

    def check(self, rows: list[dict[str, Any]]) -> QualityReport:
        columns = list(dict.fromkeys(key for row in rows for key in row))
        findings: list[Finding] = []
        for column in columns:
            null_rows = [i for i, row in enumerate(rows) if _is_null(row.get(column))]
            rate = len(null_rows) / len(rows)
            if rate <= self.threshold or not null_rows:
                continue
            severity = "ERROR" if rate > ERROR_RATE else "WARN"
            findings.append(
                Finding(
                    column=column,
                    severity=severity,
                    message=f"column '{column}' null rate {rate:.1%} exceeds threshold",
                )
            )
            findings.extend(
                Finding(
                    row_index=i,
                    column=column,
                    severity=severity,
                    message=f"null or missing value in '{column}'",
                )
                for i in null_rows
            )
        if not findings:
            findings.append(Finding(severity="INFO", message="no null values above threshold"))
        return self.make_report(len(rows), findings)
