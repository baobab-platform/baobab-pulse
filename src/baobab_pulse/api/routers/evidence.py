"""Canonical HTTP adapter for intelligence.evidence.search (P-CAP-03).

The JSON body is the exact Shared v1 request shape. Tenant authority and
classification clearance are never selected by the caller in that body.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from baobab_pulse.api.dependencies import (
    AuthenticatedCapabilityRequest,
    require_authenticated_capability_request,
    require_context_id,
)
from baobab_pulse.contracts.api.evidence import (
    EvidenceCandidateResponse,
    EvidenceSearchRequest,
    EvidenceSearchResponse,
)

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post(
    "/search",
    operation_id="searchIntelligenceEvidence",
    response_model=EvidenceSearchResponse,
)
async def search_evidence(
    request: EvidenceSearchRequest,
    auth: Annotated[
        AuthenticatedCapabilityRequest,
        Depends(require_authenticated_capability_request),
    ],
    context_id: Annotated[UUID, Depends(require_context_id)],
) -> EvidenceSearchResponse:
    """Search only within the caller-bound tenant context validated by CP."""

    candidates = await auth.runtime.evidence_search.search(
        context_id=context_id,
        caller=auth.caller,
        query_text=request.query_text,
        evidence_set_id=request.evidence_set_id,
        top_k=request.top_k,
    )
    return EvidenceSearchResponse(
        candidates=tuple(
            EvidenceCandidateResponse(**candidate.model_dump())
            for candidate in candidates
        )
    )
