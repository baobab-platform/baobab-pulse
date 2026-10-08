"""Full canonical-write -> project -> search -> hydrate round trip across
real PostgreSQL and embedded Qdrant (Qdrant refactor items 2, 6, 8, 28-31,
35-36, 105-108) — the "Final Architecture Verification" scenario from the
refactor brief, concretely:

    Evidence E123 canonically stored in PostgreSQL (tenant T1, CONFIDENTIAL,
    canonical_version=N) is projected into Qdrant; a search authorised for
    T1/CONFIDENTIAL finds it and resolves it back to the *same* canonical
    PostgreSQL row (never trusting Qdrant's own cached payload); a search
    for tenant T2 finds nothing; and once PostgreSQL's canonical_version
    advances, the old projection is flagged stale rather than treated as
    authoritative.

Requires a real, reachable PostgreSQL (``PULSE_DATABASE_URL`` or the
default local dev connection string) with migrations applied — skips
gracefully, rather than failing, when neither is available, so this test
never blocks a contributor or CI job running without a live database.
Qdrant itself stays embedded/in-process (``:memory:``); no Qdrant server is
required for this test.
"""

from __future__ import annotations

import hashlib

import asyncpg
import pytest

from baobab_pulse.application.ports.vector_projection_port import ProjectionCollection, ProjectionRecord
from baobab_pulse.application.services.evidence_retrieval_service import EvidenceRetrievalService
from baobab_pulse.configuration.settings import Settings
from baobab_pulse.domain.evidence import Evidence, EvidenceSet
from baobab_pulse.domain.shared.enums import Classification, EvidenceDirection, TenantScope
from baobab_pulse.domain.shared.errors import ProjectionWriteFailed, SemanticRetrievalUnavailable
from baobab_pulse.domain.shared.value_objects import Reference, TenantContext
from baobab_pulse.infrastructure.haystack.document_stores.qdrant_projection_store import (
    QdrantEvidenceProjectionStore,
)
from baobab_pulse.infrastructure.haystack.embedders.embedding_adapter import (
    HaystackEmbeddingAdapter,
    build_document_embedder,
    build_text_embedder,
)
from baobab_pulse.infrastructure.persistence.connection import Database
from baobab_pulse.infrastructure.persistence.evidence_repository import PostgresEvidenceSetRepository
from baobab_pulse.tenancy.context import bind_tenant_context

_DIMENSION = 16


async def _database() -> Database | None:
    settings = Settings()
    database = Database(settings.database_url)
    try:
        await database.connect()
    except (OSError, asyncpg.PostgresError):
        return None
    if not await database.is_ready():
        await database.disconnect()
        return None
    try:
        await database.pool.fetchval("SELECT to_regclass('evidence.evidence_sets')")
    except asyncpg.PostgresError:
        await database.disconnect()
        return None
    return database


def _store() -> QdrantEvidenceProjectionStore:
    embedding_port = HaystackEmbeddingAdapter(
        text_embedder=build_text_embedder("mock", dimension=_DIMENSION),
        document_embedder=build_document_embedder("mock", dimension=_DIMENSION),
        model_id="mock:test",
        model_version="1",
    )
    return QdrantEvidenceProjectionStore(
        embedding_port, collection_name="test-evidence-roundtrip", location=":memory:"
    )


def _evidence_set(*, evidence_id: str, tenant_id: str, classification: Classification, version: int) -> EvidenceSet:
    return EvidenceSet(
        id="evs_e123",
        purpose="opportunity research",
        tenant_scope=TenantScope.TENANT,
        tenant_context=TenantContext(tenant_id=tenant_id),
        classification=classification,
        version=version,
        entries=(
            Evidence(
                id=evidence_id,
                referenced_object=Reference(object_type="observation", object_id="obs_export_volume"),
                direction=EvidenceDirection.SUPPORTS,
            ),
        ),
    )


async def test_canonical_write_project_search_and_hydrate_round_trip() -> None:
    database = await _database()
    if database is None:
        pytest.skip("no live, migrated PostgreSQL reachable — see PULSE_DATABASE_URL")

    try:
        repository = PostgresEvidenceSetRepository(database)
        store = _store()
        service = EvidenceRetrievalService(semantic_retrieval=store, hydration=repository)

        content = "Ugandan coffee exports to South Africa rose 18% year-on-year in Q2."
        evidence_set = _evidence_set(
            evidence_id="evd_e123", tenant_id="tn_t1", classification=Classification.CONFIDENTIAL, version=7
        )
        await repository.add_with_text(evidence_set, {"evd_e123": content})

        await store.upsert_projection(
            ProjectionCollection.EVIDENCE,
            ProjectionRecord(
                canonical_object_id="evd_e123",
                evidence_set_id=evidence_set.id,
                canonical_version=7,
                tenant_id="tn_t1",
                classification=Classification.CONFIDENTIAL,
                content=content,
                content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                embedding_model_id="mock:test",
                embedding_model_version="1",
            ),
        )

        # Tenant T1, cleared for CONFIDENTIAL, finds and can hydrate it.
        with bind_tenant_context(TenantContext(tenant_id="tn_t1")):
            results = await service.search(content, requester_clearance=Classification.CONFIDENTIAL)
        assert len(results) == 1
        assert results[0].canonical_object_id == "evd_e123"
        assert results[0].is_stale is False

        hydrated_set, hydrated_text = await service.hydrate_for_pipeline(results)
        assert hydrated_set.id == evidence_set.id
        assert hydrated_set.version == 7
        assert hydrated_text == {"evd_e123": content}

        # Tenant T2 must never retrieve tenant T1's projection.
        with bind_tenant_context(TenantContext(tenant_id="tn_t2")):
            other_tenant_results = await service.search(content, requester_clearance=Classification.CONFIDENTIAL)
        assert other_tenant_results == ()

        # PostgreSQL advances to canonical_version=8; the Qdrant point still
        # says 7 — Pulse must flag it stale, never treat it as authoritative.
        advanced_set = evidence_set.model_copy(update={"version": 8})
        await repository.add_with_text(advanced_set, {"evd_e123": content})

        with bind_tenant_context(TenantContext(tenant_id="tn_t1")):
            stale_results = await service.search(content, requester_clearance=Classification.CONFIDENTIAL)
        assert len(stale_results) == 1
        assert stale_results[0].is_stale is True
        with pytest.raises(Exception):  # noqa: B017, PT011 -- InvariantViolation: no fresh candidates to hydrate
            await service.hydrate_for_pipeline(stale_results)
    finally:
        await database.disconnect()


async def test_qdrant_unavailability_never_blocks_or_corrupts_canonical_postgresql_writes() -> None:
    """Failure isolation (item 8, 35-36): a canonical PostgreSQL write/read
    succeeds independently of Qdrant's health — Qdrant total loss degrades
    to "semantic retrieval temporarily unavailable," never "canonical
    intelligence lost."""
    database = await _database()
    if database is None:
        pytest.skip("no live, migrated PostgreSQL reachable — see PULSE_DATABASE_URL")

    try:
        repository = PostgresEvidenceSetRepository(database)
        evidence_set = _evidence_set(
            evidence_id="evd_isolated", tenant_id="tn_t1", classification=Classification.TENANT, version=1
        )
        await repository.add_with_text(evidence_set, {"evd_isolated": "isolated content"})

        # An unreachable Qdrant endpoint never raises anything but Pulse's
        # own typed, retryable errors — and never touches PostgreSQL.
        embedding_port = HaystackEmbeddingAdapter(
            text_embedder=build_text_embedder("mock", dimension=_DIMENSION),
            document_embedder=build_document_embedder("mock", dimension=_DIMENSION),
            model_id="mock:test",
            model_version="1",
        )
        broken_store = QdrantEvidenceProjectionStore(
            embedding_port, collection_name="unreachable", url="http://localhost:1", timeout=1
        )
        with pytest.raises(ProjectionWriteFailed):
            await broken_store.upsert_projection(
                ProjectionCollection.EVIDENCE,
                ProjectionRecord(
                    canonical_object_id="evd_isolated",
                    evidence_set_id=evidence_set.id,
                    canonical_version=1,
                    tenant_id="tn_t1",
                    classification=Classification.TENANT,
                    content="isolated content",
                    content_hash="hash",
                    embedding_model_id="mock:test",
                    embedding_model_version="1",
                ),
            )
        service = EvidenceRetrievalService(semantic_retrieval=broken_store, hydration=repository)
        with bind_tenant_context(TenantContext(tenant_id="tn_t1")), pytest.raises(SemanticRetrievalUnavailable):
            await service.search("isolated content")

        # The canonical PostgreSQL write is untouched and fully readable.
        reread = await repository.get(evidence_set.id)
        assert reread is not None
        assert reread.version == 1
    finally:
        await database.disconnect()
