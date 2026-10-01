"""Tests for AgentRouter (P2-02): route batch output rows to different agents
based on a rule/classifier -- row field value, regex match, or arbitrary
callable -- with first-match-wins ordering and an optional fallback agent."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from azureml_agent_sdk.agent import AgentResponse
from azureml_agent_sdk.router import AgentRouter, NoMatchingAgentError


@dataclass
class _FakeConfig:
    name: str


class _FakeAgent:
    def __init__(self, name: str) -> None:
        self.config = _FakeConfig(name=name)
        self.calls: list[str] = []

    def run(self, user_message: str, history: list[dict[str, str]] | None = None) -> AgentResponse:
        self.calls.append(user_message)
        return AgentResponse(content=f"{self.config.name}:{user_message}")


def test_routes_by_field_equality() -> None:
    fraud_agent = _FakeAgent("fraud")
    default_agent = _FakeAgent("default")
    router = AgentRouter(
        rules=[(AgentRouter.field_equals("category", "fraud"), fraud_agent)],
        default_agent=default_agent,
    )

    agent = router.select_agent({"category": "fraud", "amount": 100})

    assert agent is fraud_agent


def test_routes_by_regex_on_a_field() -> None:
    flag_agent = _FakeAgent("flag")
    default_agent = _FakeAgent("default")
    router = AgentRouter(
        rules=[(AgentRouter.field_matches("note", r"(?i)urgent"), flag_agent)],
        default_agent=default_agent,
    )

    agent = router.select_agent({"note": "This is URGENT, please review"})

    assert agent is flag_agent


def test_routes_by_arbitrary_callable() -> None:
    high_value_agent = _FakeAgent("high-value")
    default_agent = _FakeAgent("default")
    router = AgentRouter(
        rules=[(lambda row: row["amount"] > 1000, high_value_agent)],
        default_agent=default_agent,
    )

    agent = router.select_agent({"amount": 5000})

    assert agent is high_value_agent


def test_first_matching_rule_wins() -> None:
    first_agent = _FakeAgent("first")
    second_agent = _FakeAgent("second")
    router = AgentRouter(
        rules=[
            (lambda row: row["amount"] > 100, first_agent),
            (lambda row: row["amount"] > 0, second_agent),
        ],
    )

    agent = router.select_agent({"amount": 500})

    assert agent is first_agent


def test_falls_back_to_default_agent_when_no_rule_matches() -> None:
    special_agent = _FakeAgent("special")
    default_agent = _FakeAgent("default")
    router = AgentRouter(
        rules=[(AgentRouter.field_equals("category", "fraud"), special_agent)],
        default_agent=default_agent,
    )

    agent = router.select_agent({"category": "benign"})

    assert agent is default_agent


def test_raises_when_no_rule_matches_and_no_default_configured() -> None:
    special_agent = _FakeAgent("special")
    router = AgentRouter(rules=[(AgentRouter.field_equals("category", "fraud"), special_agent)])

    with pytest.raises(NoMatchingAgentError):
        router.select_agent({"category": "benign"})


def test_run_selects_agent_and_delegates_to_it() -> None:
    fraud_agent = _FakeAgent("fraud")
    default_agent = _FakeAgent("default")
    router = AgentRouter(
        rules=[(AgentRouter.field_equals("category", "fraud"), fraud_agent)],
        default_agent=default_agent,
    )

    response = router.run({"category": "fraud"}, "please review this row")

    assert response.content == "fraud:please review this row"
    assert fraud_agent.calls == ["please review this row"]
    assert default_agent.calls == []


def test_field_matches_treats_missing_field_as_no_match() -> None:
    matcher = AgentRouter.field_matches("note", r"urgent")

    assert matcher({}) is False
