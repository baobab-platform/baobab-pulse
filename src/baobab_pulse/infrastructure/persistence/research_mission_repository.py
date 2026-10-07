"""PostgreSQL persistence for the canonical ResearchMission aggregate."""

from __future__ import annotations

import json

from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.infrastructure.persistence.connection import Database


class PostgresResearchMissionRepository:
    """Durable tenant-scoped ResearchMission repository (P-CAP-04)."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def get(self, entity_id: str) -> ResearchMission | None:
        """Unscoped reads are intentionally unsupported for capability use."""

        raise RuntimeError(
            "ResearchMission reads require get_for_tenant(); unscoped reads are forbidden"
        )

    async def get_for_tenant(
        self,
        entity_id: str,
        *,
        tenant_id: str,
    ) -> ResearchMission | None:
        record = await self._database.pool.fetchrow(
            """
            SELECT payload
            FROM intelligence.research_missions
            WHERE id = $1 AND tenant_id = $2
            """,
            entity_id,
            tenant_id,
        )
        if record is None:
            return None
        return ResearchMission.model_validate(json.loads(record["payload"]))

    async def add(self, entity: ResearchMission) -> None:
        tenant_context = entity.tenant_context
        if tenant_context is None or not tenant_context.tenant_id:
            raise ValueError("durable ResearchMission requires trusted tenant context")

        await self._database.pool.execute(
            """
            INSERT INTO intelligence.research_missions
                (id, tenant_id, status, classification, payload, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
            """,
            entity.id,
            tenant_context.tenant_id,
            entity.status.value,
            entity.classification.value,
            json.dumps(entity.model_dump(mode="json")),
            entity.created_at,
            entity.updated_at,
        )
