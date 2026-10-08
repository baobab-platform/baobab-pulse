"""Qdrant unavailability is a degraded-semantic-retrieval failure, never a
platform-down failure (Qdrant refactor item 8, 35-37): a connection refused
against an unreachable Qdrant endpoint SHALL surface as one of Pulse's own
typed errors, never a raw ``qdrant_client``/``httpx`` exception, and SHALL
never touch or require PostgreSQL. ``http://localhost:1`` is not a valid
listening port, so failure is immediate and deterministic — no live network
access or long timeout is needed to prove this.
"""

from __future__ import annotations

import pytest

from baobab_pulse.application.ports.semantic_retrieval_port import EvidenceRetrievalQuery
from baobab_pulse.application.ports.vector_projection_port import ProjectionCollection, ProjectionRecord
from baobab_pulse.domain.shared.enums import Classification
from baobab_pulse.domain.shared.errors import (
    ProjectionWriteFailed,
    SemanticRetrievalUnavailable,
    VectorStoreUnavailable,
)
from baobab_pulse.domain.shared.value_objects import TenantContext
from baobab_pulse.infrastructure.haystack.document_stores.qdrant_projection_store import (
    QdrantEvidenceProjectionStore,
)
from baobab_pulse.infrastructure.haystack.embedders.embedding_adapter import (
    HaystackEmbeddingAdapter,
    build_document_embedder,
    build_text_embedder,
)

_UNREACHABLE_URL = "http://localhost:1"


def _unreachable_store() -> QdrantEvidenceProjectionStore:
    embedding_port = HaystackEmbeddingAdapter(
        text_embedder=build_text_embedder("mock", dimension=8),
        document_embedder=build_document_embedder("mock", dimension=8),
        model_id="mock:test",
        model_version="1",
    )
    return QdrantEvidenceProjectionStore(
        embedding_port, collection_name="unreachable", url=_UNREACHABLE_URL, timeout=1
    )


def _record() -> ProjectionRecord:
    return ProjectionRecord(
        canonical_object_id="evd_1",
        evidence_set_id="evs_1",
        canonical_version=1,
        tenant_id="tn_a",
        classification=Classification.TENANT,
        content="content",
        content_hash="hash",
        embedding_model_id="mock:test",
        embedding_model_version="1",
    )


async def test_upsert_against_an_unreachable_qdrant_raises_projection_write_failed() -> None:
    store = _unreachable_store()
    with pytest.raises(ProjectionWriteFailed):
        await store.upsert_projection(ProjectionCollection.EVIDENCE, _record())


async def test_retrieve_against_an_unreachable_qdrant_raises_semantic_retrieval_unavailable() -> None:
    store = _unreachable_store()
    query = EvidenceRetrievalQuery(query_text="anything", tenant_context=TenantContext(tenant_id="tn_a"))
    with pytest.raises(SemanticRetrievalUnavailable):
        await store.retrieve_evidence(query)


async def test_semantic_retrieval_unavailable_is_a_vector_store_unavailable() -> None:
    # Callers that only handle the broader VectorStoreUnavailable category
    # (item 36) still catch a semantic-retrieval-specific failure.
    assert issubclass(SemanticRetrievalUnavailable, VectorStoreUnavailable)


async def test_is_ready_reports_false_rather_than_raising_when_qdrant_is_unreachable() -> None:
    store = _unreachable_store()
    assert await store.is_ready() is False


async def test_delete_against_an_unreachable_qdrant_raises_projection_write_failed() -> None:
    store = _unreachable_store()
    with pytest.raises(ProjectionWriteFailed):
        await store.delete_projection(ProjectionCollection.EVIDENCE, "evd_1")
