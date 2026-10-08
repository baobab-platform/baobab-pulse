"""QdrantEvidenceProjectionStore — implements both write and read Qdrant ports.

    VectorProjectionPort  ─┐
                           ├─► QdrantEvidenceProjectionStore ─► QdrantDocumentStore ─► Qdrant
    SemanticRetrievalPort ─┘

This is the only module in the codebase that imports ``qdrant_client``
(transitively via ``haystack_integrations``) directly. Every public method
takes/returns plain Pulse types (``ProjectionRecord``, ``SemanticCandidate``,
``EvidenceRetrievalQuery``) — a ``qdrant_client`` type, a
``haystack_integrations`` type, or a raw ``haystack.Document`` never crosses
back out of this module.

Tenant/classification filtering is built here, structurally, *before* the
query reaches Qdrant (item 43, 45-46) — never applied as a post-filter on an
unrestricted result set, and never delegated to the model.

Collection naming is configuration-driven (item 25-26): this class never
hard-codes a physical collection name — see :func:`resolve_collection_name`.
Safe reindexing (item 75, blue-green: new collection -> populate -> validate
-> switch -> retire) is achieved *through configuration*, not runtime code:
bump ``Settings.qdrant_evidence_collection_version`` to point a fresh
deployment at a new physical collection, backfill it via the rebuild
workflow, validate, then cut traffic over by deploying with the new version
— this class has no destructive "recreate in place" code path.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from haystack.dataclasses import Document
from haystack.document_stores.types import DuplicatePolicy
from haystack.utils import Secret
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from baobab_pulse.application.ports.embedding_port import EmbeddingPort
from baobab_pulse.application.ports.semantic_retrieval_port import EvidenceRetrievalQuery, SemanticCandidate
from baobab_pulse.application.ports.vector_projection_port import ProjectionCollection, ProjectionRecord
from baobab_pulse.domain.shared.errors import (
    ProjectionRebuildFailed,
    ProjectionWriteFailed,
    SemanticRetrievalUnavailable,
)
from baobab_pulse.security.classification import allowed_classifications

logger = logging.getLogger(__name__)

_PAYLOAD_INDEXES = [
    {"field_name": "meta.tenant_id", "field_schema": "keyword"},
    {"field_name": "meta.classification", "field_schema": "keyword"},
    {"field_name": "meta.evidence_set_id", "field_schema": "keyword"},
    {"field_name": "meta.canonical_object_id", "field_schema": "keyword"},
]


def resolve_collection_name(collection: ProjectionCollection, *, prefix: str, version: str) -> str:
    """The only place a logical collection role becomes a physical Qdrant
    collection name (item 25-26). Never call this from application/domain
    code — it exists so the mapping is auditable in one place."""
    return f"{prefix}-{collection.value}-{version}"


def _document_id(record: ProjectionRecord) -> str:
    # Deterministic on (canonical object, projection schema version): the
    # same canonical Evidence re-projected under the same projection
    # version upserts the same point; bumping projection_version creates a
    # new point instead of silently overwriting under an old assumption.
    return f"{record.canonical_object_id}:{record.projection_version}"


def _to_document(record: ProjectionRecord, embedding: Sequence[float]) -> Document:
    return Document(
        id=_document_id(record),
        content=record.content,
        embedding=list(embedding),
        meta={
            "canonical_object_id": record.canonical_object_id,
            "canonical_object_type": record.canonical_object_type,
            "evidence_set_id": record.evidence_set_id,
            "canonical_version": record.canonical_version,
            "tenant_id": record.tenant_id,
            "context_id": record.context_id,
            "classification": record.classification.value,
            "valid_from": record.valid_from.isoformat() if record.valid_from else None,
            "valid_to": record.valid_to.isoformat() if record.valid_to else None,
            "content_hash": record.content_hash,
            "projection_version": record.projection_version,
            "embedding_model_id": record.embedding_model_id,
            "embedding_model_version": record.embedding_model_version,
            **record.metadata,
        },
    )


class QdrantEvidenceProjectionStore:
    """Implements ``VectorProjectionPort`` and ``SemanticRetrievalPort`` for
    ``ProjectionCollection.EVIDENCE``. One instance owns one physical
    collection/connection."""

    def __init__(
        self,
        embedding_port: EmbeddingPort,
        *,
        collection_name: str,
        url: str | None = None,
        location: str | None = None,
        api_key: str | None = None,
        https: bool | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._embedding_port = embedding_port
        # Normalise "" -> None: an empty-string env var (PULSE_QDRANT_URL=)
        # is how an operator clears a setting in most deployment tooling,
        # but qdrant_client treats "" as "specified" and rejects
        # location+url both being non-None.
        url = url or None
        location = location or None
        self._document_store = QdrantDocumentStore(
            url=url,
            location=location,
            api_key=Secret.from_token(api_key) if api_key else None,
            https=https,
            index=collection_name,
            embedding_dim=embedding_port.dimension(),
            similarity="cosine",
            timeout=int(timeout) if timeout else None,
            recreate_index=False,
            return_embedding=False,
            progress_bar=False,
            payload_fields_to_index=_PAYLOAD_INDEXES,
        )
        self._retriever = QdrantEmbeddingRetriever(document_store=self._document_store)

    # -- VectorProjectionPort -------------------------------------------------

    async def upsert_projection(self, collection: ProjectionCollection, record: ProjectionRecord) -> None:
        await self.upsert_batch(collection, [record])

    async def upsert_batch(self, collection: ProjectionCollection, records: Sequence[ProjectionRecord]) -> None:
        if not records:
            return
        vectors = await self._embedding_port.embed_batch([record.content for record in records])
        try:
            documents = [_to_document(record, vector.values) for record, vector in zip(records, vectors, strict=True)]
            self._document_store.write_documents(documents, policy=DuplicatePolicy.OVERWRITE)
        except Exception as exc:  # noqa: BLE001 -- anti-corruption boundary: translate, never leak
            raise ProjectionWriteFailed(f"failed to upsert {len(records)} evidence projection(s): {exc}") from exc

    async def delete_projection(self, collection: ProjectionCollection, canonical_object_id: str) -> None:
        try:
            existing = self._document_store.filter_documents(
                {"field": "meta.canonical_object_id", "operator": "==", "value": canonical_object_id}
            )
            if existing:
                self._document_store.delete_documents([document.id for document in existing])
        except Exception as exc:  # noqa: BLE001
            raise ProjectionWriteFailed(
                f"failed to delete projection for canonical object {canonical_object_id!r}: {exc}"
            ) from exc

    async def delete_by_source(self, collection: ProjectionCollection, evidence_set_id: str) -> None:
        try:
            existing = self._document_store.filter_documents(
                {"field": "meta.evidence_set_id", "operator": "==", "value": evidence_set_id}
            )
            if existing:
                self._document_store.delete_documents([document.id for document in existing])
        except Exception as exc:  # noqa: BLE001
            raise ProjectionWriteFailed(
                f"failed to delete projections for evidence set {evidence_set_id!r}: {exc}"
            ) from exc

    async def replace_projection(
        self, collection: ProjectionCollection, evidence_set_id: str, records: Sequence[ProjectionRecord]
    ) -> None:
        await self.delete_by_source(collection, evidence_set_id)
        await self.upsert_batch(collection, records)

    async def rebuild_projection(self, collection: ProjectionCollection, records: Sequence[ProjectionRecord]) -> None:
        # Non-destructive by design (see module docstring): populates the
        # collection this instance is already configured for. Reindexing
        # into a *new* physical collection is a configuration change
        # (bump the collection version), not a code path here.
        try:
            await self.upsert_batch(collection, records)
        except ProjectionWriteFailed as exc:
            raise ProjectionRebuildFailed(f"projection rebuild failed after partial progress: {exc}") from exc

    # -- SemanticRetrievalPort -------------------------------------------------

    async def retrieve_evidence(self, query: EvidenceRetrievalQuery) -> tuple[SemanticCandidate, ...]:
        tenant_id = query.tenant_context.tenant_id
        if not tenant_id:
            # Defence in depth: EvidenceRetrievalQuery.tenant_context is a
            # required field, and callers are expected to obtain it via
            # tenancy.context.require_tenant_context() before this point —
            # this branch only guards against a degenerate empty tenant_id
            # slipping through (item 44: fail closed, never an
            # unrestricted query).
            raise SemanticRetrievalUnavailable("semantic evidence retrieval requires a non-empty tenant_id")

        conditions: list[dict[str, object]] = [
            {"field": "meta.tenant_id", "operator": "==", "value": tenant_id},
            {
                "field": "meta.classification",
                "operator": "in",
                "value": [c.value for c in allowed_classifications(query.requester_clearance)],
            },
        ]
        if query.evidence_set_id:
            conditions.append({"field": "meta.evidence_set_id", "operator": "==", "value": query.evidence_set_id})
        filters = {"operator": "AND", "conditions": conditions}

        query_vector = await self._embedding_port.embed_text(query.query_text)
        try:
            result = self._retriever.run(query_embedding=list(query_vector.values), filters=filters, top_k=query.top_k)
        except Exception as exc:  # noqa: BLE001
            raise SemanticRetrievalUnavailable(f"Qdrant evidence retrieval failed: {exc}") from exc

        candidates = []
        for document in result["documents"]:
            meta = document.meta
            candidates.append(
                SemanticCandidate(
                    canonical_object_id=meta["canonical_object_id"],
                    evidence_set_id=meta["evidence_set_id"],
                    canonical_version=int(meta["canonical_version"]),
                    score=document.score if document.score is not None else 0.0,
                )
            )
        return tuple(candidates)

    # -- readiness -------------------------------------------------------------

    async def is_ready(self) -> bool:
        """Cheap connectivity check for ``api.routers.health`` (item 69) —
        mirrors ``infrastructure.persistence.connection.Database.is_ready``.
        Semantic retrieval being unready never fails liveness or PostgreSQL
        readiness (item 36); it is reported as its own, separate signal."""
        try:
            self._document_store.count_documents()
            return True
        except Exception:  # noqa: BLE001 -- readiness probe: any failure means "not ready", never an exception upward
            return False
