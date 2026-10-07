"""P-CAP-07 production authority adapter and composition tests."""

from __future__ import annotations

import json
import time
import urllib.error
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.exceptions import PyJWKClientConnectionError

from baobab_pulse.api import composition
from baobab_pulse.application.ports.authentication import (
    AuthenticatedCaller,
    WorkloadAuthenticationError,
    WorkloadAuthenticationUnavailableError,
)
from baobab_pulse.application.ports.context_authority import (
    ContextAccessDeniedError,
    ContextAuthenticationError,
    ContextAuthorityUnavailableError,
    ContextNotFoundError,
)
from baobab_pulse.configuration.settings import Environment, Settings
from baobab_pulse.infrastructure.authentication.oidc_jwks import (
    OidcJwksWorkloadAuthenticator,
)
from baobab_pulse.infrastructure.control_plane import context_authority as context_module
from baobab_pulse.infrastructure.control_plane.context_authority import (
    ClientCredentialsTokenProvider,
    HttpControlPlaneContextAuthority,
)

_ISSUER = "https://iam.example.test/realms/baobab"
_AUDIENCE = "baobab-pulse"
_CONTEXT_ID = UUID("77777777-7777-4777-8777-777777777777")
_SUBJECT_TOKEN = "subject-token-that-must-never-be-logged-123456"
_VALIDATOR_TOKEN = "validator-token-for-control-plane-123456789"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()


class _StaticJwks:
    def get_signing_key_from_jwt(self, _: str) -> SimpleNamespace:
        return SimpleNamespace(key=_PUBLIC_KEY)


class _UnavailableJwks:
    def get_signing_key_from_jwt(self, _: str) -> SimpleNamespace:
        raise PyJWKClientConnectionError("jwks unavailable")


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._raw


class _StaticValidatorTokens:
    async def access_token(self) -> str:
        return _VALIDATOR_TOKEN


def _token(**overrides: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": _ISSUER,
        "sub": "service-account-caller",
        "aud": _AUDIENCE,
        "azp": "trade-caller",
        "actor_type": "workload",
        "scope": "intelligence:evidence:search",
        "iat": now - 5,
        "exp": now + 300,
        "jti": "pcap07-test-token",
        "tenant_id": "tn_claim_only",
    }
    claims.update(overrides)
    return jwt.encode(
        claims,
        _PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": "pcap07-test-key"},
    )


def _authenticator() -> OidcJwksWorkloadAuthenticator:
    authenticator = OidcJwksWorkloadAuthenticator(
        issuer=_ISSUER,
        jwks_url="https://iam.example.test/jwks",
        audience=_AUDIENCE,
        algorithms=("RS256",),
        max_token_lifetime_seconds=900,
    )
    authenticator._jwks = _StaticJwks()  # type: ignore[assignment]
    return authenticator


async def test_oidc_authenticator_verifies_canonical_workload_claims() -> None:
    caller = await _authenticator().authenticate(
        _token(
            scope=(
                "intelligence:evidence:search "
                "intelligence:restricted"
            )
        )
    )

    assert caller.subject == "service-account-caller"
    assert caller.client_id == "trade-caller"
    assert caller.tenant_id == "tn_claim_only"
    assert caller.scopes == frozenset(
        {
            "intelligence:evidence:search",
            "intelligence:restricted",
        }
    )


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "baobab-control-plane"},
        {"actor_type": "human"},
        {"exp": int(time.time()) + 3600},
    ],
)
async def test_oidc_authenticator_fails_closed_on_invalid_authority(
    claims: dict[str, object],
) -> None:
    with pytest.raises(WorkloadAuthenticationError):
        await _authenticator().authenticate(_token(**claims))


async def test_oidc_authenticator_distinguishes_jwks_unavailability() -> None:
    authenticator = OidcJwksWorkloadAuthenticator(
        issuer=_ISSUER,
        jwks_url="https://iam.example.test/jwks",
        audience=_AUDIENCE,
    )
    authenticator._jwks = _UnavailableJwks()  # type: ignore[assignment]

    with pytest.raises(WorkloadAuthenticationUnavailableError):
        await authenticator.authenticate(_token())


async def test_validator_token_provider_caches_short_lived_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    def fake_urlopen(request: object, *, timeout: float) -> _Response:
        calls.append((request, timeout))
        return _Response(
            {
                "access_token": _VALIDATOR_TOKEN,
                "token_type": "Bearer",
                "expires_in": 300,
                "scope": "context:validate",
            }
        )

    monkeypatch.setattr(context_module.urllib.request, "urlopen", fake_urlopen)
    provider = ClientCredentialsTokenProvider(
        token_url="https://iam.example.test/token",
        client_id="baobab-pulse-workload",
        client_secret="test-secret",
        timeout_seconds=2.0,
    )

    assert await provider.access_token() == _VALIDATOR_TOKEN
    assert await provider.access_token() == _VALIDATOR_TOKEN
    assert len(calls) == 1


async def test_context_authority_sends_actual_subject_token_only_in_post_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, *, timeout: float) -> _Response:
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response(
            {
                "context_id": str(_CONTEXT_ID),
                "tenant_id": "tn_authoritative",
                "resolved_at": datetime.now(UTC).isoformat(),
                "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
                "organisation_id": "org_authoritative",
                "market_id": "mkt_za",
            }
        )

    monkeypatch.setattr(context_module.urllib.request, "urlopen", fake_urlopen)
    authority = HttpControlPlaneContextAuthority(
        validation_url="https://cp.example.test/v1/platform-context/validate",
        validator_tokens=_StaticValidatorTokens(),  # type: ignore[arg-type]
        timeout_seconds=2.0,
    )
    caller = AuthenticatedCaller(
        subject="service-account-caller",
        access_token=_SUBJECT_TOKEN,
        scopes=frozenset({"intelligence:evidence:search"}),
    )

    trusted = await authority.redeem(context_id=_CONTEXT_ID, caller=caller)

    request = captured["request"]
    assert hasattr(request, "data")
    body = json.loads(request.data.decode("utf-8"))
    assert body == {
        "context_id": str(_CONTEXT_ID),
        "subject_token": _SUBJECT_TOKEN,
    }
    assert request.get_header("Authorization") == f"Bearer {_VALIDATOR_TOKEN}"
    assert _SUBJECT_TOKEN not in str(request.headers)
    assert trusted.tenant_id == "tn_authoritative"
    assert trusted.organisation_id == "org_authoritative"
    assert trusted.market_id == "mkt_za"


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, ContextAuthenticationError),
        (403, ContextAccessDeniedError),
        (404, ContextNotFoundError),
        (500, ContextAuthorityUnavailableError),
        (503, ContextAuthorityUnavailableError),
    ],
)
async def test_context_authority_maps_failures_without_subject_token_leakage(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    error_type: type[Exception],
) -> None:
    def fail_urlopen(request: object, *, timeout: float) -> _Response:
        del request, timeout
        raise urllib.error.HTTPError(
            "https://cp.example.test/v1/platform-context/validate",
            status,
            f"failure containing {_SUBJECT_TOKEN}",
            None,
            None,
        )

    monkeypatch.setattr(context_module.urllib.request, "urlopen", fail_urlopen)
    authority = HttpControlPlaneContextAuthority(
        validation_url="https://cp.example.test/v1/platform-context/validate",
        validator_tokens=_StaticValidatorTokens(),  # type: ignore[arg-type]
    )
    caller = AuthenticatedCaller(
        subject="service-account-caller",
        access_token=_SUBJECT_TOKEN,
    )

    with pytest.raises(error_type) as captured:
        await authority.redeem(context_id=_CONTEXT_ID, caller=caller)

    assert _SUBJECT_TOKEN not in str(captured.value)


def test_production_composition_fails_closed_without_authority_configuration() -> None:
    settings = Settings(
        _env_file=None,
        environment=Environment.PRODUCTION,
        iam_issuer_url=None,
        iam_jwks_url=None,
        iam_token_url=None,
        iam_client_secret=None,
        control_plane_context_validation_url=None,
    )

    with pytest.raises(RuntimeError, match="production Pulse requires"):
        composition.build_capability_runtime(settings)


def test_production_composition_builds_real_authority_adapters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        _env_file=None,
        environment=Environment.PRODUCTION,
        iam_issuer_url=_ISSUER,
        iam_jwks_url="https://iam.example.test/jwks",
        iam_token_url="https://iam.example.test/token",
        iam_client_secret="test-secret",
        control_plane_context_validation_url=(
            "https://cp.example.test/v1/platform-context/validate"
        ),
    )
    monkeypatch.setattr(composition, "get_evidence_retrieval_service", object)
    monkeypatch.setattr(composition, "get_research_mission_repository", object)
    monkeypatch.setattr(composition, "get_research_mission_mutation_store", object)

    runtime = composition.build_capability_runtime(settings)

    assert runtime is not None
    assert isinstance(runtime.authenticator, OidcJwksWorkloadAuthenticator)
    assert runtime.research_missions is not None
    assert runtime.evidence_search is not None
