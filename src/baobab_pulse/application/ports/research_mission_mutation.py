"""Mutation-governance port for canonical ResearchMission creation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from baobab_pulse.domain.research import ResearchMission


@dataclass(frozen=True, slots=True)
class ResearchMissionCreateMutation:
    """Trusted metadata plus candidate aggregate for one CREATE command."""

    tenant_id: str
    actor_subject: str
    actor_client_id: str | None
    context_id: UUID
    idempotency_key: str
    correlation_id: UUID
    request_fingerprint: str
    request_payload: str
    mission: ResearchMission


@dataclass(frozen=True, slots=True)
class ResearchMissionMutationCommit:
    """Persisted mutation result; replayed means no new mutation occurred."""

    mission: ResearchMission
    replayed: bool
    audit_id: UUID
    event_candidate_id: UUID


class ResearchMissionMutationStore(Protocol):
    """Atomically persist mission, idempotency, audit and HELD event candidate."""

    async def commit_create(
        self,
        mutation: ResearchMissionCreateMutation,
    ) -> ResearchMissionMutationCommit: ...


__all__ = [
    "ResearchMissionCreateMutation",
    "ResearchMissionMutationCommit",
    "ResearchMissionMutationStore",
]
