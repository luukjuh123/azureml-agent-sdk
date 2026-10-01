# Contributing

## Development setup

```bash
git clone https://github.com/luukjuh123/azureml-agent-sdk.git
cd azureml-agent-sdk
uv sync
uv run pytest
```

Tests mock every Azure SDK and Azure OpenAI call; no credentials are needed, and none may be
required by new tests. Never log secret values.

## Workflow

- Test-first: write a failing test, make it pass, then refactor.
- Branch from `main` as `feat/<description>` or `fix/<description>`; one backlog item per PR.
- Never force-push or skip hooks (`--no-verify`).

## Code style

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
uv run ruff check .
uv run ruff format --check .
```

Fix issues with `uv run ruff check --fix . && uv run ruff format .`.

## Adding an example

1. Create `examples/<name>_pipeline.py` using the real SDK classes with the stubs from
   `examples/_stubs.py` (`StubAMLClient`, `make_stub_openai_client`) so it runs offline.
2. Expose `build_pipeline()`/`main()` so tests can import it, and guard the entry point with
   `if __name__ == "__main__":`.
3. Add inline comments explaining each step.
4. Add a test in `tests/test_examples.py` that loads the module and asserts on its output.
