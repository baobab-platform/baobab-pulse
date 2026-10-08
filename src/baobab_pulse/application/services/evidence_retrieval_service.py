"""EvidenceRetrievalService — the "Baobab Application Service" in the Qdrant
refactor's required RAG flow (item 42)::

    Research Query
          |
          v
    Tenant / Context                <- tenancy.context.require_tenant_context()
          |
          v
    Authorisation Policy            <- SemanticRetrievalPort enforces tenant + classification
          |
          v
    SemanticRetrievalPort -> Qdrant
          |
          v
    Authorised Candidate IDs        <- search() below
          |
          v
    Canonical Hydration             <- hydrate_for_pipeline() below, via EvidenceSetHydrationPort
          |
          v
    Evidence Assembly
          |
          v
    Haystack Pipeline               <- the EXISTING, unchanged ResearchMissionService/pipeline

This service does not touch Haystack, Qdrant, or PostgreSQL directly — it
only knows ``SemanticRetrievalPort``/``EvidenceSetHydrationPort``, same as
every other application service in this codebase.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from baobab_pulse.application.ports.repositories import EvidenceSetHydrationPort
from baobab_pulse.application.ports.semantic_retrieval_port import (
    EvidenceRetrievalQuery,
    SemanticRetrievalPort,
)
from baobab_pulse.domain.evidence import EvidenceSet
from baobab_pulse.domain.shared.enums import Classification
from baobab_pulse.domain.shared.errors import InvariantViolation
from baobab_pulse.tenancy.context import require_tenant_context


class HydratedEvidenceCandidate(BaseModel):
    """An authorised retrieval hit, annotated with whether its Qdrant
    projection is stale relative to the current canonical version (item
    31). ``score`` is Qdrant's similarity score — never Pulse confidence
    or evidence quality (item 59)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_object_id: str
    evidence_set_id: str
    score: float
    is_stale: bool


class EvidenceRetrievalService:
    def __init__(self, semantic_retrieval: SemanticRetrievalPort, hydration: EvidenceSetHydrationPort) -> None:
        self._semantic_retrieval = semantic_retrieval
        self._hydration = hydration

    async def search(
        self,
        query_text: str,
        *,
        requester_clearance: Classification = Classification.TENANT,
        evidence_set_id: str | None = None,
        top_k: int = 10,
    ) -> tuple[HydratedEvidenceCandidate, ...]:
        """Fail-closed by construction: :func:`require_tenant_context` raises
        :class:`~baobab_pulse.domain.shared.errors.TenantContextMissingError`
        rather than letting an unrestricted query reach Qdrant (item 44)."""
        tenant_context = require_tenant_context()
        query = EvidenceRetrievalQuery(
            query_text=query_text,
            tenant_context=tenant_context,
            requester_clearance=requester_clearance,
            evidence_set_id=evidence_set_id,
            top_k=top_k,
        )
        raw_candidates = await self._semantic_retrieval.retrieve_evidence(query)

        current_versions: dict[str, int | None] = {}
        results: list[HydratedEvidenceCandidate] = []
        for candidate in raw_candidates:
            if candidate.evidence_set_id not in current_versions:
                current_versions[candidate.evidence_set_id] = await self._hydration.current_version(
                    candidate.evidence_set_id
                )
            current_version = current_versions[candidate.evidence_set_id]
            if current_version is None:
                # The canonical source no longer exists in PostgreSQL at
                # all (deleted/retired) — the Qdrant point is orphaned and
                # must never be treated as evidence of anything.
                continue
            results.append(
                HydratedEvidenceCandidate(
                    canonical_object_id=candidate.canonical_object_id,
                    evidence_set_id=candidate.evidence_set_id,
                    score=candidate.score,
                    is_stale=candidate.canonical_version < current_version,
                )
            )
        return tuple(results)

    async def hydrate_for_pipeline(
        self, candidates: Sequence[HydratedEvidenceCandidate]
    ) -> tuple[EvidenceSet, dict[str, str]]:
        """Turn authorised, fresh candidates into the ``(EvidenceSet,
        evidence_text)`` pair the existing, unchanged
        ``ResearchMissionService.run_research_pipeline`` already accepts —
        Qdrant's cached content is never used here; text comes back from
        PostgreSQL (item 29, 61).

        Scope limit of this reference implementation: candidates must all
        belong to one ``EvidenceSet`` (the common case — a research
        question investigates one evidence corpus at a time). Composing
        several EvidenceSets into one synthetic aggregate would cross
        AGG-PULSE aggregate boundaries and is deliberately not attempted
        here; a real cross-set research flow needs its own ADR-governed
        design, not an implicit merge.
        """
        fresh = [candidate for candidate in candidates if not candidate.is_stale]
        if not fresh:
            raise InvariantViolation("no fresh evidence candidates available to hydrate")

        evidence_set_ids = {candidate.evidence_set_id for candidate in fresh}
        if len(evidence_set_ids) > 1:
            raise InvariantViolation(
                "hydrate_for_pipeline only supports candidates from a single EvidenceSet "
                f"in this reference implementation; got {sorted(evidence_set_ids)}"
            )
        evidence_set_id = next(iter(evidence_set_ids))

        hydrated = await self._hydration.get_with_text(evidence_set_id)
        if hydrated is None:
            raise InvariantViolation(f"EvidenceSet {evidence_set_id!r} no longer exists canonically")
        evidence_set, full_text = hydrated

        matched_ids = {candidate.canonical_object_id for candidate in fresh}
        narrowed_text = {
            evidence_id: text for evidence_id, text in full_text.items() if evidence_id in matched_ids
        }
        return evidence_set, narrowed_text
