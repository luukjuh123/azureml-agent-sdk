# PyPI Packaging

## Versioning

The version lives in `pyproject.toml` (`[project] version`) and is mirrored by
`azureml_agent_sdk.__version__` — update both together. Follow semantic versioning
(`0.x` while the API is settling).

## Build

```bash
uv build
```

This writes an sdist and wheel to `dist/` using the hatchling backend. Inspect them before
publishing (`tar tzf dist/*.tar.gz`, `unzip -l dist/*.whl`).

## Publish

```bash
uv publish --token "$PYPI_TOKEN"
```

Publishing requires PyPI credentials (an API token, or trusted publishing from CI). **These are
not committed to the repository** — supply them via environment variable or CI secret, and never
log them. To rehearse first, publish to TestPyPI:
`uv publish --publish-url https://test.pypi.org/legacy/ --token "$TEST_PYPI_TOKEN"`.

## Release checklist

1. `uv run pytest` and `uv run ruff check .` are green.
2. Bump the version, commit, and tag `vX.Y.Z`.
3. `uv build`, then `uv publish`.
