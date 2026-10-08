"""In-memory reference implementation of RTD-09 projection storage.

Production persistence can replace this adapter without changing the
application service. The store is intentionally rebuildable from authoritative
upstream events and never becomes a source of regulatory/documentary truth.
"""

from __future__ import annotations

from uuid import UUID

from baobab_pulse.domain.projections import UpstreamFactProjection
from baobab_pulse.domain.shared.errors import InvariantViolation


class InMemoryUpstreamFactProjectionStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, UUID], UpstreamFactProjection] = {}

    async def put_if_absent(self, projection: UpstreamFactProjection) -> bool:
        key = projection.dedupe_key
        existing = self._items.get(key)
        if existing is None:
            self._items[key] = projection
            return True

        if existing.event_digest != projection.event_digest:
            raise InvariantViolation(
                "same upstream event occurrence identity replayed with a conflicting event digest"
            )
        return False

    async def get(
        self, *, source_event_source: str, source_event_id: UUID
    ) -> UpstreamFactProjection | None:
        return self._items.get((source_event_source, source_event_id))

    def values(self) -> tuple[UpstreamFactProjection, ...]:
        """Test/reference inspection only; not a canonical domain query API."""

        return tuple(self._items.values())
