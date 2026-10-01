"""Tests for batch output parsing & result-to-message injection (P1-06)."""

from __future__ import annotations

import json

import pytest

from azureml_agent_sdk.results import (
    UnsupportedBatchOutputFormatError,
    parse_batch_output,
    parse_csv,
    parse_jsonl,
    rows_to_messages,
)


class TestParseJsonl:
    def test_parses_lines_into_dicts(self):
        text = '{"id": 1, "amount": 100}\n{"id": 2, "amount": 250}\n'
        rows = parse_jsonl(text)
        assert rows == [{"id": 1, "amount": 100}, {"id": 2, "amount": 250}]

    def test_skips_blank_lines(self):
        text = '{"id": 1}\n\n   \n{"id": 2}\n'
        rows = parse_jsonl(text)
        assert rows == [{"id": 1}, {"id": 2}]


class TestParseCsv:
    def test_parses_rows_into_dicts(self):
        text = "id,amount\n1,100\n2,250\n"
        rows = parse_csv(text)
        assert rows == [{"id": "1", "amount": "100"}, {"id": "2", "amount": "250"}]


class TestParseBatchOutput:
    def test_parses_jsonl_file_by_suffix(self, tmp_path):
        file_path = tmp_path / "output.jsonl"
        file_path.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")

        rows = parse_batch_output(file_path)

        assert rows == [{"id": 1}, {"id": 2}]

    def test_parses_csv_file_by_suffix(self, tmp_path):
        file_path = tmp_path / "output.csv"
        file_path.write_text("id,amount\n1,100\n", encoding="utf-8")

        rows = parse_batch_output(file_path)

        assert rows == [{"id": "1", "amount": "100"}]

    def test_raises_for_unsupported_suffix(self, tmp_path):
        file_path = tmp_path / "output.txt"
        file_path.write_text("not structured data", encoding="utf-8")

        with pytest.raises(UnsupportedBatchOutputFormatError):
            parse_batch_output(file_path)

    def test_accepts_str_path(self, tmp_path):
        file_path = tmp_path / "output.jsonl"
        file_path.write_text('{"id": 1}\n', encoding="utf-8")

        rows = parse_batch_output(str(file_path))

        assert rows == [{"id": 1}]


class TestRowsToMessages:
    def test_produces_one_user_message_per_row(self):
        rows = [{"id": 1, "amount": 100}, {"id": 2, "amount": 250}]

        messages = rows_to_messages(rows)

        assert len(messages) == 2
        assert all(message["role"] == "user" for message in messages)

    def test_message_content_round_trips_row_as_json(self):
        rows = [{"id": 1, "amount": 100}]

        messages = rows_to_messages(rows)

        assert json.loads(messages[0]["content"]) == {"id": 1, "amount": 100}
