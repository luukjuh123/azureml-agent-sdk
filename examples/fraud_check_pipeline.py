"""Fraud-check pipeline: an AML batch endpoint scores transactions, then an Azure
OpenAI agent reviews the flagged ones.

Runs fully offline with stubbed Azure clients:

    uv run python examples/fraud_check_pipeline.py
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
    PipelineResult,
)

# Pretend output of the "fraud-scoring" batch endpoint: one row per transaction.
SCORED_TRANSACTIONS = [
    {"transaction_id": "t-001", "amount": 42.50, "fraud_score": 0.03, "flagged": False},
    {"transaction_id": "t-002", "amount": 9800.00, "fraud_score": 0.97, "flagged": True},
    {"transaction_id": "t-003", "amount": 15.00, "fraud_score": 0.12, "flagged": False},
    {"transaction_id": "t-004", "amount": 4999.99, "fraud_score": 0.88, "flagged": True},
]

SYSTEM_PROMPT = (
    "You are a fraud analyst. You receive one scored transaction as JSON. "
    "Reply with a verdict (BLOCK, REVIEW or APPROVE) and a one-line reason."
)


def _stub_reply(user_message: str) -> str:
    """Canned stand-in for the model; a real deployment would answer here."""
    row = json.loads(user_message)
    verdict = "BLOCK" if row["fraud_score"] > 0.9 else "REVIEW"
    return f"{verdict}: score {row['fraud_score']:.2f} on amount {row['amount']:.2f}"


def build_pipeline() -> AgentPipeline:
    # 1. Trigger: submits the batch job and polls until it completes.
    trigger = BatchEndpointTrigger(
        config=BatchEndpointConfig(
            endpoint_name="fraud-scoring",
            deployment_name="default",
            input_data_path="azureml://datastores/workspaceblobstore/paths/transactions/",
        ),
        aml_client=StubAMLClient(SCORED_TRANSACTIONS),  # type: ignore[arg-type]
        sleep=lambda _s: None,  # don't actually wait between polls
    )
    # 2. Agent: reviews each output row. client_factory swaps AOAI for a stub.
    reviewer = AzureOpenAIAgent(
        AgentConfig(
            name="fraud-reviewer",
            system_prompt=SYSTEM_PROMPT,
            model="gpt-4o",
            temperature=0.0,
        ),
        client_factory=make_stub_openai_client(_stub_reply),
    )
    return AgentPipeline(name="fraud-check", trigger=trigger, agents=[reviewer])


def flagged_reviews(result: PipelineResult) -> list[tuple[str, str]]:
    """Pair each *flagged* transaction id with the agent's verdict."""
    responses = result.agent_runs[0].responses
    return [
        (row["transaction_id"], response.content)
        for row, response in zip(result.rows, responses, strict=True)
        if row["flagged"]
    ]


def main() -> list[tuple[str, str]]:
    result = build_pipeline().run()
    reviews = flagged_reviews(result)
    for transaction_id, verdict in reviews:
        print(f"{transaction_id}: {verdict}")
    return reviews


if __name__ == "__main__":
    main()
