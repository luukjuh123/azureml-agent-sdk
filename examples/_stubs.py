"""Offline stand-ins for Azure ML and Azure OpenAI, shared by the example pipelines.

The examples use the *real* SDK classes (``BatchEndpointTrigger``, ``AzureOpenAIAgent``,
``AgentPipeline``); only the network-facing clients are replaced, so no Azure
credentials are needed. To run against real Azure, drop the stubs and build the
``AzureMLClientWrapper`` / agents without ``client_factory``.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any


class StubAMLClient:
    """Mimics the subset of ``AzureMLClientWrapper`` that BatchEndpointTrigger uses.

    "Running" the batch job just points the output at a local JSONL file holding
    the canned scoring rows, so the rest of the pipeline parses real files.
    """

    def __init__(self, rows: list[dict[str, Any]], workdir: Path | None = None) -> None:
        self._dir = workdir or Path(tempfile.mkdtemp(prefix="azureml-agent-example-"))
        self._output = self._dir / "predictions.jsonl"
        self._output.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        self.invocations: list[dict[str, Any]] = []
        self.client = SimpleNamespace(
            batch_endpoints=SimpleNamespace(invoke=self._invoke),
            jobs=SimpleNamespace(get=self._get_job),
        )

    def _invoke(self, **kwargs: Any) -> SimpleNamespace:
        self.invocations.append(kwargs)
        return SimpleNamespace(name="stub-job-001")

    def _get_job(self, name: str) -> SimpleNamespace:
        return SimpleNamespace(
            name=name,
            status="Completed",
            outputs={"score": SimpleNamespace(path=str(self._output))},
        )


def make_stub_openai_client(reply_for: Callable[[str], str]) -> Callable[[], Any]:
    """Return a ``client_factory`` whose chat completions come from ``reply_for``.

    ``reply_for`` receives the last user message (the JSON-encoded batch row).
    """

    def _create(**kwargs: Any) -> SimpleNamespace:
        user_message = kwargs["messages"][-1]["content"]
        message = SimpleNamespace(content=reply_for(user_message))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    def factory() -> Any:
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_create)))

    return factory
