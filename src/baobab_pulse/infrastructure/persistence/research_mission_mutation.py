"""PostgreSQL atomic mutation-governance store for ResearchMission CREATE."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import asyncpg
from pydantic import ValidationError

from baobab_pulse.application.ports.research_mission_mutation import (
    ResearchMissionCreateMutation,
    ResearchMissionMutationCommit,
)
from baobab_pulse.contracts.events import PulseEventEnvelope
from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.domain.shared.errors import (
    IdempotencyConflictError,
    MutationIntegrityError,
    MutationPersistenceUnavailableError,
)
from baobab_pulse.infrastructure.persistence.connection import Database

_CAPABILITY_KEY = "intelligence.research-mission.manage"
_EVENT_TYPE = "com.baobab-platform.intelligence.research-mission.created.v1"
_SOURCE = "urn:baobab-platform:service:baobab-pulse"
_HELD_DATASCHEMA = (
    "urn:baobab-platform:unregistered-schema:intelligence:research-mission.created:v1"
)


class PostgresResearchMissionMutationStore:
    """Atomically commit mission, idempotency, audit and HELD event candidate."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def commit_create(
        self,
        mutation: ResearchMissionCreateMutation,
    ) -> ResearchMissionMutationCommit:
        mission_json = self._canonical_json(mutation.mission.model_dump(mode="json"))
        result_fingerprint = self._sha256(mission_json)
        audit_id = self._stable_uuid("audit", mutation)
        event_candidate_id = self._stable_uuid("event", mutation)
        envelope = self._event_candidate(
            mutation=mutation,
            event_candidate_id=event_candidate_id,
        )
        envelope_json = envelope.to_wire_json()
        envelope_fingerprint = self._sha256(envelope_json)

        try:
            async with self._database.pool.acquire() as connection, connection.transaction():
                idempotency_row = await connection.fetchrow(
                    """
                    INSERT INTO intelligence.research_mission_idempotency (
                        tenant_id, actor_subject, capability_key, idempotency_key,
                        request_fingerprint, request_payload, mission_id, result_fingerprint,
                        context_id, correlation_id
                    ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10)
                    ON CONFLICT DO NOTHING
                    RETURNING mission_id, request_fingerprint, request_payload, result_fingerprint
                    """,
                    mutation.tenant_id,
                    mutation.actor_subject,
                    _CAPABILITY_KEY,
                    mutation.idempotency_key,
                    mutation.request_fingerprint,
                    mutation.request_payload,
                    mutation.mission.id,
                    result_fingerprint,
                    mutation.context_id,
                    mutation.correlation_id,
                )

                if idempotency_row is not None:
                    await connection.execute(
                        """
                        INSERT INTO intelligence.research_missions
                            (id, tenant_id, status, classification, payload, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                        """,
                        mutation.mission.id,
                        mutation.tenant_id,
                        mutation.mission.status.value,
                        mutation.mission.classification.value,
                        mission_json,
                        mutation.mission.created_at,
                        mutation.mission.updated_at,
                    )
                    await connection.execute(
                        """
                        INSERT INTO intelligence.research_mission_mutation_audit (
                            audit_id, mission_id, tenant_id, actor_subject, actor_client_id,
                            context_id, capability_key, operation, idempotency_key,
                            request_fingerprint, result_fingerprint, correlation_id, occurred_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'CREATE', $8, $9, $10, $11, $12)
                        """,
                        audit_id,
                        mutation.mission.id,
                        mutation.tenant_id,
                        mutation.actor_subject,
                        mutation.actor_client_id,
                        mutation.context_id,
                        _CAPABILITY_KEY,
                        mutation.idempotency_key,
                        mutation.request_fingerprint,
                        result_fingerprint,
                        mutation.correlation_id,
                        mutation.mission.created_at,
                    )
                    await connection.execute(
                        """
                        INSERT INTO intelligence.outbox (
                            id, event_type, envelope, tenant_id, actor_subject, subject_id,
                            correlation_id, idempotency_key, envelope_fingerprint, publication_status
                        ) VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8, $9, 'HELD_UNREGISTERED')
                        """,
                        event_candidate_id,
                        _EVENT_TYPE,
                        envelope_json,
                        mutation.tenant_id,
                        mutation.actor_subject,
                        mutation.mission.id,
                        mutation.correlation_id,
                        mutation.idempotency_key,
                        envelope_fingerprint,
                    )
                    return ResearchMissionMutationCommit(
                        mission=mutation.mission,
                        replayed=False,
                        audit_id=audit_id,
                        event_candidate_id=event_candidate_id,
                    )

                existing = await connection.fetchrow(
                    """
                    SELECT mission_id, request_fingerprint, request_payload, result_fingerprint
                    FROM intelligence.research_mission_idempotency
                    WHERE tenant_id = $1
                      AND actor_subject = $2
                      AND capability_key = $3
                      AND idempotency_key = $4
                    """,
                    mutation.tenant_id,
                    mutation.actor_subject,
                    _CAPABILITY_KEY,
                    mutation.idempotency_key,
                )
                if existing is None:
                    raise MutationIntegrityError(
                        "idempotency conflict occurred but no durable record can be read"
                    )
                mission_row = await connection.fetchrow(
                    """
                    SELECT payload
                    FROM intelligence.research_missions
                    WHERE id = $1 AND tenant_id = $2
                    """,
                    str(existing["mission_id"]),
                    mutation.tenant_id,
                )
                audit_row = await connection.fetchrow(
                    """
                    SELECT audit_id
                    FROM intelligence.research_mission_mutation_audit
                    WHERE tenant_id = $1
                      AND actor_subject = $2
                      AND capability_key = $3
                      AND idempotency_key = $4
                    """,
                    mutation.tenant_id,
                    mutation.actor_subject,
                    _CAPABILITY_KEY,
                    mutation.idempotency_key,
                )
                outbox_row = await connection.fetchrow(
                    """
                    SELECT id, envelope, envelope_fingerprint, publication_status
                    FROM intelligence.outbox
                    WHERE tenant_id = $1
                      AND actor_subject = $2
                      AND idempotency_key = $3
                      AND event_type = $4
                    """,
                    mutation.tenant_id,
                    mutation.actor_subject,
                    mutation.idempotency_key,
                    _EVENT_TYPE,
                )
        except IdempotencyConflictError:
            raise
        except MutationIntegrityError:
            raise
        except (
            asyncpg.UniqueViolationError,
            asyncpg.CheckViolationError,
            asyncpg.ForeignKeyViolationError,
            asyncpg.DataError,
        ) as exc:
            raise MutationIntegrityError(
                "ResearchMission mutation violates durable-store invariants"
            ) from exc
        except (asyncpg.PostgresError, asyncpg.InterfaceError, OSError) as exc:
            raise MutationPersistenceUnavailableError(
                "ResearchMission mutation-governance store is unavailable"
            ) from exc

        return self._validate_replay(
            mutation=mutation,
            idempotency_row=existing,
            mission_row=mission_row,
            audit_row=audit_row,
            outbox_row=outbox_row,
        )

    def _validate_replay(
        self,
        *,
        mutation: ResearchMissionCreateMutation,
        idempotency_row: Mapping[str, Any],
        mission_row: Mapping[str, Any] | None,
        audit_row: Mapping[str, Any] | None,
        outbox_row: Mapping[str, Any] | None,
    ) -> ResearchMissionMutationCommit:
        if str(idempotency_row["request_fingerprint"]) != mutation.request_fingerprint:
            raise IdempotencyConflictError(
                "Idempotency-Key is already bound to a different CREATE request"
            )
        stored_request_payload = self._json_object(idempotency_row["request_payload"])
        if self._sha256(self._canonical_json(stored_request_payload)) != mutation.request_fingerprint:
            raise MutationIntegrityError(
                "persisted idempotency request payload does not match its fingerprint"
            )
        if mission_row is None or audit_row is None or outbox_row is None:
            raise MutationIntegrityError(
                "committed idempotent mutation is missing mission, audit or held outbox state"
            )
        try:
            mission = ResearchMission.model_validate(self._json_object(mission_row["payload"]))
        except (TypeError, ValueError, ValidationError) as exc:
            raise MutationIntegrityError("persisted ResearchMission payload is invalid") from exc

        mission_json = self._canonical_json(mission.model_dump(mode="json"))
        if self._sha256(mission_json) != str(idempotency_row["result_fingerprint"]):
            raise MutationIntegrityError(
                "persisted ResearchMission result does not match its fingerprint"
            )
        if mission.id != str(idempotency_row["mission_id"]):
            raise MutationIntegrityError(
                "persisted idempotency mission identity diverges from canonical payload"
            )

        publication_status = str(outbox_row["publication_status"])
        if publication_status != "HELD_UNREGISTERED":
            raise MutationIntegrityError(
                "unregistered Intelligence event candidate is not HELD_UNREGISTERED"
            )
        envelope = self._validate_envelope(
            outbox_row["envelope"],
            expected_tenant_id=mutation.tenant_id,
            expected_subject=mission.id,
            expected_idempotency_key=mutation.idempotency_key,
        )
        envelope_json = envelope.to_wire_json()
        if self._sha256(envelope_json) != str(outbox_row["envelope_fingerprint"]):
            raise MutationIntegrityError(
                "persisted held event candidate does not match its fingerprint"
            )

        return ResearchMissionMutationCommit(
            mission=mission,
            replayed=True,
            audit_id=UUID(str(audit_row["audit_id"])),
            event_candidate_id=UUID(str(outbox_row["id"])),
        )

    @staticmethod
    def _event_candidate(
        *,
        mutation: ResearchMissionCreateMutation,
        event_candidate_id: UUID,
    ) -> PulseEventEnvelope:
        mission = mutation.mission
        return PulseEventEnvelope(
            id=event_candidate_id,
            type=_EVENT_TYPE,
            source=_SOURCE,
            subject=mission.id,
            time=mission.created_at,
            dataschema=_HELD_DATASCHEMA,
            baobabscope="tenant",
            correlationid=mutation.correlation_id,
            tenantid=mutation.tenant_id,
            idempotencykey=mutation.idempotency_key,
            data={
                "research_mission_id": mission.id,
                "status": mission.status.value,
                "tenant_scope": mission.tenant_scope.value,
                "classification": mission.classification.value,
            },
        )

    @classmethod
    def _validate_envelope(
        cls,
        value: Any,
        *,
        expected_tenant_id: str,
        expected_subject: str,
        expected_idempotency_key: str,
    ) -> PulseEventEnvelope:
        try:
            envelope = PulseEventEnvelope.model_validate(cls._json_object(value))
        except (TypeError, ValueError, ValidationError) as exc:
            raise MutationIntegrityError("persisted held event candidate is invalid") from exc
        if envelope.type != _EVENT_TYPE:
            raise MutationIntegrityError("held event candidate type diverges from P-CAP-05 semantics")
        if envelope.tenantid != expected_tenant_id:
            raise MutationIntegrityError("held event candidate tenant diverges from mutation")
        if envelope.subject != expected_subject:
            raise MutationIntegrityError("held event candidate subject diverges from mission")
        if envelope.idempotencykey != expected_idempotency_key:
            raise MutationIntegrityError("held event candidate idempotency key diverges from mutation")
        if envelope.dataschema != _HELD_DATASCHEMA:
            raise MutationIntegrityError("held event candidate must use the unregistered schema URN")
        return envelope

    @staticmethod
    def _stable_uuid(kind: str, mutation: ResearchMissionCreateMutation) -> UUID:
        scope = (
            f"{_SOURCE}|{kind}|{mutation.tenant_id}|{mutation.actor_subject}|"
            f"{mutation.idempotency_key}"
        )
        return uuid5(NAMESPACE_URL, scope)

    @staticmethod
    def _canonical_json(value: Mapping[str, Any] | dict[str, Any]) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _sha256(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _json_object(value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            parsed = json.loads(value)
        elif isinstance(value, bytes):
            parsed = json.loads(value.decode("utf-8"))
        elif isinstance(value, Mapping):
            parsed = dict(value)
        else:
            raise TypeError("persisted JSONB value is not an object")
        if not isinstance(parsed, dict):
            raise TypeError("persisted JSONB value is not an object")
        return parsed


__all__ = ["PostgresResearchMissionMutationStore"]
