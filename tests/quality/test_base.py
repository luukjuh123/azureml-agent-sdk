"""Tests for DataQualityAgent base + AgentPipeline integration (P3-01)."""
from __future__ import annotations

import pytest

from azureml_agent_sdk.batch_trigger import BatchJobResult
from azureml_agent_sdk.pipeline import AgentPipeline
from azureml_agent_sdk.quality.base import DataQualityAgent
from azureml_agent_sdk.quality.models import Finding, QualityReport


class _CountAgent(DataQualityAgent):
    def check(self, rows):
        return self.make_report(
            len(rows), [Finding(severity="INFO", message=f"{len(rows)} rows")]
        )


def test_base_is_abstract():
    with pytest.raises(TypeError):
        DataQualityAgent()  # type: ignore[abstract]


def test_check_returns_report_with_name_and_run_id():
    agent = _CountAgent(name="counter", run_id="run-1")
    report = agent.check([{"a": 1}])
    assert isinstance(report, QualityReport)
    assert (report.agent_name, report.run_id, report.total_rows) == ("counter", "run-1", 1)
    assert agent.config.name == "counter"


def test_default_name_is_class_name():
    assert _CountAgent().name == "_CountAgent"


class _Cfg:
    endpoint_name = "ep"


class _Trigger:
    config = _Cfg()

    def run(self):
        return BatchJobResult(job_name="job-9", status="Completed", output_path="/x.jsonl")


def test_pipeline_runs_quality_agent_as_step():
    agent = _CountAgent()
    pipe = AgentPipeline(
        "p", _Trigger(), [agent], output_parser=lambda path: [{"a": 1}, {"a": 2}]
    )
    result = pipe.run()
    assert len(result.quality_reports) == 1
    report = result.quality_reports[0]
    assert report.run_id == "job-9"
    assert report.total_rows == 2
    assert result.agent_runs == []
