"""Tests for QualityReport model (P3-07)."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from azureml_agent_sdk.quality.models import AggregateStats, Finding, QualityReport


def test_finding_defaults_and_severity_validation():
    f = Finding(severity="WARN", message="x")
    assert f.row_index is None and f.column is None
    with pytest.raises(ValidationError):
        Finding(severity="FATAL", message="x")


def test_report_creation_and_pass_rate():
    findings = [
        Finding(row_index=0, column="a", severity="ERROR", message="bad"),
        Finding(row_index=0, column="b", severity="WARN", message="meh"),
        Finding(row_index=1, severity="INFO", message="fine"),
        Finding(severity="WARN", message="dataset-level"),
    ]
    report = QualityReport.build(run_id="r1", agent_name="a", total_rows=4, findings=findings)
    assert report.aggregate == AggregateStats(
        info_count=1, warn_count=2, error_count=1, pass_rate=0.75
    )
    assert isinstance(report.generated_at, datetime)


def test_pass_rate_empty_is_one():
    assert QualityReport.build("r", "a", 0, []).aggregate.pass_rate == 1.0


def test_serialization_to_dict():
    report = QualityReport.build("r", "a", 1, [Finding(row_index=0, severity="ERROR", message="m")])
    data = report.model_dump(mode="json")
    assert data["run_id"] == "r"
    assert data["findings"][0]["severity"] == "ERROR"
    assert data["aggregate"]["pass_rate"] == 0.0
    assert QualityReport.model_validate(data) == report
