"""Load a full AgentPipeline from a YAML file (P2-06).

The YAML schema mirrors ``PipelineConfig`` (name, batch_endpoint, agents),
plus a ``type`` discriminator on each agent entry so the schema can grow to
cover other agent kinds later without breaking existing files. Today only
``azure_openai`` is supported; any other value fails Pydantic schema
validation with a clear error rather than silently building the wrong
agent. AML workspace identifiers (subscription/resource group/workspace)
fall back to the usual environment variables when omitted from the YAML,
matching the credential manager's env-var fallback convention used
elsewhere in the SDK.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

from azureml_agent_sdk.agent import AzureOpenAIAgent
from azureml_agent_sdk.aml_client import AzureMLClientWrapper
from azureml_agent_sdk.batch_trigger import BatchEndpointTrigger
from azureml_agent_sdk.config import AgentConfig, BatchEndpointConfig
from azureml_agent_sdk.credentials import CredentialManager
from azureml_agent_sdk.pipeline import AgentPipeline


class PipelineYamlError(ValueError):
    """Raised when a pipeline YAML file fails schema validation."""


class YamlAgentConfig(AgentConfig):
    """An ``AgentConfig`` plus a ``type`` discriminator for the agent kind."""

    type: Literal["azure_openai"] = "azure_openai"

    def to_agent_config(self) -> AgentConfig:
        return AgentConfig(
            name=self.name,
            system_prompt=self.system_prompt,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            endpoint=self.endpoint,
            api_version=self.api_version,
        )


class YamlPipelineConfig(BaseModel):
    """Schema for a pipeline defined in YAML."""

    name: str
    batch_endpoint: BatchEndpointConfig
    agents: list[YamlAgentConfig] = Field(min_length=1)


def load_pipeline_config(path: str | Path) -> YamlPipelineConfig:
    """Parse and validate a pipeline YAML file into a ``YamlPipelineConfig``."""
    data: Any = yaml.safe_load(Path(path).read_text()) or {}
    try:
        return YamlPipelineConfig.model_validate(data)
    except ValidationError as exc:
        raise PipelineYamlError(f"invalid pipeline YAML {path!s}: {exc}") from exc


def build_pipeline(
    config: YamlPipelineConfig,
    ml_client_factory: Callable[[], Any] | None = None,
    agent_client_factory: Callable[[], Any] | None = None,
    credential_manager: CredentialManager | None = None,
) -> AgentPipeline:
    """Construct a runnable ``AgentPipeline`` from a validated pipeline config."""
    batch_config = config.batch_endpoint
    subscription_id = batch_config.subscription_id or CredentialManager.get_env(
        "AZURE_SUBSCRIPTION_ID", required=True
    )
    resource_group = batch_config.resource_group or CredentialManager.get_env(
        "AZURE_RESOURCE_GROUP", required=True
    )
    workspace_name = batch_config.workspace_name or CredentialManager.get_env(
        "AZURE_ML_WORKSPACE", required=True
    )

    aml_client = AzureMLClientWrapper(
        subscription_id=subscription_id,
        resource_group=resource_group,
        workspace_name=workspace_name,
        credential_manager=credential_manager,
        ml_client_factory=ml_client_factory,
    )
    trigger = BatchEndpointTrigger(batch_config, aml_client)

    agents = [
        AzureOpenAIAgent(
            agent_cfg.to_agent_config(),
            credential_manager=credential_manager,
            client_factory=agent_client_factory,
        )
        for agent_cfg in config.agents
    ]

    return AgentPipeline(name=config.name, trigger=trigger, agents=agents)


def load_pipeline(
    path: str | Path,
    ml_client_factory: Callable[[], Any] | None = None,
    agent_client_factory: Callable[[], Any] | None = None,
    credential_manager: CredentialManager | None = None,
) -> AgentPipeline:
    """Load a YAML file and build a runnable ``AgentPipeline`` in one step."""
    config = load_pipeline_config(path)
    return build_pipeline(
        config,
        ml_client_factory=ml_client_factory,
        agent_client_factory=agent_client_factory,
        credential_manager=credential_manager,
    )
