"""P-CAP-04 canonical ResearchMission capability API tests."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from baobab_pulse.api.main import create_app
from baobab_pulse.api.runtime import CapabilityApiRuntime
from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.context_authority import TrustedPlatformContext
from baobab_pulse.application.services.evidence_search_capability import (
    EvidenceSearchCapabilityService,
)
from baobab_pulse.application.services.research_mission_manage_capability import (
    ResearchMissionManageCapabilityService,
)
from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.domain.shared.errors import SemanticRetrievalUnavailable

_TOKEN = "test-workload-token-123456"
_CONTEXT_ID = UUID("22222222-2222-4222-8222-222222222222")


class FakeAuthenticator:
    async def authenticate(self, access_token: str) -> AuthenticatedCaller:
        assert access_token == _TOKEN
        return AuthenticatedCaller(subject="wl_test")


class FakeContextAuthority:
    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id

    async def redeem(
        self,
        *,
        context_id: UUID,
        caller: AuthenticatedCaller,
    ) -> TrustedPlatformContext:
        assert context_id == _CONTEXT_ID
        assert caller.subject == "wl_test"
        return TrustedPlatformContext(
            context_id=context_id,
            tenant_id=self.tenant_id,
            organisation_id="org_test",
        )


class FakeResearchMissionRepository:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], ResearchMission] = {}

    async def add(self, entity: ResearchMission) -> None:
        assert entity.tenant_context is not None
        tenant_id = entity.tenant_context.tenant_id
        self.items[(tenant_id, entity.id)] = entity

    async def get_for_tenant(
        self,
        entity_id: str,
        *,
        tenant_id: str,
    ) -> ResearchMission | None:
        return self.items.get((tenant_id, entity_id))


class UnusedEvidenceRetrieval:
    async def search(self, *args: object, **kwargs: object) -> tuple[object, ...]:
        raise SemanticRetrievalUnavailable("not used in ResearchMission tests")


def _runtime(
    tenant_id: str,
    repository: FakeResearchMissionRepository,
) -> CapabilityApiRuntime:
    authority = FakeContextAuthority(tenant_id)
    research = ResearchMissionManageCapabilityService(
        context_authority=authority,
        repository=repository,
    )
    # Evidence search is a required P-CAP-03 runtime member. It is not invoked
    # in these tests, so the concrete retrieval dependency deliberately fails
    # if a route unexpectedly crosses the capability boundary.
    evidence = EvidenceSearchCapabilityService(
        context_authority=authority,
        retrieval=UnusedEvidenceRetrieval(),  # type: ignore[arg-type]
    )
    return CapabilityApiRuntime(
        authenticator=FakeAuthenticator(),
        evidence_search=evidence,
        research_missions=research,
    )


def _headers(**extra: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_TOKEN}",
        "X-Baobab-Context-Id": str(_CONTEXT_ID),
        **extra,
    }


def _create_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "operation": "CREATE",
        "title": "Uganda coffee corridor research",
        "research_question": "What changed in the corridor?",
        "tenant_scope": "TENANT",
        "classification": "TENANT",
        "confidence_requirement": "MODERATE",
    }
    body.update(overrides)
    return body


def test_create_uses_control_plane_tenant_not_tenant_header() -> None:
    repository = FakeResearchMissionRepository()
    with TestClient(create_app(_runtime("tn_authoritative", repository))) as client:
        response = client.post(
            "/research-missions/manage",
            json=_create_body(),
            headers=_headers(**{"X-Baobab-Tenant-Id": "tn_attacker"}),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PROPOSED"
    assert body["confidence_requirement"] == "MODERATE"

    stored = repository.items[("tn_authoritative", body["id"])]
    assert stored.tenant_context is not None
    assert stored.tenant_context.tenant_id == "tn_authoritative"
    assert ("tn_attacker", body["id"]) not in repository.items


def test_get_is_structurally_tenant_scoped() -> None:
    repository = FakeResearchMissionRepository()

    with TestClient(create_app(_runtime("tn_a", repository))) as client:
        create = client.post(
            "/research-missions/manage",
            json=_create_body(),
            headers=_headers(),
        )
    mission_id = create.json()["id"]

    with TestClient(create_app(_runtime("tn_a", repository))) as client:
        same_tenant = client.post(
            "/research-missions/manage",
            json={"operation": "GET", "research_mission_id": mission_id},
            headers=_headers(),
        )

    with TestClient(create_app(_runtime("tn_b", repository))) as client:
        other_tenant = client.post(
            "/research-missions/manage",
            json={"operation": "GET", "research_mission_id": mission_id},
            headers=_headers(),
        )

    assert same_tenant.status_code == 200
    assert same_tenant.json()["id"] == mission_id
    assert other_tenant.status_code == 404
    assert other_tenant.json()["code"] == "RESEARCH_MISSION_NOT_FOUND"


def test_caller_cannot_supply_tenant_id_in_canonical_body() -> None:
    repository = FakeResearchMissionRepository()
    with TestClient(create_app(_runtime("tn_authoritative", repository))) as client:
        response = client.post(
            "/research-missions/manage",
            json=_create_body(tenant_id="tn_attacker"),
            headers=_headers(),
        )

    assert response.status_code == 422


def test_tenant_invocation_cannot_create_global_or_restricted_mission() -> None:
    repository = FakeResearchMissionRepository()
    with TestClient(create_app(_runtime("tn_authoritative", repository))) as client:
        global_response = client.post(
            "/research-missions/manage",
            json=_create_body(tenant_scope="GLOBAL"),
            headers=_headers(),
        )
        restricted_response = client.post(
            "/research-missions/manage",
            json=_create_body(classification="RESTRICTED"),
            headers=_headers(),
        )

    assert global_response.status_code == 403
    assert global_response.json()["code"] == "CAPABILITY_ACCESS_DENIED"
    assert restricted_response.status_code == 403
    assert restricted_response.json()["code"] == "CAPABILITY_ACCESS_DENIED"


def test_legacy_unauthenticated_create_route_is_retired() -> None:
    repository = FakeResearchMissionRepository()
    with TestClient(create_app(_runtime("tn_authoritative", repository))) as client:
        response = client.post(
            "/research-missions",
            json={
                "title": "legacy bypass",
                "research_question": "should this route still exist?",
                "tenant_id": "tn_attacker",
            },
        )

    assert response.status_code in {404, 405}
