"""Sanity tests for the package scaffold and public API surface (P1-01, P1-10)."""
from __future__ import annotations

import azureml_agent_sdk as sdk


class TestPublicApi:
    def test_exposes_core_classes(self):
        assert hasattr(sdk, "AgentConfig")
        assert hasattr(sdk, "BatchEndpointConfig")
        assert hasattr(sdk, "PipelineConfig")
        assert hasattr(sdk, "AzureMLClientWrapper")
        assert hasattr(sdk, "BatchEndpointTrigger")
        assert hasattr(sdk, "AzureOpenAIAgent")
        assert hasattr(sdk, "AgentPipeline")
        assert hasattr(sdk, "CredentialManager")

    def test_has_version(self):
        assert isinstance(sdk.__version__, str)
        assert sdk.__version__
