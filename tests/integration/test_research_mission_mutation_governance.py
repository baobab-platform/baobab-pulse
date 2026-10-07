"""P-CAP-05 PostgreSQL mutation-governance integration tests."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

import asyncpg
import pytest

from baobab_pulse.application.ports.research_mission_mutation import (
    ResearchMissionCreateMutation,
)
from baobab_pulse.configuration.settings import Settings
from baobab_pulse.contracts.api.research_missions import ResearchMissionCreateRequest
from baobab_pulse.contracts.events import PulseEventEnvelope
from baobab_pulse.contracts.mutations import (
    canonical_create_request_json,
    create_request_fingerprint,
)
from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.domain.shared.enums import Classification, ConfidenceBand, TenantScope
from baobab_pulse.domain.shared.errors import IdempotencyConflictError
from baobab_pulse.domain.shared.value_objects import TenantContext
from baobab_pulse.infrastructure.persistence.connection import Database
from baobab_pulse.infrastructure.persistence.research_mission_mutation import (
    PostgresResearchMissionMutationStore,
)

_TENANT_ID = "tn_pcap05"
_ACTOR = "wl_pcap05"
_CLIENT_ID = "pulse-pcap05-tests"
_CONTEXT_ID = UUID("55555555-5555-4555-8555-555555555555")
_CORRELATION_ID = UUID("66666666-6666-4666-8666-666666666666")
_EVENT_TYPE = "com.baobab-platform.intelligence.research-mission.created.v1"


def _idempotency_value() -> str:
    return "pcap05-" + "integration-" + "0001"


async def _database() -> Database | None:
    database = Database(Settings().database_url)
    try:
        await database.connect()
    except (OSError, asyncpg.PostgresError):
        return None
    if not await database.is_ready():
        await database.disconnect()
        return None
    required = (
        "intelligence.research_missions",
        "intelligence.research_mission_idempotency",
        "intelligence.research_mission_mutation_audit",
        "intelligence.outbox",
    )
    for relation in required:
        if await database.pool.fetchval("SELECT to_regclass($1)", relation) is None:
            await database.disconnect()
            return None
    return database


def _request(*, title: str = "P-CAP-05 concurrent mission") -> ResearchMissionCreateRequest:
    return ResearchMissionCreateRequest(
        operation="CREATE",
        title=title,
        research_question="Does concurrent replay converge on one durable mutation?",
        tenant_scope=TenantScope.TENANT,
        classification=Classification.TENANT,
        confidence_requirement=ConfidenceBand.MODERATE,
    )


def _mutation(index: int, request: ResearchMissionCreateRequest) -> ResearchMissionCreateMutation:
    mission = ResearchMission(
        id=f"rms_{index:032x}",
        title=request.title,
        research_question=request.research_question,
        tenant_scope=request.tenant_scope,
        tenant_context=TenantContext(
            tenant_id=_TENANT_ID,
            context_id=str(_CONTEXT_ID),
            organisation_id="org_pcap05",
        ),
        classification=request.classification,
        confidence_requirement=request.confidence_requirement,
    )
    return ResearchMissionCreateMutation(
        tenant_id=_TENANT_ID,
        actor_subject=_ACTOR,
        actor_client_id=_CLIENT_ID,
        context_id=_CONTEXT_ID,
        idempotency_key=_idempotency_value(),
        correlation_id=_CORRELATION_ID,
        request_fingerprint=create_request_fingerprint(request),
        request_payload=canonical_create_request_json(request),
        mission=mission,
    )


async def _cleanup(database: Database) -> None:
    await database.pool.execute(
        "DELETE FROM intelligence.outbox WHERE tenant_id = $1 AND idempotency_key = $2",
        _TENANT_ID,
        _idempotency_value(),
    )
    await database.pool.execute(
        """
        DELETE FROM intelligence.research_mission_mutation_audit
        WHERE tenant_id = $1 AND actor_subject = $2 AND idempotency_key = $3
        """,
        _TENANT_ID,
        _ACTOR,
        _idempotency_value(),
    )
    await database.pool.execute(
        """
        DELETE FROM intelligence.research_mission_idempotency
        WHERE tenant_id = $1 AND actor_subject = $2 AND idempotency_key = $3
        """,
        _TENANT_ID,
        _ACTOR,
        _idempotency_value(),
    )
    await database.pool.execute(
        "DELETE FROM intelligence.research_missions WHERE tenant_id = $1",
        _TENANT_ID,
    )


async def test_concurrent_duplicate_create_converges_on_one_atomic_mutation() -> None:
    database = await _database()
    if database is None:
        pytest.skip("no live migrated PostgreSQL reachable — see PULSE_DATABASE_URL")

    store = PostgresResearchMissionMutationStore(database)
    request = _request()
    await _cleanup(database)
    try:
        commits = await asyncio.gather(
            *(store.commit_create(_mutation(index, request)) for index in range(1, 6))
        )

        mission_ids = {commit.mission.id for commit in commits}
        assert len(mission_ids) == 1
        assert sum(not commit.replayed for commit in commits) == 1
        assert sum(commit.replayed for commit in commits) == 4

        mission_id = next(iter(mission_ids))
        counts = {
            "missions": await database.pool.fetchval(
                "SELECT count(*) FROM intelligence.research_missions WHERE id = $1",
                mission_id,
            ),
            "idempotency": await database.pool.fetchval(
                """
                SELECT count(*) FROM intelligence.research_mission_idempotency
                WHERE tenant_id = $1 AND actor_subject = $2 AND idempotency_key = $3
                """,
                _TENANT_ID, _ACTOR, _idempotency_value(),
            ),
            "audit": await database.pool.fetchval(
                """
                SELECT count(*) FROM intelligence.research_mission_mutation_audit
                WHERE tenant_id = $1 AND actor_subject = $2 AND idempotency_key = $3
                """,
                _TENANT_ID, _ACTOR, _idempotency_value(),
            ),
            "outbox": await database.pool.fetchval(
                """
                SELECT count(*) FROM intelligence.outbox
                WHERE tenant_id = $1 AND actor_subject = $2
                  AND idempotency_key = $3 AND event_type = $4
                """,
                _TENANT_ID, _ACTOR, _idempotency_value(), _EVENT_TYPE,
            ),
        }
        assert counts == {"missions": 1, "idempotency": 1, "audit": 1, "outbox": 1}

        audit = await database.pool.fetchrow(
            """
            SELECT actor_subject, actor_client_id, context_id, correlation_id,
                   request_fingerprint, result_fingerprint
            FROM intelligence.research_mission_mutation_audit
            WHERE tenant_id = $1 AND actor_subject = $2 AND idempotency_key = $3
            """,
            _TENANT_ID, _ACTOR, _idempotency_value(),
        )
        assert audit is not None
        assert audit["actor_subject"] == _ACTOR
        assert audit["actor_client_id"] == _CLIENT_ID
        assert audit["context_id"] == _CONTEXT_ID
        assert audit["correlation_id"] == _CORRELATION_ID

        outbox = await database.pool.fetchrow(
            """
            SELECT envelope, publication_status, delivered_at, envelope_fingerprint
            FROM intelligence.outbox
            WHERE tenant_id = $1 AND actor_subject = $2
              AND idempotency_key = $3 AND event_type = $4
            """,
            _TENANT_ID, _ACTOR, _idempotency_value(), _EVENT_TYPE,
        )
        assert outbox is not None
        assert outbox["publication_status"] == "HELD_UNREGISTERED"
        assert outbox["delivered_at"] is None
        raw_envelope = outbox["envelope"]
        envelope = PulseEventEnvelope.model_validate(
            json.loads(raw_envelope) if isinstance(raw_envelope, str) else dict(raw_envelope)
        )
        assert envelope.type == _EVENT_TYPE
        assert envelope.tenantid == _TENANT_ID
        assert envelope.subject == mission_id
        assert envelope.idempotencykey == _idempotency_value()
        assert envelope.correlationid == _CORRELATION_ID
        assert envelope.dataschema.startswith("urn:baobab-platform:unregistered-schema:")

        with pytest.raises(IdempotencyConflictError):
            await store.commit_create(_mutation(99, _request(title="different request")))

        assert await database.pool.fetchval(
            """
            SELECT count(*) FROM intelligence.research_missions
            WHERE tenant_id = $1
              AND payload->>'title' = $2
            """,
            _TENANT_ID,
            request.title,
        ) == 1
    finally:
        await _cleanup(database)
        await database.disconnect()
