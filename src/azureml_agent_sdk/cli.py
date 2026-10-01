"""CLI entrypoint: ``azureml-agent run pipeline.yaml`` (P2-07).

Kept deliberately thin: argument parsing and output formatting only. The
actual work (parse YAML, build clients, execute the pipeline) lives in
``yaml_loader`` and ``pipeline`` -- ``run_pipeline_from_yaml`` is a plain
module-level function so tests can monkeypatch it without needing real
Azure ML or Azure OpenAI credentials.
"""

from __future__ import annotations

from pathlib import Path

import typer

from azureml_agent_sdk.pipeline import PipelineResult
from azureml_agent_sdk.yaml_loader import load_pipeline

app = typer.Typer(help="azureml-agent-sdk command-line interface")


@app.callback()
def _main() -> None:
    """azureml-agent-sdk command-line interface."""


def run_pipeline_from_yaml(pipeline_file: Path) -> PipelineResult:
    """Load a pipeline from ``pipeline_file`` and run it end to end."""
    pipeline = load_pipeline(pipeline_file)
    return pipeline.run()


@app.command()
def run(
    pipeline_file: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Path to a pipeline YAML file",
    ),
) -> None:
    """Run the pipeline defined in PIPELINE_FILE."""
    try:
        result = run_pipeline_from_yaml(pipeline_file)
    except Exception as exc:  # noqa: BLE001 - surface any pipeline failure to the caller
        typer.echo(f"pipeline run failed: {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"pipeline job={result.job.job_name} status={result.job.status} "
        f"rows={len(result.rows)} agents={len(result.agent_runs)}"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
