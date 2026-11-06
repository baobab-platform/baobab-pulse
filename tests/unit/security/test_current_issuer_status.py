"""N03 Pulse native PEP source-only regression; no real issuer/CP acceptance."""
from __future__ import annotations

import asyncio
import io
import json
import time
import urllib.error
from unittest.mock import Mock

import pytest

from baobab_pulse.application.ports.authentication import (
    AuthenticatedCaller,
    WorkloadAuthenticationError,
    WorkloadAuthenticationUnavailableError,
)
from baobab_pulse.infrastructure.authentication.current_issuer_status import (
    CurrentIssuerStatusWorkloadAuthenticator,
)

ISSUER = "https://iam.example.invalid"
AUDIENCE = "baobab-pulse"
TOKEN = "source-only-mock-token-not-a-real-issuer-bearer"
CLIENT = "synthetic-pulse-consumer"
SCOPE = "intelligence:evidence:search"


class SignedFixture:
    def __init__(self, *, client_id: str | None = CLIENT, deny: bool = False):
        self.client_id = client_id
        self.deny = deny
        self.calls = 0

    async def authenticate(self, token: str) -> AuthenticatedCaller:
        self.calls += 1
        if self.deny:
            raise WorkloadAuthenticationError("source-only signature fixture refused")
        return AuthenticatedCaller(
            subject=CLIENT, access_token=token,
            client_id=self.client_id,
            scopes=frozenset({SCOPE}),
        )


def n03(signed=None) -> CurrentIssuerStatusWorkloadAuthenticator:
    return CurrentIssuerStatusWorkloadAuthenticator(
        signed=signed or SignedFixture(),
        issuer=ISSUER, audience=AUDIENCE,
        introspection_url=ISSUER + "/oauth2/introspect",
        introspection_client_id="distinct-native-issuer-observer",
        introspection_client_secret="s" * 48,
    )


def active() -> dict:
    return {
        "active": True, "iss": ISSUER, "sub": CLIENT,
        "client_id": CLIENT, "aud": [AUDIENCE], "scope": SCOPE,
        "exp": int(time.time()) + 90,
    }


def test_current_status_positive_still_unattested() -> None:
    signed = SignedFixture()
    verifier = n03(signed)
    seen: list[str] = []
    def status(token):
        seen.append(token)
        return active()
    verifier._status = status  # source-only issuer substitute
    assert asyncio.run(verifier.authenticate(TOKEN)).client_id == CLIENT
    assert asyncio.run(verifier.authenticate(TOKEN)).client_id == CLIENT
    assert seen == [TOKEN, TOKEN]  # no status caching or fallback
    assert signed.calls == 2


@pytest.mark.parametrize("key,value", [
    ("active", False), ("active", 1),
    ("iss", "https://imposter.invalid"), ("sub", "other-client"),
    ("client_id", "different-client"), ("aud", ["baobab-control-plane"]),
    ("aud", [AUDIENCE, "baobab-control-plane"]),
    ("scope", SCOPE + " context:validate"),
    ("scope", ""), ("exp", True), ("exp", 0),
])
def test_issuer_revocation_binding_and_scope_negatives(key: str, value: object) -> None:
    verifier = n03()
    result = active()
    result[key] = value
    verifier._status = lambda token: result
    with pytest.raises(WorkloadAuthenticationError):
        asyncio.run(verifier.authenticate(TOKEN))


def test_signature_denial_has_no_issuer_fallback() -> None:
    verifier = n03(SignedFixture(deny=True))
    probe = Mock()
    verifier._status = probe
    with pytest.raises(WorkloadAuthenticationError):
        asyncio.run(verifier.authenticate(TOKEN))
    probe.assert_not_called()


def test_missing_signed_client_vetoes_before_introspection() -> None:
    verifier = n03(SignedFixture(client_id=None))
    probe = Mock()
    verifier._status = probe
    with pytest.raises(WorkloadAuthenticationError):
        asyncio.run(verifier.authenticate(TOKEN))
    probe.assert_not_called()


@pytest.mark.parametrize("error", [
    urllib.error.URLError("unavailable"), TimeoutError(), ValueError(),
])
def test_issuer_unknown_outcome_refuses_without_jwks_only_fallback(error: Exception) -> None:
    verifier = n03()
    def unavailable(token: str):
        raise error
    verifier._status = unavailable
    with pytest.raises(WorkloadAuthenticationUnavailableError):
        asyncio.run(verifier.authenticate(TOKEN))


@pytest.mark.parametrize("url", [
    "http://iam.example.invalid/oauth2/introspect",
    "https://evil.invalid/oauth2/introspect",
    "https://iam.example.invalid/redirected",
    "https://iam.example.invalid/oauth2/introspect?query=1",
    "https://user:secret@iam.example.invalid/oauth2/introspect",
])
def test_untrusted_status_destination_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        CurrentIssuerStatusWorkloadAuthenticator(
            signed=SignedFixture(), issuer=ISSUER, audience=AUDIENCE,
            introspection_url=url, introspection_client_id="observer",
            introspection_client_secret="s" * 32,
        )


def test_transport_uses_distinct_basic_auth_no_redirect_and_bounded_json() -> None:
    verifier = n03()
    class Reply(io.BytesIO):
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.close()
    observed: dict = {}
    class Opener:
        def open(self, request, *, timeout):
            observed["url"] = request.full_url
            observed["method"] = request.get_method()
            observed["form"] = request.data.decode("utf-8")
            observed["authorization"] = request.get_header("Authorization")
            observed["timeout"] = timeout
            return Reply(json.dumps(active()).encode())
    verifier._opener = Opener()
    assert verifier._status(TOKEN)["active"] is True
    assert observed["method"] == "POST"
    assert observed["url"] == ISSUER + "/oauth2/introspect"
    assert observed["authorization"].startswith("Basic ")
    assert "token=" in observed["form"] and "token_type_hint=access_token" in observed["form"]
    assert observed["timeout"] <= 10
    verifier._opener = Mock()
    verifier._opener.open.return_value = Reply(b'{"active":true,"active":false}')
    with pytest.raises(ValueError):
        verifier._status(TOKEN)
