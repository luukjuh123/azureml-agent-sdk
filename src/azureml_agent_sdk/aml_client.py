"""Thin wrapper around azure.ai.ml.MLClient for connecting to an AML workspace (P1-02).

The underlying ``MLClient`` is constructed lazily via ``DefaultAzureCredential`` and
can be swapped out entirely with ``ml_client_factory`` for tests, so no real Azure
credentials or network access are ever required to exercise this class.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from azureml_agent_sdk.credentials import CredentialManager


@dataclass(frozen=True)
class BatchEndpointSummary:
    """A lightweight summary of an Azure ML batch endpoint."""

    name: str
    provisioning_state: str | None = None


class AzureMLClientWrapper:
    """Connects to an Azure ML workspace and lists/fetches batch endpoints."""

    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        workspace_name: str,
        credential_manager: CredentialManager | None = None,
        ml_client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.workspace_name = workspace_name
        self._credential_manager = credential_manager or CredentialManager()
        self._ml_client_factory = ml_client_factory
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        """Return the cached ``MLClient``, constructing it lazily on first use."""
        if self._client is None:
            if self._ml_client_factory is not None:
                self._client = self._ml_client_factory()
            else:
                from azure.ai.ml import MLClient

                self._client = MLClient(
                    credential=self._credential_manager.get_credential(),
                    subscription_id=self.subscription_id,
                    resource_group_name=self.resource_group,
                    workspace_name=self.workspace_name,
                )
        return self._client

    def list_batch_endpoints(self) -> list[BatchEndpointSummary]:
        """List batch endpoints in the workspace as lightweight summaries."""
        endpoints: Iterable[Any] = self.client.batch_endpoints.list()
        return [
            BatchEndpointSummary(
                name=endpoint.name,
                provisioning_state=getattr(endpoint, "provisioning_state", None),
            )
            for endpoint in endpoints
        ]

    def get_batch_endpoint(self, name: str) -> Any:
        """Return the raw batch endpoint object for ``name``."""
        return self.client.batch_endpoints.get(name)
