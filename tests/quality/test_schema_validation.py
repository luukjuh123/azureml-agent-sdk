"""SchemaValidationAgent tests (P3-03)."""

from __future__ import annotations

from pydantic import BaseModel

from azureml_agent_sdk.quality.schema_validation import SchemaValidationAgent


class Txn(BaseModel):
    id: int
    amount: float
    currency: str


def test_valid_rows_pass():
    rows = [{"id": 1, "amount": 2.5, "currency": "EUR"}]
    report = SchemaValidationAgent(Txn).check(rows)
    assert report.aggregate.error_count == 0
    assert report.aggregate.pass_rate == 1.0


def test_invalid_rows_flag_field_names():
    rows = [{"id": "abc", "amount": 1.0, "currency": "EUR"}, {"id": 2, "amount": 1.0}]
    report = SchemaValidationAgent(Txn).check(rows)
    errs = {(f.row_index, f.column) for f in report.findings if f.severity == "ERROR"}
    assert errs == {(0, "id"), (1, "currency")}
    assert all(f.message for f in report.findings)


def test_partial_failure_pass_rate():
    rows = [{"id": 1, "amount": 1, "currency": "x"}, {"id": None, "amount": 1, "currency": "x"}]
    report = SchemaValidationAgent(Txn).check(rows)
    assert report.aggregate.pass_rate == 0.5


def test_all_invalid_and_empty():
    report = SchemaValidationAgent(Txn).check([{}, {}])
    assert report.aggregate.pass_rate == 0.0
    assert SchemaValidationAgent(Txn).check([]).total_rows == 0
