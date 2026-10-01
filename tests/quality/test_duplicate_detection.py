"""DuplicateDetectionAgent tests (P3-05)."""
from __future__ import annotations

import pytest

from azureml_agent_sdk.quality.duplicate_detection import DuplicateDetectionAgent


def test_exact_duplicates_found_key_order_insensitive():
    rows = [{"a": 1, "b": 2}, {"b": 2, "a": 1}, {"a": 9, "b": 9}, {"a": 1, "b": 2}]
    agent = DuplicateDetectionAgent()
    report = agent.check(rows)
    assert agent.find_groups(rows) == [[0, 1, 3]]
    flagged = {f.row_index for f in report.findings if f.severity == "WARN"}
    assert flagged == {1, 3}  # first occurrence is the original
    assert "group 0" in report.findings[0].message


def test_no_false_positives():
    rows = [{"a": 1}, {"a": 2}, {"a": 3}]
    report = DuplicateDetectionAgent().check(rows)
    assert report.aggregate.warn_count == 0 and report.aggregate.pass_rate == 1.0


def test_fuzzy_duplicates_above_threshold():
    rows = [
        {"name": "Acme Corporation Ltd", "city": "Berlin"},
        {"name": "Acme Corporation Limited", "city": "Berlin"},
        {"name": "Totally different", "city": "Paris"},
    ]
    agent = DuplicateDetectionAgent(fuzzy=True, threshold=0.8)
    assert agent.find_groups(rows) == [[0, 1]]
    assert DuplicateDetectionAgent(fuzzy=False).find_groups(rows) == []


def test_fuzzy_no_false_positive():
    rows = [{"name": "alpha beta"}, {"name": "gamma delta"}]
    assert DuplicateDetectionAgent(fuzzy=True, threshold=0.9).find_groups(rows) == []


def test_empty_single_and_bad_threshold():
    assert DuplicateDetectionAgent().check([]).total_rows == 0
    assert DuplicateDetectionAgent(fuzzy=True).find_groups([{"a": "x"}]) == []
    with pytest.raises(ValueError):
        DuplicateDetectionAgent(threshold=2)
