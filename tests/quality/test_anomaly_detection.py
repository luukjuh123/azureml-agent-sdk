"""AnomalyDetectionAgent tests (P3-04)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from azureml_agent_sdk.agent import AgentResponse
from azureml_agent_sdk.quality.anomaly_detection import AnomalyDetectionAgent

ROWS = [{"v": 10.0, "n": "a"} for _ in range(20)] + [{"v": 1000.0, "n": "b"}]


def _aoai(content):
    agent = MagicMock()
    agent.run.return_value = AgentResponse(content=content)
    return agent


def test_aoai_response_used():
    payload = {"anomalies": [{"row_index": 20, "column": "v", "reason": "far above the rest"}]}
    aoai = _aoai(json.dumps(payload))
    report = AnomalyDetectionAgent(agent=aoai).check(ROWS)
    assert [(f.row_index, f.column, f.severity) for f in report.findings] == [(20, "v", "WARN")]
    assert "far above" in report.findings[0].message
    assert "1000" in aoai.run.call_args.args[0]


def test_aoai_fenced_json_and_bad_indices_ignored():
    payload = {"anomalies": [{"row_index": 99, "column": "v", "reason": "x"},
                             {"row_index": 3, "column": "v", "reason": "y"}]}
    report = AnomalyDetectionAgent(agent=_aoai("```json\n" + json.dumps(payload) + "\n```")).check(ROWS)
    assert [f.row_index for f in report.findings] == [3]


def test_zscore_fallback_when_aoai_raises():
    aoai = MagicMock()
    aoai.run.side_effect = RuntimeError("down")
    report = AnomalyDetectionAgent(agent=aoai).check(ROWS)
    assert [(f.row_index, f.column) for f in report.findings] == [(20, "v")]


def test_zscore_fallback_on_unparsable_reply():
    report = AnomalyDetectionAgent(agent=_aoai("not json")).check(ROWS)
    assert [f.row_index for f in report.findings] == [20]


def test_no_agent_uses_zscore_and_ignores_non_numeric():
    agent = AnomalyDetectionAgent()
    report = agent.check(ROWS)
    assert {f.column for f in report.findings} == {"v"}
    assert report.findings[0].severity == "WARN"


def test_empty_constant_and_single():
    agent = AnomalyDetectionAgent()
    assert agent.check([]).total_rows == 0
    assert agent.check([{"v": 1}]).aggregate.warn_count == 0
    assert agent.check([{"v": 5}] * 5).aggregate.warn_count == 0


def test_booleans_and_none_skipped():
    rows = [{"v": True}, {"v": None}, {"v": 1}]
    assert AnomalyDetectionAgent().check(rows).aggregate.warn_count == 0
