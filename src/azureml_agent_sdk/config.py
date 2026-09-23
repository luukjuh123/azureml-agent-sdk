"""Pydantic v2 configuration models for azureml-agent-sdk (P1-09)."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _require_non_blank(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("must not be blank")
    return value


class BatchEndpointConfig(BaseModel):
    """Configuration for submitting and polling an Azure ML batch endpoint job."""

    endpoint_name: str
    deployment_name: str | None = None
    subscription_id: str | None = None
    resource_group: str | None = None
    workspace_name: str | None = None
    input_data_path: str
    poll_interval_seconds: float = Field(default=10.0, gt=0)
    timeout_seconds: float = Field(default=3600.0, gt=0)

    @field_validator("endpoint_name", "input_data_path")
    @classmethod
    def _validate_non_blank(cls, value: str) -> str:
        return _require_non_blank(value)


class AgentConfig(BaseModel):
    """Configuration for a single AzureOpenAIAgent."""

    name: str
    system_prompt: str
    model: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    endpoint: str | None = None
    api_version: str = "2024-02-15-preview"

    @field_validator("name", "system_prompt", "model")
    @classmethod
    def _validate_non_blank(cls, value: str) -> str:
        return _require_non_blank(value)


class PipelineConfig(BaseModel):
    """Configuration for an AgentPipeline: one batch endpoint, one or more agents."""

    name: str
    batch_endpoint: BatchEndpointConfig
    agents: list[AgentConfig]

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _require_non_blank(value)

    @field_validator("agents")
    @classmethod
    def _validate_at_least_one_agent(cls, value: list[AgentConfig]) -> list[AgentConfig]:
        if not value:
            raise ValueError("PipelineConfig requires at least one agent")
        return value
