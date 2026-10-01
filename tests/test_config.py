"""Tests for Pydantic v2 config schema (P1-09)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from azureml_agent_sdk.config import AgentConfig, BatchEndpointConfig, PipelineConfig


class TestBatchEndpointConfig:
    def test_builds_with_required_fields_and_defaults(self):
        config = BatchEndpointConfig(
            endpoint_name="fraud-scoring",
            input_data_path="azureml://datastores/blob/paths/input",
        )
        assert config.endpoint_name == "fraud-scoring"
        assert config.poll_interval_seconds == 10.0
        assert config.timeout_seconds == 3600.0
        assert config.deployment_name is None

    def test_blank_endpoint_name_rejected(self):
        with pytest.raises(ValidationError):
            BatchEndpointConfig(endpoint_name="   ", input_data_path="x")

    def test_non_positive_poll_interval_rejected(self):
        with pytest.raises(ValidationError):
            BatchEndpointConfig(
                endpoint_name="e",
                input_data_path="x",
                poll_interval_seconds=0,
            )


class TestAgentConfig:
    def test_builds_with_required_fields_and_defaults(self):
        config = AgentConfig(
            name="reviewer",
            system_prompt="You review flagged rows.",
            model="gpt-4o",
        )
        assert config.temperature == 0.7
        assert config.api_version == "2024-02-15-preview"
        assert config.max_tokens is None

    @pytest.mark.parametrize("temperature", [-0.1, 2.1])
    def test_temperature_out_of_range_rejected(self, temperature):
        with pytest.raises(ValidationError):
            AgentConfig(
                name="reviewer",
                system_prompt="prompt",
                model="gpt-4o",
                temperature=temperature,
            )

    def test_blank_system_prompt_rejected(self):
        with pytest.raises(ValidationError):
            AgentConfig(name="reviewer", system_prompt=" ", model="gpt-4o")


class TestPipelineConfig:
    def test_builds_with_nested_configs(self):
        batch = BatchEndpointConfig(endpoint_name="e", input_data_path="x")
        agent = AgentConfig(name="reviewer", system_prompt="p", model="gpt-4o")
        pipeline = PipelineConfig(name="fraud-check", batch_endpoint=batch, agents=[agent])
        assert pipeline.name == "fraud-check"
        assert pipeline.agents[0].name == "reviewer"

    def test_empty_agents_list_rejected(self):
        batch = BatchEndpointConfig(endpoint_name="e", input_data_path="x")
        with pytest.raises(ValidationError):
            PipelineConfig(name="fraud-check", batch_endpoint=batch, agents=[])

    def test_builds_from_plain_dict(self):
        pipeline = PipelineConfig.model_validate(
            {
                "name": "fraud-check",
                "batch_endpoint": {"endpoint_name": "e", "input_data_path": "x"},
                "agents": [{"name": "reviewer", "system_prompt": "p", "model": "gpt-4o"}],
            }
        )
        assert len(pipeline.agents) == 1
