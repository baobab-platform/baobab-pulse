"""P-CAP-03 HTTP boundary tests for intelligence.evidence.search."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from baobab_pulse.api import dependencies
from baobab_pulse.api.main import create_app
from baobab_pulse.api.runtime import CapabilityApiRuntime
from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.context_authority import (
    ContextAuthorityUnavailableError,
    ContextNotFoundError,
    TrustedPlatformContext,
)
from baobab_pulse.application.services.evidence_retrieval_service import (
    EvidenceRetrievalService,
    HydratedEvidenceCandidate,
)
from baobab_pulse.application.services.evidence_search_capability import (
    EvidenceSearchCapabilityService,
)
from baobab_pulse.domain.shared.enums import Classification
from baobab_pulse.tenancy.context import require_tenant_context

_TOKEN = "test-workload-token-123456"
_CONTEXT_ID = UUID("11111111-1111-4111-8111-111111111111")

_CACHED_DEPENDENCIES = (
    dependencies.get_settings,
    dependencies.get_database,
    dependencies.get_embedding_port,
    dependencies.get_qdrant_evidence_store,
    dependencies.get_evidence_repository,
    dependencies.get_evidence_retrieval_service,
    dependencies.get_research_mission_repository,
    dependencies.get_research_mission_service,
)


class FakeAuthenticator:
    async def authenticate(self, access_token: str) -> AuthenticatedCaller:
        assert access_token == _TOKEN
        return AuthenticatedCaller(subject="wl_test")


class FakeContextAuthority:
    def __init__(
        self,
        *,
        tenant_id: str = "tn_authoritative",
        error: Exception | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.error = error
        self.last_caller: AuthenticatedCaller | None = None

    async def redeem(
        self,
        *,
        context_id: UUID,
        caller: AuthenticatedCaller,
    ) -> TrustedPlatformContext:
        assert context_id == _CONTEXT_ID
        self.last_caller = caller
        if self.error is not None:
            raise self.error
        return TrustedPlatformContext(
            context_id=context_id,
            tenant_id=self.tenant_id,
            organisation_id="org_test",
        )


class RecordingRetrieval(EvidenceRetrievalService):
    def __init__(self) -> None:
        self.tenant_id: str | None = None
        self.context_id: str | None = None
        self.clearance: Classification | None = None

    async def search(
        self,
        query_text: str,
        *,
        requester_clearance: Classification = Classification.TENANT,
        evidence_set_id: str | None = None,
        top_k: int = 10,
    ) -> tuple[HydratedEvidenceCandidate, ...]:
        del evidence_set_id, top_k
        assert query_text == "coffee exports"
        context = require_tenant_context()
        self.tenant_id = context.tenant_id
        self.context_id = context.context_id
        self.clearance = requester_clearance
        return ()


def _runtime(
    *,
    authority: FakeContextAuthority | None = None,
    retrieval: RecordingRetrieval | None = None,
) -> tuple[CapabilityApiRuntime, RecordingRetrieval]:
    actual_retrieval = retrieval or RecordingRetrieval()
    service = EvidenceSearchCapabilityService(
        context_authority=authority or FakeContextAuthority(),
        retrieval=actual_retrieval,
    )
    return (
        CapabilityApiRuntime(
            authenticator=FakeAuthenticator(),
            evidence_search=service,
        ),
        actual_retrieval,
    )


@pytest.fixture(autouse=True)
def clear_cached_dependencies(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv(
        "PULSE_DATABASE_URL",
        "postgresql://pulse:pulse@localhost:1/baobab_pulse",
    )
    for cached in _CACHED_DEPENDENCIES:
        cached.cache_clear()
    yield
    for cached in _CACHED_DEPENDENCIES:
        cached.cache_clear()


def _headers(**extra: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_TOKEN}",
        "X-Baobab-Context-Id": str(_CONTEXT_ID),
        **extra,
    }


def test_missing_bearer_token_fails_closed() -> None:
    runtime, _ = _runtime()
    with TestClient(create_app(runtime)) as client:
        response = client.post(
            "/evidence/search",
            json={"query_text": "coffee exports"},
            headers={"X-Baobab-Context-Id": str(_CONTEXT_ID)},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_INVALID"


def test_missing_context_id_fails_closed_without_tenant_header_fallback() -> None:
    runtime, _ = _runtime()
    with TestClient(create_app(runtime)) as client:
        response = client.post(
            "/evidence/search",
            json={"query_text": "coffee exports"},
            headers={
                "Authorization": f"Bearer {_TOKEN}",
                "X-Baobab-Tenant-Id": "tn_attacker",
            },
        )

    assert response.status_code == 400
    assert response.json()["code"] == "CAPABILITY_REQUEST_INVALID"


def test_validated_context_is_the_only_tenant_authority() -> None:
    authority = FakeContextAuthority(tenant_id="tn_authoritative")
    runtime, retrieval = _runtime(authority=authority)

    with TestClient(create_app(runtime)) as client:
        response = client.post(
            "/evidence/search",
            json={"query_text": "coffee exports"},
            headers=_headers(**{"X-Baobab-Tenant-Id": "tn_attacker"}),
        )

    assert response.status_code == 200
    assert response.json() == {"candidates": []}
    assert authority.last_caller is not None
    assert authority.last_caller.access_token == _TOKEN
    assert retrieval.tenant_id == "tn_authoritative"
    assert retrieval.context_id == str(_CONTEXT_ID)
    assert retrieval.clearance == Classification.TENANT


def test_caller_cannot_select_classification_clearance() -> None:
    runtime, _ = _runtime()
    with TestClient(create_app(runtime)) as client:
        response = client.post(
            "/evidence/search",
            json={
                "query_text": "coffee exports",
                "requester_clearance": "RESTRICTED",
            },
            headers=_headers(),
        )

    assert response.status_code == 422


def test_context_not_owned_or_expired_is_indistinguishable_not_found() -> None:
    runtime, _ = _runtime(
        authority=FakeContextAuthority(error=ContextNotFoundError("not found"))
    )
    with TestClient(create_app(runtime)) as client:
        response = client.post(
            "/evidence/search",
            json={"query_text": "coffee exports"},
            headers=_headers(),
        )

    assert response.status_code == 404
    assert response.json()["code"] == "CONTEXT_NOT_FOUND"


def test_control_plane_unavailability_is_retryable_503() -> None:
    runtime, _ = _runtime(
        authority=FakeContextAuthority(
            error=ContextAuthorityUnavailableError("cp unavailable")
        )
    )
    with TestClient(create_app(runtime)) as client:
        response = client.post(
            "/evidence/search",
            json={"query_text": "coffee exports"},
            headers=_headers(),
        )

    assert response.status_code == 503
    assert response.json()["code"] == "CAPABILITY_AUTHORITY_UNAVAILABLE"
    assert response.json()["retryable"] is True


def test_unconfigured_capability_runtime_fails_closed() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/evidence/search",
            json={"query_text": "coffee exports"},
            headers=_headers(),
        )

    assert response.status_code == 503
    assert response.json()["code"] == "CAPABILITY_RUNTIME_UNAVAILABLE"
