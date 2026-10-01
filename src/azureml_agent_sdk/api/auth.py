"""Bearer token auth (P4-04). The secret comes from ``AZUREML_AGENT_API_TOKEN``."""
from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request

TOKEN_ENV = "AZUREML_AGENT_API_TOKEN"


def make_auth_dependency(api_token: str | None):
    """Return a dependency validating the bearer token. Fails closed if no token is set."""

    def require_token(request: Request) -> None:
        expected = api_token if api_token is not None else os.environ.get(TOKEN_ENV, "")
        scheme, _, supplied = request.headers.get("Authorization", "").partition(" ")
        if (
            not expected
            or scheme.lower() != "bearer"
            or not hmac.compare_digest(supplied.encode(), expected.encode())
        ):
            raise HTTPException(
                status_code=401,
                detail="invalid or missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return require_token
