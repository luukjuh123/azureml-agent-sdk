"""Content-moderation pipeline: an AML batch endpoint classifies text, then Azure
OpenAI agents draft moderation decisions, routed by the classifier's label.

Runs fully offline with stubbed Azure clients:

    uv run python examples/content_moderation_pipeline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _stubs import StubAMLClient, make_stub_openai_client

from azureml_agent_sdk import (
    AgentConfig,
    AgentRouter,
    AzureOpenAIAgent,
    BatchEndpointConfig,
    BatchEndpointTrigger,
    parse_batch_output,
)

# Pretend output of the "text-classifier" batch endpoint.
CLASSIFIED_POSTS = [
    {"post_id": "p-1", "text": "Loving the new release!", "label": "safe"},
    {"post_id": "p-2", "text": "You are all idiots.", "label": "toxic"},
    {"post_id": "p-3", "text": "Buy followers cheap at example.biz", "label": "spam"},
    {"post_id": "p-4", "text": "Great tutorial, thanks.", "label": "safe"},
]


def _agent(name: str, prompt: str, decision: str) -> AzureOpenAIAgent:
    """Build an agent whose stubbed model always drafts ``decision``."""

    def reply(user_message: str) -> str:
        row = json.loads(user_message)
        return f"{decision} {row['post_id']}"

    return AzureOpenAIAgent(
        AgentConfig(name=name, system_prompt=prompt, model="gpt-4o", temperature=0.2),
        client_factory=make_stub_openai_client(reply),
    )


def build_router() -> AgentRouter:
    """Route rows by label: toxic -> moderator, spam -> spam handler, else approve."""
    moderator = _agent("moderator", "Draft a moderation decision for toxic content.", "REMOVE")
    spam_handler = _agent("spam-handler", "Draft a moderation decision for spam.", "BAN_LINK")
    approver = _agent("approver", "Confirm that safe content can stay up.", "KEEP")
    return AgentRouter(
        rules=[
            (AgentRouter.field_equals("label", "toxic"), moderator),
            (AgentRouter.field_equals("label", "spam"), spam_handler),
        ],
        default_agent=approver,
    )


def build_trigger() -> BatchEndpointTrigger:
    return BatchEndpointTrigger(
        config=BatchEndpointConfig(
            endpoint_name="text-classifier",
            deployment_name="default",
            input_data_path="azureml://datastores/workspaceblobstore/paths/posts/",
        ),
        aml_client=StubAMLClient(CLASSIFIED_POSTS),  # type: ignore[arg-type]
        sleep=lambda _s: None,
    )


def main() -> dict[str, str]:
    job = build_trigger().run()
    rows = parse_batch_output(job.output_path)
    router = build_router()
    decisions = {
        row["post_id"]: router.run(row, json.dumps(row, sort_keys=True)).content for row in rows
    }
    for post_id, decision in decisions.items():
        print(f"{post_id}: {decision}")
    return decisions


if __name__ == "__main__":
    main()
