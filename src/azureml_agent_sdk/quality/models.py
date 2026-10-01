"""Structured quality report models (P3-07)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["INFO", "WARN", "ERROR"]


class Finding(BaseModel):
    """A single quality finding, optionally tied to a row and/or column."""

    row_index: int | None = None
    column: str | None = None
    severity: Severity
    message: str


class AggregateStats(BaseModel):
    """Counts per severity plus the fraction of rows with no WARN/ERROR finding."""

    info_count: int = 0
    warn_count: int = 0
    error_count: int = 0
    pass_rate: float = 1.0


class QualityReport(BaseModel):
    """The output of a DataQualityAgent run."""

    run_id: str
    agent_name: str
    total_rows: int
    findings: list[Finding] = Field(default_factory=list)
    aggregate: AggregateStats = Field(default_factory=AggregateStats)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def build(
        cls, run_id: str, agent_name: str, total_rows: int, findings: list[Finding]
    ) -> QualityReport:
        """Create a report, computing aggregate stats from ``findings``.

        ``pass_rate`` is the fraction of rows without a row-level WARN/ERROR
        finding; an empty batch has a pass rate of 1.0.
        """
        counts = {"INFO": 0, "WARN": 0, "ERROR": 0}
        failed_rows: set[int] = set()
        for f in findings:
            counts[f.severity] += 1
            if f.severity != "INFO" and f.row_index is not None:
                failed_rows.add(f.row_index)
        pass_rate = 1.0 if total_rows <= 0 else max(0.0, 1 - len(failed_rows) / total_rows)
        return cls(
            run_id=run_id,
            agent_name=agent_name,
            total_rows=total_rows,
            findings=findings,
            aggregate=AggregateStats(
                info_count=counts["INFO"],
                warn_count=counts["WARN"],
                error_count=counts["ERROR"],
                pass_rate=pass_rate,
            ),
        )
