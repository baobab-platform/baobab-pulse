"""Port for rebuildable RTD-09 upstream-fact projections."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from baobab_pulse.domain.projections import UpstreamFactProjection


class UpstreamFactProjectionPort(Protocol):
    async def put_if_absent(self, projection: UpstreamFactProjection) -> bool:
        """Persist projection if event occurrence is new.

        Returns True when inserted, False for an idempotent replay of the exact
        same occurrence/payload. Implementations must fail closed if the same
        occurrence identity is replayed with a conflicting payload digest.
        """
        ...

    async def get(
        self, *, source_engine_id: str, source_event_id: UUID
    ) -> UpstreamFactProjection | None:
        """Return one projection by canonical (source engine, event id)."""
        ...
