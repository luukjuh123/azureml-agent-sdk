"""DuplicateDetectionAgent: exact (SHA-256) and fuzzy duplicate rows (P3-05)."""
from __future__ import annotations

import hashlib
import json
from difflib import SequenceMatcher
from typing import Any

from azureml_agent_sdk.quality.base import DataQualityAgent
from azureml_agent_sdk.quality.models import Finding, QualityReport


def row_hash(row: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()


def token_set_ratio(a: str, b: str) -> float:
    """Token-set similarity in [0, 1] (same idea as rapidfuzz's token_set_ratio)."""
    ta, tb = set(a.lower().split()), set(b.lower().split())
    if not ta or not tb:
        return 0.0
    common = " ".join(sorted(ta & tb))
    a_rest = " ".join(sorted(ta - tb))
    b_rest = " ".join(sorted(tb - ta))
    s_common = common
    s_a = f"{common} {a_rest}".strip()
    s_b = f"{common} {b_rest}".strip()
    pairs = [(s_a, s_b)]
    if common:
        pairs += [(s_common, s_a), (s_common, s_b)]
    return max(SequenceMatcher(None, x, y).ratio() for x, y in pairs)


def _text(row: dict[str, Any]) -> str:
    return " ".join(v for v in row.values() if isinstance(v, str))


class DuplicateDetectionAgent(DataQualityAgent):
    """Groups duplicate rows; every row after the first in a group is flagged WARN."""

    def __init__(self, fuzzy: bool = False, threshold: float = 0.9, **kwargs: Any) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        super().__init__(**kwargs)
        self.fuzzy = fuzzy
        self.threshold = threshold

    def find_groups(self, rows: list[dict[str, Any]]) -> list[list[int]]:
        """Return groups (lists of row indices, ascending) with more than one row."""
        parent = list(range(len(rows)))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[max(rx, ry)] = min(rx, ry)

        seen: dict[str, int] = {}
        for i, row in enumerate(rows):
            union(i, seen.setdefault(row_hash(row), i))

        if self.fuzzy:
            texts = [_text(r) for r in rows]
            for i in range(len(rows)):
                if not texts[i]:
                    continue
                for j in range(i + 1, len(rows)):
                    if find(i) != find(j) and texts[j] and (
                        token_set_ratio(texts[i], texts[j]) >= self.threshold
                    ):
                        union(i, j)

        groups: dict[int, list[int]] = {}
        for i in range(len(rows)):
            groups.setdefault(find(i), []).append(i)
        return sorted((g for g in groups.values() if len(g) > 1), key=lambda g: g[0])

    def check(self, rows: list[dict[str, Any]]) -> QualityReport:
        findings: list[Finding] = []
        for group_id, group in enumerate(self.find_groups(rows)):
            findings.extend(
                Finding(
                    row_index=i,
                    severity="WARN",
                    message=f"duplicate of row {group[0]} (group {group_id}, rows {group})",
                )
                for i in group[1:]
            )
        if not findings:
            findings.append(Finding(severity="INFO", message="no duplicate rows found"))
        return self.make_report(len(rows), findings)
