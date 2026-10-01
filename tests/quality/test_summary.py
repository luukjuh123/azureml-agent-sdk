"""SummaryAgent tests (P3-06)."""

from __future__ import annotations

from unittest.mock import MagicMock

from azureml_agent_sdk.agent import AgentResponse
from azureml_agent_sdk.quality.models import Finding, QualityReport
from azureml_agent_sdk.quality.summary import SummaryAgent

REPORT = QualityReport.build(
    "r1",
    "null_check",
    10,
    [
        Finding(row_index=1, column="a", severity="ERROR", message="a is null"),
        Finding(row_index=2, column="a", severity="WARN", message="a is null"),
    ],
)


def _aoai(text="All good."):
    m = MagicMock()
    m.run.return_value = AgentResponse(content=text)
    return m


def test_summarize_passes_stats_to_aoai_and_returns_text():
    aoai = _aoai("Two issues found.")
    text = SummaryAgent(aoai).summarize(REPORT)
    assert text == "Two issues found."
    prompt = aoai.run.call_args.args[0]
    for expected in ("10", "null_check", "a is null", "error_count", "warn_count"):
        assert expected in prompt


def test_check_emits_info_finding_with_summary():
    report = SummaryAgent(_aoai("Summary text"), reports=[REPORT]).check([{}] * 10)
    assert report.total_rows == 10
    assert [f.severity for f in report.findings] == ["INFO"]
    assert report.findings[0].message == "Summary text"


def test_check_without_reports_still_works():
    aoai = _aoai("empty")
    report = SummaryAgent(aoai).check([])
    assert report.findings[0].message == "empty"
    assert "0" in aoai.run.call_args.args[0]


def test_top_issues_limited():
    findings = [
        Finding(row_index=i, column=f"c{i}", severity="WARN", message=f"m{i}") for i in range(30)
    ]
    big = QualityReport.build("r", "x", 30, findings)
    aoai = _aoai()
    SummaryAgent(aoai, max_issues=5).summarize(big)
    assert "m4" in aoai.run.call_args.args[0] and "m20" not in aoai.run.call_args.args[0]
