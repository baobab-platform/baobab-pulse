"""PostgresEvidenceSetRepository — canonical persistence for EvidenceSet.

Implements ``application.ports.repositories.Repository[EvidenceSet]``
(``EvidenceSetRepository``). This is the "PostgreSQL = canonical
operational truth" half of the Qdrant refactor's required relationship
(item 6, 28-29): a Qdrant projection's ``canonical_object_id`` /
``canonical_version`` are only ever resolved back to something authoritative
by reading *this* table, never by trusting whatever Qdrant happens to have
cached.

Deliberately one JSONB payload column, not a normalised schema — see
``migrations/0002_evidence.sql`` for why that is a proportionate, not a
lazy, choice for this refactor's scope.
"""

from __future__ import annotations

import json

from baobab_pulse.domain.evidence import EvidenceSet
from baobab_pulse.infrastructure.persistence.connection import Database


class PostgresEvidenceSetRepository:
    """Implements ``application.ports.repositories.Repository[EvidenceSet]``,
    plus the ``*_with_text`` variants the Qdrant refactor's hydration path
    needs (Evidence itself carries no text — see
    ``application.ports.vector_projection_port.ProjectionRecord``'s
    docstring — so the canonical repository is what a caller resolves text
    from, never Qdrant's cached payload copy)."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def get(self, entity_id: str) -> EvidenceSet | None:
        hydrated = await self.get_with_text(entity_id)
        return hydrated[0] if hydrated is not None else None

    async def get_with_text(self, entity_id: str) -> tuple[EvidenceSet, dict[str, str]] | None:
        record = await self._database.pool.fetchrow(
            "SELECT payload, evidence_text FROM evidence.evidence_sets WHERE id = $1", entity_id
        )
        if record is None:
            return None
        evidence_set = EvidenceSet.model_validate(json.loads(record["payload"]))
        evidence_text: dict[str, str] = json.loads(record["evidence_text"])
        return evidence_set, evidence_text

    async def add(self, entity: EvidenceSet) -> None:
        await self.add_with_text(entity, {})

    async def add_with_text(self, entity: EvidenceSet, evidence_text: dict[str, str]) -> None:
        """Upsert-by-id: this repository keeps the *latest* canonical
        version only (full revision history is out of scope for this
        refactor, same as every other aggregate in this codebase today)."""
        tenant_id = entity.tenant_context.tenant_id if entity.tenant_context else None
        await self._database.pool.execute(
            """
            INSERT INTO evidence.evidence_sets
                (id, tenant_id, classification, canonical_version, payload, evidence_text, updated_at)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, now())
            ON CONFLICT (id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                classification = EXCLUDED.classification,
                canonical_version = EXCLUDED.canonical_version,
                payload = EXCLUDED.payload,
                evidence_text = EXCLUDED.evidence_text,
                updated_at = now()
            """,
            entity.id,
            tenant_id,
            entity.classification.value,
            entity.version,
            json.dumps(entity.model_dump(mode="json")),
            json.dumps(evidence_text),
        )

    async def current_version(self, entity_id: str) -> int | None:
        """Cheap staleness check (item 31) — reads one integer column
        rather than deserialising the full payload just to compare
        ``canonical_version``."""
        record = await self._database.pool.fetchrow(
            "SELECT canonical_version FROM evidence.evidence_sets WHERE id = $1", entity_id
        )
        return int(record["canonical_version"]) if record is not None else None
