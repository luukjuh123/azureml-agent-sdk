"""Write QualityReports to JSON, Markdown, and Azure Blob Storage (P3-08)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from azureml_agent_sdk.quality.models import QualityReport


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


class ReportSerializer:
    @staticmethod
    def to_json_str(report: QualityReport) -> str:
        return report.model_dump_json(indent=2)

    @staticmethod
    def to_json(report: QualityReport, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(ReportSerializer.to_json_str(report), encoding="utf-8")
        return out

    @staticmethod
    def to_markdown(report: QualityReport, path: str | Path) -> Path:
        agg = report.aggregate
        lines = [
            f"# Quality Report: {report.agent_name}",
            "",
            f"- **Run ID:** {report.run_id}",
            f"- **Generated at:** {report.generated_at.isoformat()}",
            f"- **Total rows:** {report.total_rows}",
            f"- **Pass rate:** {agg.pass_rate:.1%}",
            f"- **Findings:** {agg.error_count} error, {agg.warn_count} warn, {agg.info_count} info",
            "",
            "## Findings",
            "",
        ]
        if report.findings:
            lines += ["| Row | Column | Severity | Message |", "| --- | --- | --- | --- |"]
            for f in report.findings:
                row = "-" if f.row_index is None else f.row_index
                col = "-" if f.column is None else _cell(f.column)
                lines.append(f"| {row} | {col} | {f.severity} | {_cell(f.message)} |")
        else:
            lines.append("No findings.")
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return out

    @staticmethod
    def to_blob(report: QualityReport, container_client: Any, blob_name: str) -> None:
        """Upload the JSON report via an ``azure.storage.blob.ContainerClient``."""
        container_client.upload_blob(
            name=blob_name, data=ReportSerializer.to_json_str(report), overwrite=True
        )
