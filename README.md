# azureml-agent-sdk

Couple **Azure ML Batch Endpoints** with **Azure OpenAI** agents to build multi-agent
post-processing pipelines — without hand-rolling credential plumbing, polling loops, or
result marshalling.

- `BatchEndpointTrigger` — submit and poll a batch endpoint job, resolve its output path
- `AzureOpenAIAgent` — configurable wrapper around an AOAI chat-completions deployment
- `AgentPipeline` — chain a trigger into one or more agents
- Data-quality agents, parallel groups, routing, memory, retries, YAML pipelines, and an optional REST harness

## Getting Started

### Install

```bash
pip install azureml-agent-sdk          # or: uv add azureml-agent-sdk
pip install "azureml-agent-sdk[api]"   # optional: FastAPI REST harness
pip install "azureml-agent-sdk[monitor]"  # optional: Azure Monitor log sink
```

Requires Python 3.11+.

### Configure

Credentials come from `DefaultAzureCredential` or environment variables — never from prompts,
and secrets are never logged.

```bash
export AZURE_SUBSCRIPTION_ID=...
export AZURE_RESOURCE_GROUP=...
export AZURE_ML_WORKSPACE=...
export AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
export AZURE_OPENAI_API_KEY=...        # optional; omit to use DefaultAzureCredential
export AZURE_OPENAI_DEPLOYMENT=...
```

### Your first pipeline

```python
from azureml_agent_sdk import (
    AgentConfig,
    AgentPipeline,
    AzureMLClientWrapper,
    AzureOpenAIAgent,
    BatchEndpointConfig,
    BatchEndpointTrigger,
)

trigger = BatchEndpointTrigger(
    config=BatchEndpointConfig(
        endpoint_name="fraud-scoring",
        deployment_name="default",
        input_data_path="azureml://datastores/workspaceblobstore/paths/transactions/",
    ),
    aml_client=AzureMLClientWrapper(),  # reads AZURE_* env vars
)

reviewer = AzureOpenAIAgent(
    AgentConfig(
        name="fraud-reviewer",
        system_prompt="Review this scored transaction. Reply BLOCK, REVIEW or APPROVE with a reason.",
        model="gpt-4o",
        temperature=0.0,
    )
)

result = AgentPipeline(name="fraud-check", trigger=trigger, agents=[reviewer]).run()
for row, response in zip(result.rows, result.agent_runs[0].responses):
    print(row["transaction_id"], response.content)
```

The same pipeline can be defined in YAML and run from the terminal:
`azureml-agent run pipeline.yaml`.

### Try it offline

The `examples/` directory has runnable pipelines that use stubbed Azure clients, so they need
no credentials:

```bash
uv run python examples/fraud_check_pipeline.py
uv run python examples/content_moderation_pipeline.py
uv run python examples/data_drift_pipeline.py
```

## Documentation

- [Architecture](docs/architecture.md)
- [API reference](docs/api_reference.md)
- [PyPI packaging](docs/pypi_packaging.md)
- [Contributing](CONTRIBUTING.md)

See `CLAUDE.md` for the project description and `todo.md` for the build backlog.
