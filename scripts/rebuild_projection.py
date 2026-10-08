"""Rebuild the Qdrant evidence projection from canonical PostgreSQL data.

The controlled reindex pathway (item 32, 74-75):

    canonical EvidenceSets (PostgreSQL)
        -> resolve text
        -> ProjectionRecord per Evidence entry
        -> embed
        -> Qdrant (replace-by-source: old points for that EvidenceSet are
           deleted first, so a projection never mixes stale and fresh
           points for the same source)

Safe to re-run at any time — a complete loss of Qdrant means "semantic
retrieval temporarily unavailable," never lost canonical data (item 8), and
re-running this script is the documented recovery path.

Usage:
    uv run python scripts/rebuild_projection.py                    # every EvidenceSet
    uv run python scripts/rebuild_projection.py --evidence-set-id evs_123
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys

from baobab_pulse.application.ports.vector_projection_port import ProjectionCollection, ProjectionRecord
from baobab_pulse.configuration.settings import Settings
from baobab_pulse.domain.evidence import EvidenceSet
from baobab_pulse.domain.shared.errors import PulseError
from baobab_pulse.infrastructure.haystack.document_stores.qdrant_projection_store import (
    QdrantEvidenceProjectionStore,
    resolve_collection_name,
)
from baobab_pulse.infrastructure.haystack.embedders.embedding_adapter import (
    HaystackEmbeddingAdapter,
    build_document_embedder,
    build_text_embedder,
)
from baobab_pulse.infrastructure.persistence.connection import Database
from baobab_pulse.infrastructure.persistence.evidence_repository import PostgresEvidenceSetRepository


async def _fetch_evidence_sets(
    database: Database, repository: PostgresEvidenceSetRepository, evidence_set_id: str | None
) -> list[tuple[EvidenceSet, dict[str, str]]]:
    if evidence_set_id:
        hydrated = await repository.get_with_text(evidence_set_id)
        return [hydrated] if hydrated is not None else []

    rows = await database.pool.fetch("SELECT id FROM evidence.evidence_sets ORDER BY id")
    results: list[tuple[EvidenceSet, dict[str, str]]] = []
    for row in rows:
        hydrated = await repository.get_with_text(row["id"])
        if hydrated is not None:
            results.append(hydrated)
    return results


def _records_for(
    evidence_set: EvidenceSet, evidence_text: dict[str, str], *, embedding_model_id: str, embedding_model_version: str
) -> list[ProjectionRecord]:
    tenant_id = evidence_set.tenant_context.tenant_id if evidence_set.tenant_context else None
    records = []
    for entry in evidence_set.entries:
        text = evidence_text.get(entry.id)
        if text is None:
            # Evidence entries with no resolved text are not projected —
            # there is nothing to embed (item 27: Evidence carries no text
            # of its own).
            continue
        records.append(
            ProjectionRecord(
                canonical_object_id=entry.id,
                evidence_set_id=evidence_set.id,
                canonical_version=evidence_set.version,
                tenant_id=tenant_id,
                classification=evidence_set.classification,
                valid_from=entry.valid_from,
                valid_to=entry.valid_to,
                content=text,
                content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                embedding_model_id=embedding_model_id,
                embedding_model_version=embedding_model_version,
            )
        )
    return records


async def main(evidence_set_id: str | None) -> None:
    settings = Settings()
    database = Database(settings.database_url)
    await database.connect()
    try:
        repository = PostgresEvidenceSetRepository(database)
        pairs = await _fetch_evidence_sets(database, repository, evidence_set_id)
        if not pairs:
            print("No EvidenceSets found to project.")
            return

        embedding_port = HaystackEmbeddingAdapter(
            text_embedder=build_text_embedder(
                settings.embedding_provider, dimension=settings.embedding_dimension, model=settings.embedding_model_id
            ),
            document_embedder=build_document_embedder(
                settings.embedding_provider, dimension=settings.embedding_dimension, model=settings.embedding_model_id
            ),
            model_id=f"{settings.embedding_provider}:{settings.embedding_model_id}",
            model_version="1",
        )
        store = QdrantEvidenceProjectionStore(
            embedding_port,
            collection_name=resolve_collection_name(
                ProjectionCollection.EVIDENCE,
                prefix=settings.qdrant_collection_prefix,
                version=settings.qdrant_evidence_collection_version,
            ),
            url=settings.qdrant_url,
            location=settings.qdrant_location,
            api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
            https=settings.qdrant_tls,
            timeout=settings.qdrant_timeout_seconds,
        )

        total = 0
        for evidence_set, evidence_text in pairs:
            records = _records_for(
                evidence_set,
                evidence_text,
                embedding_model_id=embedding_port.model_identity(),
                embedding_model_version="1",
            )
            if not records:
                print(f"EvidenceSet {evidence_set.id}: nothing to project (no resolved text).")
                continue
            await store.replace_projection(ProjectionCollection.EVIDENCE, evidence_set.id, records)
            total += len(records)
            print(f"Projected {len(records)} evidence entr(y/ies) from EvidenceSet {evidence_set.id} (canonical_version={evidence_set.version}).")
        print(f"Done. {total} projection(s) written.")
    finally:
        await database.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--evidence-set-id", default=None, help="Rebuild only this EvidenceSet's projection.")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.evidence_set_id))
    except (OSError, PulseError) as exc:
        print(f"Projection rebuild failed: {exc}", file=sys.stderr)
        sys.exit(1)
