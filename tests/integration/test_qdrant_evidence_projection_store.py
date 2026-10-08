"""End-to-end proof that Qdrant semantic retrieval actually works (Qdrant
refactor items 2, 5, 42-46, 74).

Uses Qdrant's embedded, in-process mode (``location=":memory:"``) — a real
``qdrant_client``/``QdrantDocumentStore``/``QdrantEmbeddingRetriever`` stack,
just with no server process — so this exercises the genuine Haystack ->
Qdrant retrieval path (not a hand-rolled fake) while staying credential-free
and requiring no live service, same principle as
``tests/integration/test_haystack_reference_pipeline.py``'s ``MockChatGenerator``.

Each ``_store()`` call gets a fresh, empty embedded collection (verified: a
new ``QdrantDocumentStore(location=":memory:")`` instance never sees another
instance's points, even under the same collection name), so tests need no
manual cleanup between them.
"""

from __future__ import annotations

import hashlib

from baobab_pulse.application.ports.semantic_retrieval_port import EvidenceRetrievalQuery
from baobab_pulse.application.ports.vector_projection_port import ProjectionCollection, ProjectionRecord
from baobab_pulse.domain.shared.enums import Classification
from baobab_pulse.domain.shared.value_objects import TenantContext
from baobab_pulse.infrastructure.haystack.document_stores.qdrant_projection_store import (
    QdrantEvidenceProjectionStore,
)
from baobab_pulse.infrastructure.haystack.embedders.embedding_adapter import (
    HaystackEmbeddingAdapter,
    build_document_embedder,
    build_text_embedder,
)

_DIMENSION = 16


def _store() -> QdrantEvidenceProjectionStore:
    embedding_port = HaystackEmbeddingAdapter(
        text_embedder=build_text_embedder("mock", dimension=_DIMENSION),
        document_embedder=build_document_embedder("mock", dimension=_DIMENSION),
        model_id="mock:test",
        model_version="1",
    )
    return QdrantEvidenceProjectionStore(
        embedding_port, collection_name="test-evidence", location=":memory:"
    )


def _record(
    *,
    canonical_object_id: str = "evd_1",
    evidence_set_id: str = "evs_1",
    tenant_id: str | None = "tn_a",
    classification: Classification = Classification.TENANT,
    content: str = "Ugandan coffee exports to South Africa rose 18% year-on-year.",
    canonical_version: int = 1,
) -> ProjectionRecord:
    return ProjectionRecord(
        canonical_object_id=canonical_object_id,
        evidence_set_id=evidence_set_id,
        canonical_version=canonical_version,
        tenant_id=tenant_id,
        classification=classification,
        content=content,
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        embedding_model_id="mock:test",
        embedding_model_version="1",
    )


def _query(
    *, tenant_id: str = "tn_a", requester_clearance: Classification = Classification.TENANT, query_text: str
) -> EvidenceRetrievalQuery:
    return EvidenceRetrievalQuery(
        query_text=query_text, tenant_context=TenantContext(tenant_id=tenant_id), requester_clearance=requester_clearance
    )


async def test_upsert_then_retrieve_finds_the_projection_by_exact_content_match() -> None:
    store = _store()
    record = _record()
    await store.upsert_projection(ProjectionCollection.EVIDENCE, record)

    candidates = await store.retrieve_evidence(_query(query_text=record.content))

    assert len(candidates) == 1
    assert candidates[0].canonical_object_id == "evd_1"
    assert candidates[0].evidence_set_id == "evs_1"
    assert candidates[0].canonical_version == 1
    # Identical content -> identical mock embedding -> maximal cosine similarity.
    assert candidates[0].score > 0.99


async def test_tenant_isolation_a_different_tenant_never_sees_the_projection() -> None:
    store = _store()
    await store.upsert_projection(ProjectionCollection.EVIDENCE, _record(tenant_id="tn_a"))

    candidates = await store.retrieve_evidence(
        _query(tenant_id="tn_b", query_text="Ugandan coffee exports to South Africa rose 18% year-on-year.")
    )

    assert candidates == ()


async def test_classification_isolation_insufficient_clearance_never_sees_the_projection() -> None:
    store = _store()
    await store.upsert_projection(
        ProjectionCollection.EVIDENCE, _record(classification=Classification.CONFIDENTIAL)
    )

    candidates = await store.retrieve_evidence(
        _query(
            requester_clearance=Classification.TENANT,
            query_text="Ugandan coffee exports to South Africa rose 18% year-on-year.",
        )
    )

    assert candidates == ()


async def test_classification_isolation_sufficient_clearance_sees_the_projection() -> None:
    store = _store()
    await store.upsert_projection(
        ProjectionCollection.EVIDENCE, _record(classification=Classification.CONFIDENTIAL)
    )

    candidates = await store.retrieve_evidence(
        _query(
            requester_clearance=Classification.RESTRICTED,
            query_text="Ugandan coffee exports to South Africa rose 18% year-on-year.",
        )
    )

    assert len(candidates) == 1


async def test_public_clearance_cannot_retrieve_confidential_evidence() -> None:
    store = _store()
    await store.upsert_projection(
        ProjectionCollection.EVIDENCE, _record(classification=Classification.CONFIDENTIAL)
    )

    candidates = await store.retrieve_evidence(
        _query(
            requester_clearance=Classification.PUBLIC,
            query_text="Ugandan coffee exports to South Africa rose 18% year-on-year.",
        )
    )

    assert candidates == ()


async def test_evidence_set_id_narrows_the_search() -> None:
    store = _store()
    await store.upsert_projection(
        ProjectionCollection.EVIDENCE, _record(canonical_object_id="evd_1", evidence_set_id="evs_1")
    )
    await store.upsert_projection(
        ProjectionCollection.EVIDENCE, _record(canonical_object_id="evd_2", evidence_set_id="evs_2")
    )

    query = _query(query_text="Ugandan coffee exports to South Africa rose 18% year-on-year.")
    query = query.model_copy(update={"evidence_set_id": "evs_2"})

    candidates = await store.retrieve_evidence(query)

    assert [c.canonical_object_id for c in candidates] == ["evd_2"]


async def test_delete_projection_removes_only_the_named_canonical_object() -> None:
    store = _store()
    await store.upsert_projection(
        ProjectionCollection.EVIDENCE, _record(canonical_object_id="evd_1", content="alpha content")
    )
    await store.upsert_projection(
        ProjectionCollection.EVIDENCE, _record(canonical_object_id="evd_2", content="beta content")
    )

    await store.delete_projection(ProjectionCollection.EVIDENCE, "evd_1")

    survivors = await store.retrieve_evidence(_query(query_text="content"))
    assert [c.canonical_object_id for c in survivors] == ["evd_2"]


async def test_delete_by_source_removes_every_projection_from_that_evidence_set() -> None:
    store = _store()
    await store.upsert_batch(
        ProjectionCollection.EVIDENCE,
        [
            _record(canonical_object_id="evd_1", evidence_set_id="evs_1", content="alpha content"),
            _record(canonical_object_id="evd_2", evidence_set_id="evs_1", content="beta content"),
            _record(canonical_object_id="evd_3", evidence_set_id="evs_2", content="gamma content"),
        ],
    )

    await store.delete_by_source(ProjectionCollection.EVIDENCE, "evs_1")

    query = _query(query_text="gamma content").model_copy(update={"top_k": 10})
    survivors = await store.retrieve_evidence(query)
    assert [c.canonical_object_id for c in survivors] == ["evd_3"]


async def test_replace_projection_swaps_out_stale_points_for_one_source() -> None:
    store = _store()
    await store.upsert_projection(
        ProjectionCollection.EVIDENCE,
        _record(canonical_object_id="evd_old", evidence_set_id="evs_1", content="old content", canonical_version=1),
    )

    await store.replace_projection(
        ProjectionCollection.EVIDENCE,
        "evs_1",
        [_record(canonical_object_id="evd_new", evidence_set_id="evs_1", content="new content", canonical_version=2)],
    )

    survivors = await store.retrieve_evidence(_query(query_text="content"))
    assert [c.canonical_object_id for c in survivors] == ["evd_new"]
    assert survivors[0].canonical_version == 2


async def test_is_ready_reports_true_for_a_working_store() -> None:
    store = _store()
    assert await store.is_ready() is True
