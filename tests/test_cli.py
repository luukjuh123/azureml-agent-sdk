"""Tests for the CLI entrypoint (P2-07): `azureml-agent run pipeline.yaml`.

The pipeline runner is monkeypatched so these tests never touch real Azure
ML or Azure OpenAI, only the CLI's argument parsing, dispatch, and output.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from azureml_agent_sdk import cli
from azureml_agent_sdk.batch_trigger import BatchJobResult
from azureml_agent_sdk.pipeline import AgentRunResult, PipelineResult

runner = CliRunner()


def _make_pipeline_file(tmp_path: Path) -> Path:
    path = tmp_path / "pipeline.yaml"
    path.write_text("name: fraud-check\n")  # contents are irrelevant; runner is mocked
    return path


def test_run_command_invokes_the_pipeline_runner_with_the_given_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline_file = _make_pipeline_file(tmp_path)
    calls: list[Path] = []
    fake_result = PipelineResult(
        job=BatchJobResult(job_name="job-1", status="Completed", output_path="p"),
        rows=[{"id": 1}],
        agent_runs=[],
    )

    def fake_runner(path: Path) -> PipelineResult:
        calls.append(path)
        return fake_result

    monkeypatch.setattr(cli, "run_pipeline_from_yaml", fake_runner)

    result = runner.invoke(cli.app, ["run", str(pipeline_file)])

    assert result.exit_code == 0
    assert calls == [pipeline_file]


def test_run_command_prints_a_summary_of_the_pipeline_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline_file = _make_pipeline_file(tmp_path)
    fake_result = PipelineResult(
        job=BatchJobResult(job_name="job-42", status="Completed", output_path="p"),
        rows=[{"id": 1}, {"id": 2}],
        agent_runs=[AgentRunResult(agent_name="reviewer", responses=[])],
    )
    monkeypatch.setattr(cli, "run_pipeline_from_yaml", lambda path: fake_result)

    result = runner.invoke(cli.app, ["run", str(pipeline_file)])

    assert result.exit_code == 0
    assert "job-42" in result.stdout
    assert "Completed" in result.stdout


def test_run_command_requires_the_run_subcommand_name() -> None:
    # Bare `azureml-agent pipeline.yaml` (no "run") must not silently work --
    # the CLI surface is `azureml-agent run pipeline.yaml`.
    result = runner.invoke(cli.app, ["pipeline.yaml"])

    assert result.exit_code != 0


def test_run_command_fails_cleanly_on_a_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.yaml"

    result = runner.invoke(cli.app, ["run", str(missing)])

    assert result.exit_code != 0


def test_run_command_exits_non_zero_when_the_pipeline_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline_file = _make_pipeline_file(tmp_path)

    def failing_runner(path: Path) -> PipelineResult:
        raise RuntimeError("batch job failed")

    monkeypatch.setattr(cli, "run_pipeline_from_yaml", failing_runner)

    result = runner.invoke(cli.app, ["run", str(pipeline_file)])

    assert result.exit_code != 0
    assert "batch job failed" in result.stdout


def test_default_runner_loads_and_runs_the_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline_file = _make_pipeline_file(tmp_path)
    fake_result = PipelineResult(
        job=BatchJobResult(job_name="job-1", status="Completed", output_path="p"),
        rows=[],
        agent_runs=[],
    )
    calls: list[Path] = []

    def fake_load_pipeline(path):
        calls.append(path)

        class _FakePipeline:
            def run(self_inner):
                return fake_result

        return _FakePipeline()

    monkeypatch.setattr(cli, "load_pipeline", fake_load_pipeline)

    result = cli.run_pipeline_from_yaml(pipeline_file)

    assert result is fake_result
    assert calls == [pipeline_file]
