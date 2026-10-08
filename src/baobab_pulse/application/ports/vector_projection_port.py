"""VectorProjectionPort — the write side of Qdrant semantic projections.

Qdrant refactor items 16-17, 27-31: every field here is either a direct
canonical reference (``canonical_object_id``, ``canonical_version``,
``evidence_set_id``) or projection/embedding metadata needed to detect a
stale projection later — never a Qdrant SDK type
(``PointStruct``/``Filter``/... stay entirely inside
``infrastructure.haystack.document_stores.qdrant_projection_store``).

Only the ``evidence`` collection role is implemented (item 24: "use only
those justified by current code" — no other retrieval use case exists yet
in this codebase). ``ProjectionCollection`` is still an enum, not a bare
string, so a second logical collection (e.g. ``documents``, ``research``)
is a one-line addition rather than a call-site string typo waiting to
happen.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from baobab_pulse.domain.shared.enums import Classification


class ProjectionCollection(StrEnum):
    """A logical collection role (item 24) — never a physical Qdrant
    collection name. ``infrastructure.haystack.document_stores
    .qdrant_projection_store.resolve_collection_name`` is the only place a
    logical role becomes a physical, versioned name (item 25-26)."""

    EVIDENCE = "evidence"


class ProjectionRecord(BaseModel):
    """One semantically-searchable projection of one canonical Evidence
    entry, in Pulse's own vocabulary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_object_id: str
    """The canonical ``Evidence.id`` this projection represents."""
    canonical_object_type: str = "evidence"
    evidence_set_id: str
    """The owning ``EvidenceSet.id`` — the grouping/source identifier a
    caller uses to hydrate authoritative context (item 27's
    ``source_id``/``dataset_id`` role, adapted to what this domain
    actually has)."""
    canonical_version: int
    """The owning ``EvidenceSet.version`` at projection time (Evidence
    itself carries no independent version in this domain model — only
    EvidenceSet is a versioned aggregate, AGG-PULSE/CIM §63) — used for
    staleness detection (item 31)."""
    tenant_id: str | None
    context_id: str | None = None
    classification: Classification
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    content: str
    """The resolved text this projection is embedded from. Qdrant is a
    projection of this text, never the source of it (item 27, 61)."""
    content_hash: str
    projection_version: str = "1"
    """Schema/mapping version of the projection itself — distinct from
    ``canonical_version`` (item 30)."""
    embedding_model_id: str
    embedding_model_version: str
    metadata: dict[str, str] = {}


class VectorProjectionPort(Protocol):
    """Implemented today by
    ``infrastructure.haystack.document_stores.qdrant_projection_store.QdrantEvidenceProjectionStore``.
    """

    async def upsert_projection(self, collection: ProjectionCollection, record: ProjectionRecord) -> None: ...

    async def upsert_batch(
        self, collection: ProjectionCollection, records: Sequence[ProjectionRecord]
    ) -> None: ...

    async def delete_projection(self, collection: ProjectionCollection, canonical_object_id: str) -> None: ...

    async def delete_by_source(self, collection: ProjectionCollection, evidence_set_id: str) -> None:
        """Remove every projection derived from one canonical source
        (e.g. an ``EvidenceSet``) — used on classification tightening,
        tenant/rights removal, or before a full re-projection (item 47-48)."""
        ...

    async def replace_projection(
        self, collection: ProjectionCollection, evidence_set_id: str, records: Sequence[ProjectionRecord]
    ) -> None:
        """Atomically-in-intent replace every projection for one source:
        delete-by-source, then upsert the given records."""
        ...

    async def rebuild_projection(
        self, collection: ProjectionCollection, records: Sequence[ProjectionRecord]
    ) -> None:
        """Full-collection rebuild (item 32, 75): populate a fresh physical
        collection from canonical data end to end. Used by the projection
        rebuild workflow, never by request-path code."""
        ...
