"""FastAPI app: trigger and monitor pipelines over HTTP (P4-01, P4-05)."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from azureml_agent_sdk.api.auth import make_auth_dependency
from azureml_agent_sdk.api.runner import PipelineRunner, execute_run
from azureml_agent_sdk.api.store import RunRecord, RunStore, SqliteRunStore


class RunRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"pipeline_file": "fraud-check.yaml"}]}
    )
    pipeline_file: str


class RunAccepted(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"run_id": "3f2b...", "status": "pending"}]}
    )
    run_id: str
    status: str


class ReportResponse(BaseModel):
    run_id: str
    reports: list[dict[str, Any]]


def _default_runner(path: Path) -> Any:
    from azureml_agent_sdk.cli import run_pipeline_from_yaml

    return run_pipeline_from_yaml(path)


def create_app(
    store: RunStore | None = None,
    pipeline_runner: PipelineRunner | None = None,
    api_token: str | None = None,
    pipelines_dir: str | Path | None = None,
) -> FastAPI:
    """Build the app. Defaults: SQLite at ``$AZUREML_AGENT_DB`` (runs.db), pipelines
    resolved inside ``$AZUREML_AGENT_PIPELINES_DIR`` (cwd), token from env."""
    store = store or SqliteRunStore(os.environ.get("AZUREML_AGENT_DB", "runs.db"))
    runner = pipeline_runner or _default_runner
    base = Path(pipelines_dir or os.environ.get("AZUREML_AGENT_PIPELINES_DIR", ".")).resolve()
    auth = Depends(make_auth_dependency(api_token))

    app = FastAPI(
        title="azureml-agent-sdk REST harness",
        description="Trigger and monitor AgentPipeline runs. Requires a Bearer token.",
    )

    def _get(run_id: str) -> RunRecord:
        record = store.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="run not found")
        return record

    @app.post("/pipelines/run", status_code=202, response_model=RunAccepted, dependencies=[auth])
    def run_pipeline(body: RunRequest, background: BackgroundTasks) -> RunAccepted:
        path = (base / body.pipeline_file).resolve()
        if not path.is_relative_to(base):
            raise HTTPException(status_code=400, detail="pipeline_file escapes pipelines directory")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="pipeline file not found")
        run_id = uuid.uuid4().hex
        store.create(RunRecord(run_id=run_id, pipeline_file=body.pipeline_file))
        background.add_task(execute_run, store, runner, run_id, path)
        return RunAccepted(run_id=run_id, status="pending")

    @app.get("/pipelines/{run_id}/status", response_model=RunRecord,
             response_model_exclude={"reports"}, dependencies=[auth])
    def run_status(run_id: str) -> RunRecord:
        return _get(run_id)

    @app.get("/pipelines/{run_id}/report", response_model=ReportResponse, dependencies=[auth])
    def run_report(run_id: str) -> ReportResponse:
        record = _get(run_id)
        if record.status != "succeeded":
            raise HTTPException(status_code=409, detail=f"run is {record.status}; no report")
        return ReportResponse(run_id=run_id, reports=record.reports or [])

    return app


def app_factory() -> FastAPI:
    """Uvicorn factory: ``uvicorn azureml_agent_sdk.api.app:app_factory --factory``."""
    return create_app()
