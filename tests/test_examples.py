"""Offline tests for the example pipelines (P5-01..P5-03): no network, no Azure credentials."""

from __future__ import annotations

import importlib.util
import socket
import sys
from pathlib import Path
from types import ModuleType

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"examples_{name}", EXAMPLES_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _blocked(*_a: object, **_k: object) -> None:
        raise AssertionError("example attempted network access")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    for var in ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"):
        monkeypatch.delenv(var, raising=False)


def test_fraud_check_reviews_only_flagged_rows(capsys: pytest.CaptureFixture[str]) -> None:
    module = _load("fraud_check_pipeline")
    reviews = module.main()
    assert [tid for tid, _ in reviews] == ["t-002", "t-004"]
    assert reviews[0][1].startswith("BLOCK")
    assert reviews[1][1].startswith("REVIEW")
    assert "t-002" in capsys.readouterr().out


def test_fraud_check_pipeline_runs_all_rows() -> None:
    module = _load("fraud_check_pipeline")
    result = module.build_pipeline().run()
    assert result.job.status == "Completed"
    assert len(result.rows) == len(result.agent_runs[0].responses) == 4


def test_content_moderation_routes_by_label() -> None:
    module = _load("content_moderation_pipeline")
    decisions = module.main()
    assert decisions == {
        "p-1": "KEEP p-1",
        "p-2": "REMOVE p-2",
        "p-3": "BAN_LINK p-3",
        "p-4": "KEEP p-4",
    }


def test_data_drift_report_summarises_features() -> None:
    module = _load("data_drift_pipeline")
    report = module.main()
    assert report.startswith("# Drift report (2/4 features drifted)")
    assert "- income: significant drift (PSI=0.31)" in report
    assert "- age: stable" in report


def test_data_drift_pipeline_includes_quality_report() -> None:
    module = _load("data_drift_pipeline")
    result = module.build_pipeline().run()
    assert len(result.quality_reports) == 1
    assert result.quality_reports[0].total_rows == 4
