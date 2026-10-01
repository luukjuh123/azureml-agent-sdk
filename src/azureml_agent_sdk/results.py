"""Parse Azure ML batch endpoint output (JSONL/CSV) and turn rows into agent
messages (P1-06)."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any


class UnsupportedBatchOutputFormatError(ValueError):
    """Raised when a batch output file's format cannot be determined or is unsupported."""


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    """Parse newline-delimited JSON into a list of row dicts, skipping blank lines."""
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        rows.append(json.loads(stripped))
    return rows


def parse_csv(text: str) -> list[dict[str, Any]]:
    """Parse CSV text into a list of row dicts, keyed by header."""
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def parse_batch_output(path: str | Path) -> list[dict[str, Any]]:
    """Parse a batch output file into row dicts, inferring format from the suffix."""
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    text = file_path.read_text(encoding="utf-8")
    if suffix in {".jsonl", ".json"}:
        return parse_jsonl(text)
    if suffix == ".csv":
        return parse_csv(text)
    raise UnsupportedBatchOutputFormatError(f"unsupported batch output format: {suffix!r}")


def rows_to_messages(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Turn parsed batch output rows into user messages for an agent context window."""
    return [{"role": "user", "content": json.dumps(row, sort_keys=True)} for row in rows]
