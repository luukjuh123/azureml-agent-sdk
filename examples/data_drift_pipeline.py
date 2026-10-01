"""Data-drift pipeline: an AML batch endpoint computes per-feature drift metrics,
then an Azure OpenAI agent writes a drift report.

Runs fully offline with stubbed Azure clients:

    uv run python examples/data_drift_pipeline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _stubs import StubAMLClient, make_stub_openai_client

from azureml_agent_sdk import (
    AgentConfig,
    AgentPipeline,
    AzureOpenAIAgent,
    BatchEndpointConfig,
    BatchEndpointTrigger,
    NullCheckAgent,
    PipelineResult,
)

# Pretend output of the "drift-metrics" batch endpoint: one row per feature.
DRIFT_METRICS = [
    {"feature": "age", "psi": 0.04, "drifted": False},
    {"feature": "income", "psi": 0.31, "drifted": True},
    {"feature": "tenure_months", "psi": 0.07, "drifted": False},
    {"feature": "region", "psi": 0.45, "drifted": True},
]

SYSTEM_PROMPT = (
    "You are an ML monitoring assistant. You receive drift metrics for one feature "
    "as JSON (PSI above 0.2 is significant). Write a one-sentence report line."
)


def _stub_reply(user_message: str) -> str:
    row = json.loads(user_message)
    level = "significant drift" if row["drifted"] else "stable"
    return f"- {row['feature']}: {level} (PSI={row['psi']:.2f})"


def build_pipeline() -> AgentPipeline:
    trigger = BatchEndpointTrigger(
        config=BatchEndpointConfig(
            endpoint_name="drift-metrics",
            deployment_name="default",
            input_data_path="azureml://datastores/workspaceblobstore/paths/features/",
        ),
        aml_client=StubAMLClient(DRIFT_METRICS),  # type: ignore[arg-type]
        sleep=lambda _s: None,
    )
    writer = AzureOpenAIAgent(
        AgentConfig(name="drift-reporter", system_prompt=SYSTEM_PROMPT, model="gpt-4o"),
        client_factory=make_stub_openai_client(_stub_reply),
    )
    # DataQualityAgents mix in with LLM agents; this one checks the metrics themselves.
    return AgentPipeline(
        name="data-drift", trigger=trigger, agents=[NullCheckAgent(threshold=0.0), writer]
    )


def render_report(result: PipelineResult) -> str:
    """Assemble the agent's per-feature lines into one Markdown report."""
    lines = [r.content for r in result.agent_runs[0].responses]
    drifted = sum(1 for row in result.rows if row["drifted"])
    header = f"# Drift report ({drifted}/{len(result.rows)} features drifted)"
    return "\n".join([header, *lines])


def main() -> str:
    report = render_report(build_pipeline().run())
    print(report)
    return report


if __name__ == "__main__":
    main()
