"""azureml-agent-sdk: couple Azure ML Batch Endpoints with Azure OpenAI agents to
build multi-agent post-processing pipelines."""
from __future__ import annotations

from azureml_agent_sdk.agent import AgentResponse, AzureOpenAIAgent
from azureml_agent_sdk.aml_client import AzureMLClientWrapper, BatchEndpointSummary
from azureml_agent_sdk.batch_trigger import (
    BatchEndpointTrigger,
    BatchJobFailedError,
    BatchJobResult,
    BatchJobTimeoutError,
)
from azureml_agent_sdk.config import AgentConfig, BatchEndpointConfig, PipelineConfig
from azureml_agent_sdk.credentials import CredentialManager, MissingCredentialError
from azureml_agent_sdk.logging_utils import (
    JsonFormatter,
    attach_azure_monitor_sink,
    get_pipeline_logger,
    log_step,
)
from azureml_agent_sdk.parallel import ParallelAgentGroup
from azureml_agent_sdk.pipeline import AgentPipeline, AgentRunResult, PipelineResult
from azureml_agent_sdk.results import (
    UnsupportedBatchOutputFormatError,
    parse_batch_output,
    parse_csv,
    parse_jsonl,
    rows_to_messages,
)
from azureml_agent_sdk.router import AgentRouter, NoMatchingAgentError

__version__ = "0.1.0"

__all__ = [
    "AgentConfig",
    "AgentPipeline",
    "AgentResponse",
    "AgentRouter",
    "AgentRunResult",
    "AzureMLClientWrapper",
    "AzureOpenAIAgent",
    "BatchEndpointConfig",
    "BatchEndpointSummary",
    "BatchEndpointTrigger",
    "BatchJobFailedError",
    "BatchJobResult",
    "BatchJobTimeoutError",
    "CredentialManager",
    "JsonFormatter",
    "MissingCredentialError",
    "NoMatchingAgentError",
    "ParallelAgentGroup",
    "PipelineConfig",
    "PipelineResult",
    "UnsupportedBatchOutputFormatError",
    "attach_azure_monitor_sink",
    "get_pipeline_logger",
    "log_step",
    "parse_batch_output",
    "parse_csv",
    "parse_jsonl",
    "rows_to_messages",
    "__version__",
]
