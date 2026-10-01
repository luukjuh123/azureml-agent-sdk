"""Tests for AzureOpenAIAgent (P1-04)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from azureml_agent_sdk.agent import AgentResponse, AzureOpenAIAgent
from azureml_agent_sdk.config import AgentConfig


@dataclass
class _FakeMessage:
    content: str


@dataclass
class _FakeChoice:
    message: _FakeMessage


@dataclass
class _FakeCompletion:
    choices: list[_FakeChoice]


class _FakeCompletions:
    def __init__(self, reply="Looks fine."):
        self.reply = reply
        self.create_calls: list[dict[str, Any]] = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return _FakeCompletion(choices=[_FakeChoice(message=_FakeMessage(content=self.reply))])


@dataclass
class _FakeChat:
    completions: _FakeCompletions


class _FakeAzureOpenAIClient:
    def __init__(self, reply="Looks fine."):
        self.completions = _FakeCompletions(reply=reply)
        self.chat = _FakeChat(completions=self.completions)


def _make_agent(reply="Looks fine.", **config_overrides):
    fake_client = _FakeAzureOpenAIClient(reply=reply)
    config = AgentConfig(
        name="reviewer",
        system_prompt="You review flagged rows.",
        model="gpt-4o",
        **config_overrides,
    )
    agent = AzureOpenAIAgent(config=config, client_factory=lambda: fake_client)
    return agent, fake_client


class TestAzureOpenAIAgentRun:
    def test_returns_agent_response_with_content_and_raw(self):
        agent, fake_client = _make_agent(reply="No issues found.")

        response = agent.run("row: {'amount': 100}")

        assert isinstance(response, AgentResponse)
        assert response.content == "No issues found."
        assert response.raw is not None

    def test_sends_system_prompt_and_user_message(self):
        agent, fake_client = _make_agent()

        agent.run("please review this row")

        kwargs = fake_client.completions.create_calls[0]
        messages = kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "You review flagged rows."}
        assert messages[-1] == {"role": "user", "content": "please review this row"}

    def test_sends_configured_model_and_temperature(self):
        agent, fake_client = _make_agent(temperature=0.2)

        agent.run("hello")

        kwargs = fake_client.completions.create_calls[0]
        assert kwargs["model"] == "gpt-4o"
        assert kwargs["temperature"] == 0.2

    def test_includes_conversation_history_between_system_and_user_message(self):
        agent, fake_client = _make_agent()
        history = [
            {"role": "user", "content": "earlier row"},
            {"role": "assistant", "content": "earlier reply"},
        ]

        agent.run("latest row", history=history)

        messages = fake_client.completions.create_calls[0]["messages"]
        assert messages == [
            {"role": "system", "content": "You review flagged rows."},
            {"role": "user", "content": "earlier row"},
            {"role": "assistant", "content": "earlier reply"},
            {"role": "user", "content": "latest row"},
        ]


class TestClientLazyConstruction:
    def test_client_factory_called_once_and_cached(self):
        calls = []

        def factory():
            calls.append(1)
            return _FakeAzureOpenAIClient()

        config = AgentConfig(name="reviewer", system_prompt="p", model="gpt-4o")
        agent = AzureOpenAIAgent(config=config, client_factory=factory)

        assert calls == []
        _ = agent.client
        _ = agent.client
        assert len(calls) == 1
