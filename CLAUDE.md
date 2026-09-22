# azureml-agent-sdk

A Python SDK that couples **Azure ML Batch Endpoints** with **Azure OpenAI** endpoints to build
multi-agent post-processing pipelines — without hand-rolling credential plumbing, polling loops,
or result-marshalling every time.

## Purpose

Azure ML Batch Endpoints are great at running a scoring/inference job over a large dataset, but
turning their output into something actionable (review flagged rows, summarize a run, check data
quality, route rows to a human) usually means writing the same glue code again: poll the job,
download the output, parse JSONL/CSV, stuff rows into a chat completion, handle retries and rate
limits, wire up logging. `azureml-agent-sdk` packages that glue into a small set of composable
primitives:

- **`BatchEndpointTrigger`** — submit and poll an Azure ML batch endpoint job, resolve the output
  blob path when it completes.
- **`AzureOpenAIAgent`** — a thin, configurable wrapper around an Azure OpenAI chat completions
  deployment (system prompt, temperature, model), reachable either via an AML managed online
  endpoint or a direct AOAI resource.
- **`AgentPipeline`** — chains a `BatchEndpointTrigger` into one or more `AzureOpenAIAgent`s,
  feeding parsed batch output rows into agent context windows as the pipeline runs.
- **Data-quality agents** (`NullCheckAgent`, `SchemaValidationAgent`, `AnomalyDetectionAgent`,
  `DuplicateDetectionAgent`, `SummaryAgent`) — post-batch checkers that emit a structured
  `QualityReport` instead of ad-hoc prints.
- **Multi-agent orchestration** — parallel agent groups, rule/classifier-based routing, per-agent
  conversation memory, retry policies for AOAI rate limits, and YAML-defined pipelines.
- **Optional REST harness** — a FastAPI app to trigger and monitor pipelines over HTTP for
  services that don't want to embed the SDK directly.

The SDK targets developers who already have an Azure ML workspace with batch endpoints deployed
and an Azure OpenAI resource (or AOAI-backed AML endpoint) and want to bolt agent-driven
post-processing onto the batch output with minimal boilerplate.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Package/env manager | uv |
| Azure ML | `azure-ai-ml`, `azure-identity` |
| Azure OpenAI | `openai` (Azure client) |
| Config/validation | Pydantic v2 |
| Optional REST harness | FastAPI |
| Tests | pytest, pytest-asyncio |

## Repository Layout (target — see backlog for build order)

```
src/azureml_agent_sdk/   ← library source
tests/                    ← pytest suite (mocked Azure SDK / AOAI calls)
examples/                 ← runnable example pipelines (fraud-check, content-moderation, data-drift)
docs/                     ← architecture, API reference, getting started
```

## Agents

| Agent | Role |
|-------|------|
| azureml-agent-sdk-engineer | Implements the SDK, writes tests first, creates PRs |

## Credentials & Config

All credentials come from environment variables or `DefaultAzureCredential` — never from
interactive prompts, and never logged. Typical variables:

```
AZURE_SUBSCRIPTION_ID=
AZURE_RESOURCE_GROUP=
AZURE_ML_WORKSPACE=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
```

## Rules

@../../../.claude/rules/test-first.md
@../../../.claude/rules/pr-workflow.md
@../../../.claude/rules/karpathy-guidelines.md
