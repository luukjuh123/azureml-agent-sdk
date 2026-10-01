"""Tests for the YAML pipeline loader (P2-06): load a full AgentPipeline from
a YAML file, validating its schema via Pydantic -- valid config, missing
required fields, and an invalid agent type."""

from __future__ import annotations

from pathlib import Path

import pytest

from azureml_agent_sdk.agent import AzureOpenAIAgent
from azureml_agent_sdk.credentials import MissingCredentialError
from azureml_agent_sdk.pipeline import AgentPipeline
from azureml_agent_sdk.yaml_loader import (
    PipelineYamlError,
    build_pipeline,
    load_pipeline,
    load_pipeline_config,
)

VALID_YAML = """
name: fraud-check
batch_endpoint:
  endpoint_name: fraud-scoring
  input_data_path: azureml://datastores/x/paths/y
  subscription_id: sub-123
  resource_group: rg-123
  workspace_name: ws-123
agents:
  - type: azure_openai
    name: reviewer
    system_prompt: You are a fraud reviewer.
    model: gpt-4o
    temperature: 0.2
  - name: summarizer
    system_prompt: Summarize the batch run.
    model: gpt-4o-mini
"""


def _write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "pipeline.yaml"
    path.write_text(content)
    return path


def test_load_pipeline_config_parses_a_valid_yaml_file(tmp_path: Path) -> None:
    path = _write_yaml(tmp_path, VALID_YAML)

    config = load_pipeline_config(path)

    assert config.name == "fraud-check"
    assert config.batch_endpoint.endpoint_name == "fraud-scoring"
    assert len(config.agents) == 2
    assert config.agents[0].type == "azure_openai"
    # type is optional and defaults to azure_openai
    assert config.agents[1].type == "azure_openai"


def test_build_pipeline_constructs_a_runnable_agent_pipeline(tmp_path: Path) -> None:
    path = _write_yaml(tmp_path, VALID_YAML)
    config = load_pipeline_config(path)

    pipeline = build_pipeline(
        config,
        ml_client_factory=lambda: object(),
        agent_client_factory=lambda: object(),
    )

    assert isinstance(pipeline, AgentPipeline)
    assert pipeline.name == "fraud-check"
    assert pipeline.trigger.config.endpoint_name == "fraud-scoring"
    assert len(pipeline.agents) == 2
    assert all(isinstance(agent, AzureOpenAIAgent) for agent in pipeline.agents)
    assert [agent.config.name for agent in pipeline.agents] == ["reviewer", "summarizer"]


def test_load_pipeline_reads_yaml_and_builds_in_one_step(tmp_path: Path) -> None:
    path = _write_yaml(tmp_path, VALID_YAML)

    pipeline = load_pipeline(
        path,
        ml_client_factory=lambda: object(),
        agent_client_factory=lambda: object(),
    )

    assert isinstance(pipeline, AgentPipeline)
    assert pipeline.name == "fraud-check"


def test_missing_required_top_level_field_raises(tmp_path: Path) -> None:
    yaml_without_batch_endpoint = """
name: fraud-check
agents:
  - name: reviewer
    system_prompt: You are a fraud reviewer.
    model: gpt-4o
"""
    path = _write_yaml(tmp_path, yaml_without_batch_endpoint)

    with pytest.raises(PipelineYamlError):
        load_pipeline_config(path)


def test_missing_required_agent_field_raises(tmp_path: Path) -> None:
    yaml_missing_model = """
name: fraud-check
batch_endpoint:
  endpoint_name: fraud-scoring
  input_data_path: azureml://datastores/x/paths/y
agents:
  - name: reviewer
    system_prompt: You are a fraud reviewer.
"""
    path = _write_yaml(tmp_path, yaml_missing_model)

    with pytest.raises(PipelineYamlError):
        load_pipeline_config(path)


def test_invalid_agent_type_raises(tmp_path: Path) -> None:
    yaml_invalid_type = """
name: fraud-check
batch_endpoint:
  endpoint_name: fraud-scoring
  input_data_path: azureml://datastores/x/paths/y
agents:
  - type: carrier_pigeon
    name: reviewer
    system_prompt: You are a fraud reviewer.
    model: gpt-4o
"""
    path = _write_yaml(tmp_path, yaml_invalid_type)

    with pytest.raises(PipelineYamlError):
        load_pipeline_config(path)


def test_no_agents_raises(tmp_path: Path) -> None:
    yaml_empty_agents = """
name: fraud-check
batch_endpoint:
  endpoint_name: fraud-scoring
  input_data_path: azureml://datastores/x/paths/y
agents: []
"""
    path = _write_yaml(tmp_path, yaml_empty_agents)

    with pytest.raises(PipelineYamlError):
        load_pipeline_config(path)


def test_build_pipeline_falls_back_to_env_vars_for_aml_workspace_identifiers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_without_workspace_ids = """
name: fraud-check
batch_endpoint:
  endpoint_name: fraud-scoring
  input_data_path: azureml://datastores/x/paths/y
agents:
  - name: reviewer
    system_prompt: You are a fraud reviewer.
    model: gpt-4o
"""
    path = _write_yaml(tmp_path, yaml_without_workspace_ids)
    config = load_pipeline_config(path)
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "sub-from-env")
    monkeypatch.setenv("AZURE_RESOURCE_GROUP", "rg-from-env")
    monkeypatch.setenv("AZURE_ML_WORKSPACE", "ws-from-env")

    pipeline = build_pipeline(config, ml_client_factory=lambda: object())

    assert pipeline.trigger._aml_client.subscription_id == "sub-from-env"
    assert pipeline.trigger._aml_client.resource_group == "rg-from-env"
    assert pipeline.trigger._aml_client.workspace_name == "ws-from-env"


def test_build_pipeline_raises_missing_credential_when_no_workspace_id_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_without_workspace_ids = """
name: fraud-check
batch_endpoint:
  endpoint_name: fraud-scoring
  input_data_path: azureml://datastores/x/paths/y
agents:
  - name: reviewer
    system_prompt: You are a fraud reviewer.
    model: gpt-4o
"""
    path = _write_yaml(tmp_path, yaml_without_workspace_ids)
    config = load_pipeline_config(path)
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    monkeypatch.delenv("AZURE_RESOURCE_GROUP", raising=False)
    monkeypatch.delenv("AZURE_ML_WORKSPACE", raising=False)

    with pytest.raises(MissingCredentialError):
        build_pipeline(config, ml_client_factory=lambda: object())
