# azureml-agent-sdk

A Python SDK that couples Azure ML Batch Endpoints with Azure OpenAI agents to build
multi-agent post-processing pipelines.

See `CLAUDE.md` for the full project description and `todo.md` for the build backlog.

## Layout

```
src/azureml_agent_sdk/   library source
tests/                    pytest suite (mocked Azure SDK / AOAI calls)
examples/                 runnable example pipelines
docs/                     architecture, API reference, getting started
```

## Development

```bash
uv sync
uv run pytest
```

A full getting-started guide lands in `docs/` as part of a later backlog phase.
