"""NullCheckAgent tests (P3-02)."""
from __future__ import annotations

import pytest

from azureml_agent_sdk.quality.null_check import NullCheckAgent


def _sev(report, column):
    return {f.severity for f in report.findings if f.column == column and f.row_index is None}


def test_clean_data_is_info():
    report = NullCheckAgent().check([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])
    assert {f.severity for f in report.findings} == {"INFO"}
    assert report.aggregate.pass_rate == 1.0


def test_partial_nulls_warn():
    rows = [{"a": None}, {"a": 1}, {"a": 2}, {"a": 3}]
    report = NullCheckAgent(threshold=0.1).check(rows)
    assert _sev(report, "a") == {"WARN"}
    assert any(f.row_index == 0 and f.column == "a" for f in report.findings)


def test_all_null_column_error():
    report = NullCheckAgent().check([{"a": None, "b": 1}, {"a": "", "b": 2}])
    assert _sev(report, "a") == {"ERROR"}
    assert _sev(report, "b") == set()


def test_missing_key_counts_as_null():
    report = NullCheckAgent().check([{"a": 1, "b": 2}, {"a": 1}])
    assert _sev(report, "b") == {"WARN"}
    assert any(f.row_index == 1 and f.column == "b" for f in report.findings)


def test_below_threshold_not_flagged():
    rows = [{"a": None}] + [{"a": i} for i in range(19)]
    report = NullCheckAgent(threshold=0.1).check(rows)
    assert _sev(report, "a") == set()


def test_empty_and_single_row():
    assert NullCheckAgent().check([]).total_rows == 0
    assert NullCheckAgent().check([{"a": None}]).aggregate.error_count >= 1


def test_invalid_threshold():
    with pytest.raises(ValueError):
        NullCheckAgent(threshold=1.5)
