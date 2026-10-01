"""Run store for pipeline run state: SQLite (dev) or Azure Table Storage (prod) (P4-03)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional, Protocol

from pydantic import BaseModel, Field

RunStatus = Literal["pending", "running", "succeeded", "failed"]
_FIELDS = {"status", "error", "summary", "reports"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RunRecord(BaseModel):
    run_id: str
    status: RunStatus = "pending"
    pipeline_file: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    error: Optional[str] = None
    summary: Optional[dict[str, Any]] = None
    reports: Optional[list[dict[str, Any]]] = None


class RunStore(Protocol):
    def create(self, record: RunRecord) -> None: ...
    def get(self, run_id: str) -> RunRecord | None: ...
    def update(self, run_id: str, **changes: Any) -> None: ...


def _check(changes: dict[str, Any]) -> None:
    unknown = set(changes) - _FIELDS
    if unknown:
        raise ValueError(f"cannot update fields: {sorted(unknown)}")


class SqliteRunStore:
    """SQLite-backed store. A connection is opened per call so it is thread-safe."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=30)

    def create(self, record: RunRecord) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO runs (run_id, data) VALUES (?, ?)",
                (record.run_id, record.model_dump_json()),
            )

    def get(self, run_id: str) -> RunRecord | None:
        with self._conn() as c:
            row = c.execute("SELECT data FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return RunRecord.model_validate_json(row[0]) if row else None

    def update(self, run_id: str, **changes: Any) -> None:
        _check(changes)
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT data FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(run_id)
            record = RunRecord.model_validate_json(row[0]).model_copy(
                update={**changes, "updated_at": _now()}
            )
            c.execute("UPDATE runs SET data = ? WHERE run_id = ?", (record.model_dump_json(), run_id))


class AzureTableRunStore:
    """Azure Table Storage store. ``table_client`` is an ``azure.data.tables.TableClient``."""

    _PK = "pipeline-runs"

    def __init__(self, table_client: Any) -> None:
        self._table = table_client

    def create(self, record: RunRecord) -> None:
        self._table.create_entity(
            {"PartitionKey": self._PK, "RowKey": record.run_id, "data": record.model_dump_json()}
        )

    def get(self, run_id: str) -> RunRecord | None:
        try:
            entity = self._table.get_entity(self._PK, run_id)
        except Exception as exc:  # noqa: BLE001 - ResourceNotFoundError or test stand-in
            if type(exc).__name__ in {"ResourceNotFoundError", "LookupError", "KeyError"}:
                return None
            raise
        return RunRecord.model_validate(json.loads(entity["data"]))

    def update(self, run_id: str, **changes: Any) -> None:
        _check(changes)
        record = self.get(run_id)
        if record is None:
            raise KeyError(run_id)
        record = record.model_copy(update={**changes, "updated_at": _now()})
        self._table.update_entity(
            {"PartitionKey": self._PK, "RowKey": run_id, "data": record.model_dump_json()},
            mode="merge",
        )
