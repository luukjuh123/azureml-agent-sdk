"""SchemaValidationAgent: validate rows against a Pydantic v2 model (P3-03)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from azureml_agent_sdk.quality.base import DataQualityAgent
from azureml_agent_sdk.quality.models import Finding, QualityReport


class SchemaValidationAgent(DataQualityAgent):
    """Emits one ERROR finding per failing field per invalid row."""

    def __init__(self, schema: type[BaseModel], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.schema = schema

    def check(self, rows: list[dict[str, Any]]) -> QualityReport:
        findings: list[Finding] = []
        for i, row in enumerate(rows):
            try:
                self.schema.model_validate(row)
            except ValidationError as exc:
                for err in exc.errors():
                    loc = ".".join(str(p) for p in err["loc"]) or None
                    findings.append(
                        Finding(row_index=i, column=loc, severity="ERROR", message=err["msg"])
                    )
        if not findings:
            findings.append(Finding(severity="INFO", message="all rows match the schema"))
        return self.make_report(len(rows), findings)
