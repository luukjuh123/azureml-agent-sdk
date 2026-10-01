"""Tests for the unified credential manager (P1-07)."""

from __future__ import annotations

import pytest

from azureml_agent_sdk.credentials import CredentialManager, MissingCredentialError


class TestGetCredential:
    def test_uses_injected_factory_and_never_touches_default_azure_credential(self):
        calls = []

        def fake_factory():
            calls.append(1)
            return "fake-credential"

        manager = CredentialManager(credential_factory=fake_factory)
        credential = manager.get_credential()

        assert credential == "fake-credential"
        assert len(calls) == 1

    def test_caches_credential_across_calls(self):
        calls = []

        def fake_factory():
            calls.append(1)
            return object()

        manager = CredentialManager(credential_factory=fake_factory)
        first = manager.get_credential()
        second = manager.get_credential()

        assert first is second
        assert len(calls) == 1


class TestGetEnv:
    def test_returns_value_when_set(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
        assert (
            CredentialManager.get_env("AZURE_OPENAI_ENDPOINT") == "https://example.openai.azure.com"
        )

    def test_returns_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("SOME_UNSET_VAR", raising=False)
        assert CredentialManager.get_env("SOME_UNSET_VAR", default="fallback") == "fallback"

    def test_raises_when_required_and_missing(self, monkeypatch):
        monkeypatch.delenv("SOME_REQUIRED_VAR", raising=False)
        with pytest.raises(MissingCredentialError):
            CredentialManager.get_env("SOME_REQUIRED_VAR", required=True)


class TestMaskSecret:
    def test_masks_middle_of_long_secret(self):
        masked = CredentialManager.mask_secret("sk-abcdefghijklmnop")
        assert masked.startswith("sk")
        assert masked.endswith("op")
        assert "abcdefghijklmn" not in masked

    def test_masks_short_secret_entirely(self):
        assert CredentialManager.mask_secret("abcd") == "****"

    def test_empty_secret_returns_empty_string(self):
        assert CredentialManager.mask_secret("") == ""
        assert CredentialManager.mask_secret(None) == ""

    def test_never_returns_the_original_value(self):
        secret = "super-secret-api-key-value"
        assert CredentialManager.mask_secret(secret) != secret
