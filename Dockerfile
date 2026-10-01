FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra api
ENV PATH="/app/.venv/bin:$PATH" AZUREML_AGENT_DB=/data/runs.db AZUREML_AGENT_PIPELINES_DIR=/pipelines
EXPOSE 8000
CMD ["uvicorn", "azureml_agent_sdk.api.app:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000"]
