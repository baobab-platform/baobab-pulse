"""P-CAP-04/05 canonical ResearchMission capability API tests."""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi.testclient import TestClient

from baobab_pulse.api.main import create_app
from baobab_pulse.api.runtime import CapabilityApiRuntime
from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.context_authority import TrustedPlatformContext
from baobab_pulse.application.ports.research_mission_mutation import (
    ResearchMissionCreateMutation,
    ResearchMissionMutationCommit,
)
from baobab_pulse.application.services.evidence_search_capability import (
    EvidenceSearchCapabilityService,
)
from baobab_pulse.application.services.research_mission_manage_capability import (
    ResearchMissionManageCapabilityService,
)
from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.domain.shared.errors import (
    IdempotencyConflictError,
    SemanticRetrievalUnavailable,
)

_TOKEN = "test-workload-token-123456"
_CONTEXT_ID = UUID("22222222-2222-4222-8222-222222222222")
_CORRELATION_ID = UUID("33333333-3333-4333-8333-333333333333")
_IDEMPOTENCY_KEY = "pcap05-create-0001"


class FakeAuthenticator:
    async def authenticate(self, access_token: str) -> AuthenticatedCaller:
        assert access_token == _TOKEN
        return AuthenticatedCaller(subject="wl_test", client_id="pulse-tests")


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

    async def get_for_tenant(
        self,
        entity_id: str,
        *,
        tenant_id: str,
    ) -> ResearchMission | None:
        return self.items.get((tenant_id, entity_id))


class FakeMutationStore:
    def __init__(self, repository: FakeResearchMissionRepository) -> None:
        self.repository = repository
        self.records: dict[tuple[str, str, str], tuple[str, ResearchMission]] = {}
        self.commits: list[ResearchMissionCreateMutation] = []

    async def commit_create(
        self,
        mutation: ResearchMissionCreateMutation,
    ) -> ResearchMissionMutationCommit:
        key = (mutation.tenant_id, mutation.actor_subject, mutation.idempotency_key)
        existing = self.records.get(key)
        if existing is not None:
            fingerprint, mission = existing
            if fingerprint != mutation.request_fingerprint:
                raise IdempotencyConflictError(
                    "Idempotency-Key is already bound to a different CREATE request"
                )
            return self._commit(mutation, mission=mission, replayed=True)

        self.records[key] = (mutation.request_fingerprint, mutation.mission)
        self.commits.append(mutation)
        self.repository.items[(mutation.tenant_id, mutation.mission.id)] = mutation.mission
        return self._commit(mutation, mission=mutation.mission, replayed=False)

    @staticmethod
    def _commit(
        mutation: ResearchMissionCreateMutation,
        *,
        mission: ResearchMission,
        replayed: bool,
    ) -> ResearchMissionMutationCommit:
        scope = f"{mutation.tenant_id}|{mutation.actor_subject}|{mutation.idempotency_key}"
        return ResearchMissionMutationCommit(
            mission=mission,
            replayed=replayed,
            audit_id=uuid5(NAMESPACE_URL, f"audit|{scope}"),
            event_candidate_id=uuid5(NAMESPACE_URL, f"event|{scope}"),
        )


class UnusedEvidenceRetrieval:
    async def search(self, *args: object, **kwargs: object) -> tuple[object, ...]:
        raise SemanticRetrievalUnavailable("not used in ResearchMission tests")


def _runtime(
    tenant_id: str,
    repository: FakeResearchMissionRepository,
    mutation_store: FakeMutationStore,
) -> CapabilityApiRuntime:
    authority = FakeContextAuthority(tenant_id)
    research = ResearchMissionManageCapabilityService(
        context_authority=authority,
        repository=repository,
        mutation_store=mutation_store,
    )
    evidence = EvidenceSearchCapabilityService(
        context_authority=authority,
        retrieval=UnusedEvidenceRetrieval(),  # type: ignore[arg-type]
    )
    return CapabilityApiRuntime(
        authenticator=FakeAuthenticator(),
        evidence_search=evidence,
        research_missions=research,
    )


def _headers(
    *,
    include_idempotency: bool = True,
    idempotency_key: str = _IDEMPOTENCY_KEY,
    **extra: str,
) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {_TOKEN}",
        "X-Baobab-Context-Id": str(_CONTEXT_ID),
        "X-Correlation-Id": str(_CORRELATION_ID),
        **extra,
    }
    if include_idempotency:
        headers["Idempotency-Key"] = idempotency_key
    return headers


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


def _fixtures(
    tenant_id: str = "tn_authoritative",
) -> tuple[CapabilityApiRuntime, FakeResearchMissionRepository, FakeMutationStore]:
    repository = FakeResearchMissionRepository()
    mutation_store = FakeMutationStore(repository)
    return _runtime(tenant_id, repository, mutation_store), repository, mutation_store


def test_create_uses_control_plane_tenant_not_tenant_header() -> None:
    runtime, repository, mutation_store = _fixtures()
    with TestClient(create_app(runtime)) as client:
        response = client.post(
            "/research-missions/manage",
            json=_create_body(),
            headers=_headers(**{"X-Baobab-Tenant-Id": "tn_attacker"}),
        )

    assert response.status_code == 200
    body = response.json()
    stored = repository.items[("tn_authoritative", body["id"])]
    assert stored.tenant_context is not None
    assert stored.tenant_context.tenant_id == "tn_authoritative"
    assert len(mutation_store.commits) == 1
    mutation = mutation_store.commits[0]
    assert mutation.actor_subject == "wl_test"
    assert mutation.actor_client_id == "pulse-tests"
    assert mutation.context_id == _CONTEXT_ID
    assert mutation.correlation_id == _CORRELATION_ID
    assert mutation.idempotency_key == _IDEMPOTENCY_KEY
    assert _TOKEN not in mutation.request_payload


def test_same_idempotency_key_and_request_replays_same_mission() -> None:
    runtime, _, mutation_store = _fixtures()
    with TestClient(create_app(runtime)) as client:
        first = client.post(
            "/research-missions/manage",
            json=_create_body(),
            headers=_headers(),
        )
        second = client.post(
            "/research-missions/manage",
            json=_create_body(),
            headers=_headers(),
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(mutation_store.commits) == 1


def test_same_idempotency_key_with_different_request_is_409() -> None:
    runtime, _, _ = _fixtures()
    with TestClient(create_app(runtime)) as client:
        first = client.post(
            "/research-missions/manage",
            json=_create_body(),
            headers=_headers(),
        )
        conflict = client.post(
            "/research-missions/manage",
            json=_create_body(title="Different research mission"),
            headers=_headers(),
        )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_create_requires_valid_idempotency_key() -> None:
    runtime, _, _ = _fixtures()
    with TestClient(create_app(runtime)) as client:
        missing = client.post(
            "/research-missions/manage",
            json=_create_body(),
            headers=_headers(include_idempotency=False),
        )
        invalid = client.post(
            "/research-missions/manage",
            json=_create_body(),
            headers=_headers(idempotency_key="short"),
        )

    assert missing.status_code == 400
    assert missing.json()["code"] == "CAPABILITY_REQUEST_INVALID"
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "CAPABILITY_REQUEST_INVALID"


def test_get_does_not_require_idempotency_key_and_is_tenant_scoped() -> None:
    runtime_a, repository, mutation_store = _fixtures("tn_a")
    with TestClient(create_app(runtime_a)) as client:
        create = client.post(
            "/research-missions/manage",
            json=_create_body(),
            headers=_headers(),
        )
    mission_id = create.json()["id"]

    with TestClient(create_app(_runtime("tn_a", repository, mutation_store))) as client:
        same_tenant = client.post(
            "/research-missions/manage",
            json={"operation": "GET", "research_mission_id": mission_id},
            headers=_headers(include_idempotency=False),
        )

    with TestClient(create_app(_runtime("tn_b", repository, mutation_store))) as client:
        other_tenant = client.post(
            "/research-missions/manage",
            json={"operation": "GET", "research_mission_id": mission_id},
            headers=_headers(include_idempotency=False),
        )

    assert same_tenant.status_code == 200
    assert other_tenant.status_code == 404
    assert other_tenant.json()["code"] == "RESEARCH_MISSION_NOT_FOUND"


def test_caller_cannot_supply_tenant_id_in_canonical_body() -> None:
    runtime, _, _ = _fixtures()
    with TestClient(create_app(runtime)) as client:
        response = client.post(
            "/research-missions/manage",
            json=_create_body(tenant_id="tn_attacker"),
            headers=_headers(),
        )

    assert response.status_code == 422


def test_tenant_invocation_cannot_create_global_or_restricted_mission() -> None:
    runtime, _, _ = _fixtures()
    with TestClient(create_app(runtime)) as client:
        global_response = client.post(
            "/research-missions/manage",
            json=_create_body(tenant_scope="GLOBAL"),
            headers=_headers(idempotency_key="pcap05-create-global"),
        )
        restricted_response = client.post(
            "/research-missions/manage",
            json=_create_body(classification="RESTRICTED"),
            headers=_headers(idempotency_key="pcap05-create-restricted"),
        )

    assert global_response.status_code == 403
    assert restricted_response.status_code == 403


def test_legacy_unauthenticated_create_route_is_retired() -> None:
    runtime, _, _ = _fixtures()
    with TestClient(create_app(runtime)) as client:
        response = client.post(
            "/research-missions",
            json={
                "title": "legacy bypass",
                "research_question": "should this route still exist?",
                "tenant_id": "tn_attacker",
            },
        )

    assert response.status_code in {404, 405}



def test_invalid_correlation_id_is_rejected_with_replacement_error_correlation() -> None:
    runtime, _, _ = _fixtures()
    with TestClient(create_app(runtime)) as client:
        response = client.post(
            "/research-missions/manage",
            json=_create_body(),
            headers=_headers(**{"X-Correlation-Id": "not-a-uuid"}),
        )

    assert response.status_code == 400
    assert response.json()["code"] == "CAPABILITY_REQUEST_INVALID"
    replacement = UUID(response.headers["X-Correlation-Id"])
    assert response.json()["correlation_id"] == str(replacement)
