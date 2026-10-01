import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from azureml_agent_sdk.api.app import create_app
from azureml_agent_sdk.api.store import SqliteRunStore
from azureml_agent_sdk.quality.models import Finding, QualityReport

TOKEN = "s3cret"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _result():
    report = QualityReport.build(
        "j", "null", 2, [Finding(severity="WARN", message="x", row_index=0)]
    )
    return SimpleNamespace(
        job=SimpleNamespace(job_name="job-1", status="Completed"),
        rows=[{}, {}],
        agent_runs=[],
        quality_reports=[report],
    )


@pytest.fixture
def make(tmp_path):
    (tmp_path / "p.yaml").write_text("x: 1")

    def _make(runner=None, token=TOKEN):
        app = create_app(
            store=SqliteRunStore(tmp_path / "r.db"),
            pipeline_runner=runner or (lambda path: _result()),
            api_token=token,
            pipelines_dir=tmp_path,
        )
        return TestClient(app)

    return _make


def _wait(client, run_id, want):
    for _ in range(50):
        body = client.get(f"/pipelines/{run_id}/status", headers=AUTH).json()
        if body["status"] in want:
            return body
        time.sleep(0.02)
    raise AssertionError(body)


def test_run_status_report_happy_path(make):
    c = make()
    r = c.post("/pipelines/run", json={"pipeline_file": "p.yaml"}, headers=AUTH)
    assert r.status_code == 202
    run_id = r.json()["run_id"]
    body = _wait(c, run_id, {"succeeded", "failed"})
    assert body["status"] == "succeeded" and body["summary"]["rows"] == 2
    rep = c.get(f"/pipelines/{run_id}/report", headers=AUTH)
    assert rep.status_code == 200
    assert rep.json()["reports"][0]["aggregate"]["warn_count"] == 1


def test_failed_run_records_error(make):
    def boom(path):
        raise RuntimeError("kaput")

    c = make(boom)
    run_id = c.post("/pipelines/run", json={"pipeline_file": "p.yaml"}, headers=AUTH).json()[
        "run_id"
    ]
    body = _wait(c, run_id, {"failed"})
    assert "kaput" in body["error"]
    assert c.get(f"/pipelines/{run_id}/report", headers=AUTH).status_code == 409


def test_unknown_run_404(make):
    c = make()
    assert c.get("/pipelines/nope/status", headers=AUTH).status_code == 404
    assert c.get("/pipelines/nope/report", headers=AUTH).status_code == 404


def test_path_traversal_rejected(make):
    c = make()
    r = c.post("/pipelines/run", json={"pipeline_file": "../../etc/passwd"}, headers=AUTH)
    assert r.status_code == 400
    r = c.post("/pipelines/run", json={"pipeline_file": "missing.yaml"}, headers=AUTH)
    assert r.status_code == 404


def test_auth_required(make):
    c = make()
    assert c.get("/pipelines/x/status").status_code == 401
    assert (
        c.get("/pipelines/x/status", headers={"Authorization": "Bearer wrong"}).status_code == 401
    )
    assert c.post("/pipelines/run", json={"pipeline_file": "p.yaml"}).status_code == 401


def test_fail_closed_without_token(make):
    c = make(token="")
    assert c.get("/pipelines/x/status", headers=AUTH).status_code == 401


def test_token_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("AZUREML_AGENT_API_TOKEN", "envtok")
    app = create_app(
        store=SqliteRunStore(tmp_path / "r.db"),
        pipeline_runner=lambda p: _result(),
        pipelines_dir=tmp_path,
    )
    c = TestClient(app)
    assert (
        c.get("/pipelines/x/status", headers={"Authorization": "Bearer envtok"}).status_code == 404
    )


def test_openapi_docs_have_examples(make):
    c = make()
    assert c.get("/docs").status_code == 200
    schema = c.get("/openapi.json").json()
    assert "/pipelines/run" in schema["paths"]
    body = schema["components"]["schemas"]["RunRequest"]
    assert body["examples"]
