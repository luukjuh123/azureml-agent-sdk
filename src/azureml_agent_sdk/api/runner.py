"""Background task runner: executes a pipeline and records its state (P4-02)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from azureml_agent_sdk.api.store import RunStore

PipelineRunner = Callable[[Path], Any]


def execute_run(store: RunStore, runner: PipelineRunner, run_id: str, pipeline_file: Path) -> None:
    """Run the pipeline, persisting running/succeeded/failed. Never raises."""
    store.update(run_id, status="running")
    try:
        result = runner(pipeline_file)
        store.update(
            run_id,
            status="succeeded",
            summary={
                "job_name": result.job.job_name,
                "job_status": result.job.status,
                "rows": len(result.rows),
                "agents": len(result.agent_runs),
            },
            reports=[r.model_dump(mode="json") for r in result.quality_reports],
        )
    except Exception as exc:  # noqa: BLE001 - failure is recorded, not propagated
        store.update(run_id, status="failed", error=f"{type(exc).__name__}: {exc}")
