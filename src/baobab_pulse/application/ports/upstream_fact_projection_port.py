"""Port for rebuildable RTD-09 upstream-fact projections."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from baobab_pulse.domain.projections import UpstreamFactProjection


class UpstreamFactProjectionPort(Protocol):
    async def put_if_absent(self, projection: UpstreamFactProjection) -> bool:
        """Persist projection if event occurrence is new.

        Returns True when inserted, False for an idempotent replay of the exact
        same occurrence. Implementations deduplicate by canonical CloudEvents
        (source, id) and must fail closed if that occurrence is replayed with a
        conflicting immutable event digest.
        """
        ...

    async def get(
        self, *, source_event_source: str, source_event_id: UUID
    ) -> UpstreamFactProjection | None:
        """Return one projection by canonical CloudEvents (source, id)."""
        ...
