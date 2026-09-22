"""Unified credential management: DefaultAzureCredential + env-var fallback (P1-07).

Never logs secret values. ``CredentialManager`` accepts an injectable
``credential_factory`` so tests never need to construct a real
``DefaultAzureCredential`` or touch the network.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any


class MissingCredentialError(RuntimeError):
    """Raised when a required credential or environment variable is missing."""


class CredentialManager:
    """Resolves Azure credentials and environment-backed configuration values."""

    def __init__(self, credential_factory: Callable[[], Any] | None = None) -> None:
        self._credential_factory = credential_factory
        self._credential: Any | None = None

    def get_credential(self) -> Any:
        """Return a cached credential, building it lazily on first use."""
        if self._credential is None:
            if self._credential_factory is not None:
                self._credential = self._credential_factory()
            else:
                from azure.identity import DefaultAzureCredential

                self._credential = DefaultAzureCredential()
        return self._credential

    @staticmethod
    def get_env(name: str, default: str | None = None, *, required: bool = False) -> str | None:
        """Read an environment variable, optionally requiring it to be set."""
        value = os.environ.get(name, default)
        if required and not value:
            raise MissingCredentialError(f"required environment variable {name!r} is not set")
        return value

    @staticmethod
    def mask_secret(value: str | None) -> str:
        """Mask a secret value for safe logging, keeping only a short prefix/suffix."""
        if not value:
            return ""
        if len(value) <= 4:
            return "*" * len(value)
        return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
