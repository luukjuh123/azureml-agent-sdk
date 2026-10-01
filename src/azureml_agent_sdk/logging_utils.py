"""Structured JSON logging & telemetry for pipeline steps (P1-08).

Every pipeline step is logged as a single JSON object via ``log_step``. An
optional Azure Monitor sink can be attached with ``attach_azure_monitor_sink``;
it degrades gracefully (returns ``False``) when no connection string is
configured or the sink cannot be set up, rather than raising.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

_REDACT_KEYS = {"api_key", "azure_openai_api_key", "key", "secret", "token", "password"}


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    return {key: ("***" if key.lower() in _REDACT_KEYS else value) for key, value in data.items()}


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects, redacting secret-like keys."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        step_data = getattr(record, "step_data", None)
        if step_data:
            payload["data"] = _redact(step_data)
        return json.dumps(payload)


def get_pipeline_logger(name: str = "azureml_agent_sdk.pipeline") -> logging.Logger:
    """Return a logger configured to emit structured JSON, without duplicate handlers."""
    logger = logging.getLogger(name)
    if not any(isinstance(handler.formatter, JsonFormatter) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def log_step(logger: logging.Logger, step: str, **data: Any) -> None:
    """Log a single pipeline step with structured key/value data."""
    logger.info(step, extra={"step_data": data})


def attach_azure_monitor_sink(
    logger: logging.Logger,
    connection_string: str | None = None,
    configure_fn: Callable[..., Any] | None = None,
) -> bool:
    """Attach an Azure Monitor sink if a connection string is configured.

    ``configure_fn`` defaults to ``azure.monitor.opentelemetry.configure_azure_monitor``
    and can be injected for tests. Returns ``True`` if the sink was attached, ``False``
    if it was skipped or could not be set up — this never raises for a missing or
    misbehaving optional dependency, since the sink is opt-in telemetry.
    """
    if not connection_string:
        return False
    if configure_fn is None:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor as configure_fn
        except ImportError:
            return False
    try:
        configure_fn(connection_string=connection_string)  # type: ignore[misc]
    except ImportError:
        return False
    return True
