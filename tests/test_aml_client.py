"""Tests for the AzureML client wrapper (P1-02)."""
from __future__ import annotations

from dataclasses import dataclass

from azureml_agent_sdk.aml_client import AzureMLClientWrapper, BatchEndpointSummary


@dataclass
class _FakeEndpoint:
    name: str
    provisioning_state: str = "Succeeded"


class _FakeBatchEndpointsOperations:
    def __init__(self, endpoints):
        self._endpoints = endpoints

    def list(self):
        return iter(self._endpoints)

    def get(self, name):
        for endpoint in self._endpoints:
            if endpoint.name == name:
                return endpoint
        raise KeyError(name)


class _FakeMLClient:
    def __init__(self, endpoints):
        self.batch_endpoints = _FakeBatchEndpointsOperations(endpoints)


class TestAzureMLClientWrapper:
    def _make_wrapper(self, endpoints):
        return AzureMLClientWrapper(
            subscription_id="sub-1",
            resource_group="rg-1",
            workspace_name="ws-1",
            ml_client_factory=lambda: _FakeMLClient(endpoints),
        )

    def test_list_batch_endpoints_returns_summaries(self):
        wrapper = self._make_wrapper(
            [_FakeEndpoint(name="fraud-scoring"), _FakeEndpoint(name="content-mod")]
        )

        summaries = wrapper.list_batch_endpoints()

        assert summaries == [
            BatchEndpointSummary(name="fraud-scoring", provisioning_state="Succeeded"),
            BatchEndpointSummary(name="content-mod", provisioning_state="Succeeded"),
        ]

    def test_get_batch_endpoint_returns_matching_endpoint(self):
        wrapper = self._make_wrapper([_FakeEndpoint(name="fraud-scoring")])

        endpoint = wrapper.get_batch_endpoint("fraud-scoring")

        assert endpoint.name == "fraud-scoring"

    def test_client_is_constructed_lazily_and_cached(self):
        build_calls = []

        def factory():
            build_calls.append(1)
            return _FakeMLClient([])

        wrapper = AzureMLClientWrapper(
            subscription_id="sub-1",
            resource_group="rg-1",
            workspace_name="ws-1",
            ml_client_factory=factory,
        )

        assert build_calls == []
        _ = wrapper.client
        _ = wrapper.client
        assert len(build_calls) == 1

    def test_no_real_credential_required_when_factory_injected(self):
        # Constructing and using the wrapper must never touch DefaultAzureCredential
        # or make a network call when a fake ml_client_factory is supplied.
        wrapper = self._make_wrapper([_FakeEndpoint(name="e")])
        assert wrapper.list_batch_endpoints()
