"""A thin, configurable wrapper around an Azure OpenAI chat completions deployment (P1-04).

Reachable either via a direct AOAI resource (API key or Azure AD token) or an AML
managed online endpoint (via a custom ``endpoint``). ``client_factory`` can be
injected to swap in a fake client for tests, so no real AOAI credentials or
network calls are ever required.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from azureml_agent_sdk.config import AgentConfig
from azureml_agent_sdk.credentials import CredentialManager


@dataclass
class AgentResponse:
    """The result of a single agent turn."""

    content: str
    raw: Any = field(repr=False, default=None)


class AzureOpenAIAgent:
    """Wraps an Azure OpenAI chat completions deployment with a fixed system prompt."""

    def __init__(
        self,
        config: AgentConfig,
        credential_manager: CredentialManager | None = None,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.config = config
        self._credential_manager = credential_manager or CredentialManager()
        self._client_factory = client_factory
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        """Return the cached AOAI client, constructing it lazily on first use."""
        if self._client is None:
            if self._client_factory is not None:
                self._client = self._client_factory()
            else:
                self._client = self._build_default_client()
        return self._client

    def _build_default_client(self) -> Any:
        from openai import AzureOpenAI

        endpoint = self.config.endpoint or CredentialManager.get_env(
            "AZURE_OPENAI_ENDPOINT", required=True
        )
        api_key = CredentialManager.get_env("AZURE_OPENAI_API_KEY")
        if api_key:
            return AzureOpenAI(
                azure_endpoint=endpoint,  # type: ignore[arg-type]
                api_key=api_key,
                api_version=self.config.api_version,
            )

        from azure.identity import get_bearer_token_provider

        token_provider = get_bearer_token_provider(
            self._credential_manager.get_credential(),
            "https://cognitiveservices.azure.com/.default",
        )
        return AzureOpenAI(
            azure_endpoint=endpoint,  # type: ignore[arg-type]
            azure_ad_token_provider=token_provider,
            api_version=self.config.api_version,
        )

    def run(self, user_message: str, history: list[dict[str, str]] | None = None) -> AgentResponse:
        """Send ``user_message`` (with optional prior turns) and return the agent's reply."""
        messages = [{"role": "system", "content": self.config.system_prompt}]
        messages.extend(history or [])
        messages.append({"role": "user", "content": user_message})

        completion = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        content = completion.choices[0].message.content
        return AgentResponse(content=content, raw=completion)
