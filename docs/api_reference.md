# API Reference

All names below are importable from `azureml_agent_sdk`.

## Configuration

- `BatchEndpointConfig(endpoint_name, input_data_path, deployment_name=None, subscription_id=None, resource_group=None, workspace_name=None, poll_interval_seconds=10.0, timeout_seconds=3600.0)`
- `AgentConfig(name, system_prompt, model, temperature=0.7, max_tokens=None, endpoint=None, api_version="2024-02-15-preview")`
- `PipelineConfig(name, batch_endpoint, agents)`

## BatchEndpointTrigger

`BatchEndpointTrigger(config, aml_client, sleep=time.sleep, clock=time.monotonic)`

| Method | Description |
|--------|-------------|
| `submit() -> str` | Invoke the endpoint; return the job name |
| `get_status(job_name) -> str` | Current job status |
| `get_output_path(job_name) -> str` | Resolve the output path of a completed job |
| `run() -> BatchJobResult` | Submit, poll to terminal state, return `BatchJobResult(job_name, status, output_path)` |

Raises `BatchJobFailedError` (Failed/Canceled) or `BatchJobTimeoutError`.

## AzureOpenAIAgent

`AzureOpenAIAgent(config, credential_manager=None, client_factory=None)`

- `run(user_message, history=None) -> AgentResponse` — one chat completion; `AgentResponse.content` holds the reply.
- `client` — lazily built `AzureOpenAI` client (API key if `AZURE_OPENAI_API_KEY` is set, else Azure AD token).

## AgentPipeline

`AgentPipeline(name, trigger, agents, output_parser=parse_batch_output, events=None)`

- `run() -> PipelineResult` with `.job`, `.rows`, `.agent_runs` (`AgentRunResult(agent_name, responses)`) and `.quality_reports`.
- `DataQualityAgent` entries in `agents` run once over all rows; others run once per row.

## ParallelAgentGroup

`ParallelAgentGroup(agents, max_concurrency=None)`

- `await run(user_message, history=None) -> list[AgentResponse]` — all agents concurrently, in agent order.
- `await run_batch(messages, history=None) -> list[list[AgentResponse]]`

## AgentRouter

`AgentRouter(rules, default_agent=None)` where `rules` is a list of `(matcher, agent)`.

- `select_agent(row)` — first matching agent, else the default; raises `NoMatchingAgentError`.
- `run(row, user_message, history=None) -> AgentResponse`
- `AgentRouter.field_equals(field, value)` / `AgentRouter.field_matches(field, pattern)` — matcher builders.

## AgentMemory

`AgentMemory(max_tokens, token_counter=None)` — `add(role, content)` evicts the oldest turns to stay
within budget; `history()` returns the window; `total_tokens()` counts it.

## RetryPolicy

`RetryPolicy(max_retries=3, base_delay=1.0, max_delay=30.0, jitter=0.1, retryable_exceptions=DEFAULT_RETRYABLE_EXCEPTIONS, sleep=..., random_func=...)`

- `call(fn, *args, **kwargs)` — call with exponential backoff on retryable errors; re-raises after `max_retries`.
- `compute_delay(attempt)` — delay before retry `attempt` (1-indexed).

## Data-quality agents

`DataQualityAgent` (abstract): `check(rows) -> QualityReport`.

| Class | Purpose |
|-------|---------|
| `NullCheckAgent(threshold=0.1)` | Flags null/missing values above a threshold |
| `SchemaValidationAgent(schema)` | Validates rows against a Pydantic model |
| `AnomalyDetectionAgent(agent=None, z_threshold=3.0)` | Flags numeric outliers (optionally AOAI-assisted) |
| `DuplicateDetectionAgent(fuzzy=False, threshold=0.9)` | Hash + optional fuzzy duplicate detection |
| `SummaryAgent(agent, reports=None, max_issues=10)` | AOAI natural-language summary of reports |

## QualityReport

Pydantic model: `run_id`, `agent_name`, `total_rows`, `findings: list[Finding]`, `aggregate: AggregateStats`, `generated_at`.
`Finding(row_index, column, severity, message)` with severity `INFO | WARN | ERROR`;
`AggregateStats(info_count, warn_count, error_count, pass_rate)`.
Build with `QualityReport.build(run_id, agent_name, total_rows, findings)`.
`ReportSerializer.to_json / to_markdown / to_blob` persist reports.

## Other

- `PipelineEvents` — hooks: batch start/complete, agent start/complete, error.
- `CredentialManager` — `DefaultAzureCredential` + env-var fallback.
- `load_pipeline(path)` / `build_pipeline(config)` — YAML pipelines.
- `parse_batch_output`, `parse_jsonl`, `parse_csv`, `rows_to_messages` — output parsing helpers.
