"""EventPublisher port — the transactional-outbox write side.

PULSE-016 / item 58: Pulse events are published through a transactional
outbox, not a direct broker call inside a request/analysis handler.
Consumers MUST assume at-least-once delivery (item 59) — handlers on the
*consuming* side are Pulse's own concern to make idempotent; this port only
covers the write ("append this event to the outbox atomically with the state
change that produced it").
"""

from __future__ import annotations

from typing import Protocol

from baobab_pulse.domain.shared.base import DomainEvent


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent, *, event_type: str) -> None:
        """Append ``event`` to the outbox under the given wire event type
        (e.g. ``"com.baobab-platform.pulse.insight.published.v1"`` — see
        ``baobab_pulse.contracts.events`` for the envelope this becomes)."""
        ...
