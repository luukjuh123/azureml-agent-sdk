"""Tests for structured JSON logging & telemetry (P1-08)."""
from __future__ import annotations

import json
import logging

from azureml_agent_sdk.logging_utils import (
    JsonFormatter,
    attach_azure_monitor_sink,
    get_pipeline_logger,
    log_step,
)


class TestJsonFormatter:
    def _make_record(self, message="hello", extra=None):
        record = logging.LogRecord(
            name="azureml_agent_sdk.pipeline",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )
        if extra:
            record.step_data = extra
        return record

    def test_formats_record_as_valid_json_with_core_fields(self):
        formatter = JsonFormatter()
        output = formatter.format(self._make_record("batch.start"))
        payload = json.loads(output)

        assert payload["message"] == "batch.start"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "azureml_agent_sdk.pipeline"
        assert "timestamp" in payload

    def test_includes_step_data_when_present(self):
        formatter = JsonFormatter()
        output = formatter.format(self._make_record("agent.start", extra={"agent": "reviewer"}))
        payload = json.loads(output)

        assert payload["data"]["agent"] == "reviewer"

    def test_redacts_secret_like_keys_in_step_data(self):
        formatter = JsonFormatter()
        output = formatter.format(
            self._make_record("agent.start", extra={"api_key": "sk-abcdef", "agent": "reviewer"})
        )
        payload = json.loads(output)

        assert payload["data"]["api_key"] == "***"
        assert payload["data"]["agent"] == "reviewer"
        assert "sk-abcdef" not in output


class TestGetPipelineLogger:
    def test_returns_logger_with_json_formatter_attached(self):
        logger = get_pipeline_logger("test.pipeline.one")
        assert any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers)

    def test_does_not_duplicate_handlers_on_repeated_calls(self):
        logger_a = get_pipeline_logger("test.pipeline.two")
        handler_count_after_first = len(logger_a.handlers)
        logger_b = get_pipeline_logger("test.pipeline.two")

        assert logger_a is logger_b
        assert len(logger_b.handlers) == handler_count_after_first


class TestLogStep:
    def test_logs_info_record_with_step_data(self, caplog):
        logger = get_pipeline_logger("test.pipeline.three")
        with caplog.at_level(logging.INFO, logger="test.pipeline.three"):
            log_step(logger, "batch.complete", job_name="job-1", status="Completed")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.message == "batch.complete"
        assert record.step_data == {"job_name": "job-1", "status": "Completed"}


class TestAttachAzureMonitorSink:
    def test_returns_false_when_no_connection_string(self):
        logger = get_pipeline_logger("test.pipeline.four")
        assert attach_azure_monitor_sink(logger, connection_string=None) is False

    def test_calls_injected_configure_fn_with_connection_string_when_attached(self):
        logger = get_pipeline_logger("test.pipeline.five")
        calls = []

        def fake_configure(**kwargs):
            calls.append(kwargs)

        attached = attach_azure_monitor_sink(
            logger, connection_string="InstrumentationKey=x", configure_fn=fake_configure
        )

        assert attached is True
        assert calls == [{"connection_string": "InstrumentationKey=x"}]

    def test_returns_false_when_configure_fn_raises_import_error(self):
        logger = get_pipeline_logger("test.pipeline.six")

        def missing_dependency(**kwargs):
            raise ImportError("azure-monitor-opentelemetry not installed")

        # Degrades gracefully rather than raising, since the sink is optional.
        assert (
            attach_azure_monitor_sink(
                logger, connection_string="InstrumentationKey=x", configure_fn=missing_dependency
            )
            is False
        )
