"""ReportSerializer tests (P3-08)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from azureml_agent_sdk.quality.models import Finding, QualityReport
from azureml_agent_sdk.quality.serializer import ReportSerializer

REPORT = QualityReport.build(
    "r1", "null_check", 4,
    [Finding(row_index=0, column="a", severity="ERROR", message="a | null"),
     Finding(severity="INFO", message="ok")],
)


def test_json_roundtrip(tmp_path):
    path = tmp_path / "sub" / "r.json"
    ReportSerializer.to_json(REPORT, path)
    text = path.read_text()
    assert "\n  " in text  # pretty-printed
    assert QualityReport.model_validate(json.loads(text)) == REPORT


def test_markdown_sections(tmp_path):
    path = tmp_path / "r.md"
    ReportSerializer.to_markdown(REPORT, path)
    md = path.read_text()
    assert "# Quality Report" in md and "null_check" in md and "r1" in md
    assert "Pass rate" in md and "75.0%" in md
    assert "| Row | Column | Severity | Message |" in md
    assert "| 0 | a | ERROR | a \\| null |" in md
    assert "| - | - | INFO | ok |" in md


def test_markdown_no_findings(tmp_path):
    path = tmp_path / "r.md"
    ReportSerializer.to_markdown(QualityReport.build("r", "a", 0, []), path)
    assert "No findings" in path.read_text()


def test_blob_upload_args():
    container = MagicMock()
    ReportSerializer.to_blob(REPORT, container, "reports/r1.json")
    container.upload_blob.assert_called_once()
    kwargs = container.upload_blob.call_args.kwargs
    assert kwargs["name"] == "reports/r1.json"
    assert kwargs["overwrite"] is True
    assert QualityReport.model_validate(json.loads(kwargs["data"])) == REPORT
