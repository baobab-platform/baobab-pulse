"""Canonical HTTP adapter for intelligence.research-mission.manage."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from baobab_pulse.api.dependencies import (
    AuthenticatedCapabilityRequest,
    require_authenticated_capability_request,
    require_context_id,
)
from baobab_pulse.contracts.api.research_missions import (
    ResearchMissionManageRequest,
    ResearchMissionResponse,
)
from baobab_pulse.domain.shared.errors import CapabilityRuntimeUnavailableError

router = APIRouter(prefix="/research-missions", tags=["research-missions"])


@router.post(
    "/manage",
    operation_id="manageIntelligenceResearchMission",
    response_model=ResearchMissionResponse,
)
async def manage_research_mission(
    request: ResearchMissionManageRequest,
    auth: Annotated[
        AuthenticatedCapabilityRequest,
        Depends(require_authenticated_capability_request),
    ],
    context_id: Annotated[UUID, Depends(require_context_id)],
) -> ResearchMissionResponse:
    service = auth.runtime.research_missions
    if service is None:
        raise CapabilityRuntimeUnavailableError(
            "ResearchMission capability runtime is not configured"
        )

    mission = await service.manage(
        context_id=context_id,
        caller=auth.caller,
        request=request,
    )
    return ResearchMissionResponse.from_domain(mission)
