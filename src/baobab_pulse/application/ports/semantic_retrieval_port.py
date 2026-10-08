"""SemanticRetrievalPort — the read side of Qdrant semantic projections.

Only ``retrieve_evidence`` is implemented — the only retrieval use case
this codebase actually has (item 18: "according to existing application
needs"); ``retrieve_documents``/``retrieve_research``/
``retrieve_entity_candidates`` are not stubbed speculatively.

Tenant filtering happens inside the port implementation, before any
candidate crosses back out (item 43-44): a missing tenant context is a
hard failure here, never an unrestricted query. See
``application.services.evidence_retrieval_service`` for how a
``SemanticCandidate`` is authorised and staleness-checked before it is
allowed to inform canonical hydration.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from baobab_pulse.domain.shared.enums import Classification
from baobab_pulse.domain.shared.value_objects import TenantContext


class EvidenceRetrievalQuery(BaseModel):
    """Everything a semantic evidence search needs, in Pulse's own
    vocabulary — never a Qdrant filter/query type."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query_text: str
    tenant_context: TenantContext
    """Required, not optional (item 44: fail closed) — see
    :func:`baobab_pulse.tenancy.context.require_tenant_context`, which the
    caller uses to obtain this before constructing a query."""
    requester_clearance: Classification = Classification.TENANT
    evidence_set_id: str | None = None
    """Optionally narrow the search to one EvidenceSet — most callers
    leave this unset and search the tenant's whole evidence corpus."""
    top_k: int = 10


class SemanticCandidate(BaseModel):
    """A retrieval hit, already tenant/classification-authorised. Not
    evidence yet, and never confidence (item 59) — ``score`` is Qdrant's
    similarity score and nothing more; it is dropped, not carried forward,
    once ``application.services.evidence_retrieval_service`` hydrates the
    canonical object."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_object_id: str
    evidence_set_id: str
    canonical_version: int
    """The ``EvidenceSet.version`` recorded *at projection time* — compare
    against the hydrated object's current version to detect staleness
    (item 31); this port never decides staleness itself."""
    score: float


class SemanticRetrievalPort(Protocol):
    """Implemented today by
    ``infrastructure.haystack.document_stores.qdrant_projection_store.QdrantEvidenceProjectionStore``.
    """

    async def retrieve_evidence(self, query: EvidenceRetrievalQuery) -> tuple[SemanticCandidate, ...]:
        """Raises :class:`~baobab_pulse.domain.shared.errors.SemanticRetrievalUnavailable`
        if the vector store cannot be reached — never a raw Qdrant/HTTP
        exception (item 37)."""
        ...
