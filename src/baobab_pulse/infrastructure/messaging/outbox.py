"""The transactional outbox (implements ``EventPublisher``).

Item 58: design persistence boundaries to support a transactional outbox
without prematurely implementing an enterprise broker (item 58, 114: no
Kafka until a real contract requires it). ``InMemoryOutbox`` remains the
legacy/reference publisher adapter. P-CAP-05 adds durable PostgreSQL outbox
candidates for ResearchMission CREATE, but those rows are explicitly
``HELD_UNREGISTERED`` because Shared still reserves the Intelligence event
context without activating a producer event. No relay may publish them.

Every event this outbox accepts is wrapped in a
``contracts.events.PulseEventEnvelope`` before being appended — a
``DomainEvent`` never reaches a consumer in its in-process shape.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

from baobab_pulse.contracts.events import PulseEventEnvelope
from baobab_pulse.domain.shared.base import DomainEvent

_HELD_UNREGISTERED_EVENT_TYPES = {
    "com.baobab-platform.intelligence.research-mission.created.v1",
}


class InMemoryOutbox:
    def __init__(self, *, source: str = "urn:baobab-platform:service:baobab-pulse") -> None:
        self._source = source
        self.entries: list[PulseEventEnvelope] = []

    async def publish(self, event: DomainEvent, *, event_type: str) -> None:
        if event_type in _HELD_UNREGISTERED_EVENT_TYPES:
            raise ValueError(
                f"{event_type} is HELD_UNREGISTERED and has no Shared publication authority"
            )
        baobabscope: Literal["tenant", "platform"] = "tenant" if event.tenant_id else "platform"
        envelope = PulseEventEnvelope(
            id=uuid4(),
            type=event_type,
            source=self._source,
            subject=event.subject_id,
            time=event.occurred_at,
            dataschema=self._dataschema_for(event_type),
            baobabscope=baobabscope,
            correlationid=_as_uuid(event.correlation_id),
            causationid=_as_uuid(event.causation_id) if event.causation_id else None,
            tenantid=event.tenant_id,
            data=event.payload,
        )
        self.entries.append(envelope)

    @staticmethod
    def _dataschema_for(event_type: str) -> str:
        entity_verb_version = event_type.removeprefix("com.baobab-platform.intelligence.")
        return f"https://contracts.baobab-platform.com/intelligence/events/v1/{entity_verb_version}.schema.json"


def _as_uuid(value: str | None) -> UUID:
    return UUID(value) if value else uuid4()
