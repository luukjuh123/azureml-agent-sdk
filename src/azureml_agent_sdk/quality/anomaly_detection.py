"""AnomalyDetectionAgent: flag numeric outliers via AOAI, z-score fallback (P3-04)."""
from __future__ import annotations

import json
import logging
import re
import statistics
from typing import Any

from azureml_agent_sdk.quality.base import DataQualityAgent
from azureml_agent_sdk.quality.models import Finding, QualityReport

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a data quality analyst. Identify statistical outliers in the numeric columns of "
    'the given rows. Reply with JSON only: {"anomalies": [{"row_index": <int>, '
    '"column": "<name>", "reason": "<short reason>"}]}. Use an empty list if there are none.'
)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_reply(content: str) -> list[dict[str, Any]]:
    match = re.search(r"\{.*\}", content or "", re.DOTALL)
    data = json.loads(match.group(0) if match else content)
    anomalies = data["anomalies"]
    if not isinstance(anomalies, list):
        raise ValueError("anomalies must be a list")
    return anomalies


class AnomalyDetectionAgent(DataQualityAgent):
    """Uses an ``AzureOpenAIAgent`` (if given) to flag outliers; on any failure or
    unparsable reply, falls back to a z-score test (``|z| > z_threshold``)."""

    def __init__(
        self, agent: Any | None = None, z_threshold: float = 3.0, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.agent = agent
        self.z_threshold = z_threshold

    def check(self, rows: list[dict[str, Any]]) -> QualityReport:
        findings: list[Finding] | None = None
        if rows and self.agent is not None:
            findings = self._check_with_aoai(rows)
        if findings is None:
            findings = self._check_zscore(rows)
        if not findings:
            findings = [Finding(severity="INFO", message="no anomalies detected")]
        return self.make_report(len(rows), findings)

    def _check_with_aoai(self, rows: list[dict[str, Any]]) -> list[Finding] | None:
        prompt = json.dumps({"rows": dict(enumerate(rows))}, default=str)
        try:
            anomalies = _parse_reply(self.agent.run(prompt).content)
            findings = []
            for a in anomalies:
                idx = a.get("row_index")
                if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < len(rows):
                    continue
                findings.append(
                    Finding(
                        row_index=idx,
                        column=a.get("column"),
                        severity="WARN",
                        message=str(a.get("reason") or "flagged as outlier by AOAI"),
                    )
                )
            return findings
        except Exception as exc:  # AOAI unavailable or bad reply -> statistical fallback
            logger.warning("AOAI anomaly detection failed (%s); using z-score", type(exc).__name__)
            return None

    def _check_zscore(self, rows: list[dict[str, Any]]) -> list[Finding]:
        findings: list[Finding] = []
        columns = list(dict.fromkeys(k for row in rows for k in row))
        for column in columns:
            points = [(i, r[column]) for i, r in enumerate(rows) if _is_number(r.get(column))]
            if len(points) < 2:
                continue
            values = [v for _, v in points]
            mean = statistics.fmean(values)
            std = statistics.pstdev(values)
            if std == 0:
                continue
            for i, v in points:
                z = (v - mean) / std
                if abs(z) > self.z_threshold:
                    findings.append(
                        Finding(
                            row_index=i,
                            column=column,
                            severity="WARN",
                            message=f"value {v} has z-score {z:.2f} (threshold {self.z_threshold})",
                        )
                    )
        return findings
