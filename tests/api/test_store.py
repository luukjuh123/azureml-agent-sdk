from datetime import datetime, timezone

import pytest

from azureml_agent_sdk.api.store import (
    AzureTableRunStore,
    RunRecord,
    SqliteRunStore,
)


def _record(run_id="r1"):
    now = datetime.now(timezone.utc)
    return RunRecord(run_id=run_id, status="pending", pipeline_file="p.yaml",
                     created_at=now, updated_at=now)


def test_sqlite_roundtrip(tmp_path):
    store = SqliteRunStore(tmp_path / "runs.db")
    store.create(_record())
    got = store.get("r1")
    assert got.status == "pending" and got.pipeline_file == "p.yaml"
    store.update("r1", status="succeeded", summary={"rows": 3}, reports=[{"a": 1}])
    got = store.get("r1")
    assert got.status == "succeeded" and got.summary == {"rows": 3} and got.reports == [{"a": 1}]


def test_sqlite_missing_returns_none(tmp_path):
    assert SqliteRunStore(tmp_path / "runs.db").get("nope") is None


def test_sqlite_update_missing_raises(tmp_path):
    with pytest.raises(KeyError):
        SqliteRunStore(tmp_path / "runs.db").update("nope", status="failed")


class FakeTable:
    def __init__(self):
        self.rows = {}

    def create_entity(self, entity):
        self.rows[(entity["PartitionKey"], entity["RowKey"])] = dict(entity)

    def get_entity(self, partition_key, row_key):
        try:
            return dict(self.rows[(partition_key, row_key)])
        except KeyError:
            raise LookupError

    def update_entity(self, entity, mode="merge"):
        self.rows[(entity["PartitionKey"], entity["RowKey"])].update(entity)


def test_table_store_roundtrip():
    store = AzureTableRunStore(FakeTable())
    store.create(_record())
    store.update("r1", status="failed", error="boom")
    got = store.get("r1")
    assert got.status == "failed" and got.error == "boom"
    assert store.get("missing") is None
