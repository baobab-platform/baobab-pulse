"""Canonical intelligence.research-mission.manage adapter (P-CAP-04)."""

from typing import Protocol
from uuid import UUID

from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.context_authority import (
    ContextAccessDeniedError,
    ContextAuthenticationError,
    ContextAuthorityPort,
    ContextAuthorityUnavailableError,
    ContextNotFoundError,
    TrustedPlatformContext,
)
from baobab_pulse.contracts.api.research_missions import (
    ResearchMissionCreateRequest,
    ResearchMissionGetRequest,
    ResearchMissionManageRequest,
)
from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.domain.shared.enums import Classification, TenantScope
from baobab_pulse.domain.shared.errors import (
    CapabilityAccessDeniedError,
    CapabilityAuthenticationError,
    CapabilityAuthorityUnavailableError,
    CapabilityContextNotFoundError,
    ResearchMissionNotFoundError,
)
from baobab_pulse.domain.shared.identifiers import new_id
from baobab_pulse.domain.shared.value_objects import TenantContext


class DurableResearchMissionRepository(Protocol):
    async def add(self, entity: ResearchMission) -> None: ...

    async def get_for_tenant(
        self,
        entity_id: str,
        *,
        tenant_id: str,
    ) -> ResearchMission | None: ...


class ResearchMissionManageCapabilityService:
    """Create/get durable ResearchMission aggregates under trusted CP tenancy."""

    def __init__(
        self,
        *,
        context_authority: ContextAuthorityPort,
        repository: DurableResearchMissionRepository,
    ) -> None:
        self._context_authority = context_authority
        self._repository = repository

    async def manage(
        self,
        *,
        context_id: UUID,
        caller: AuthenticatedCaller,
        request: ResearchMissionManageRequest,
    ) -> ResearchMission:
        trusted = await self._trusted_context(context_id=context_id, caller=caller)
        if isinstance(request, ResearchMissionCreateRequest):
            return await self._create(request=request, trusted=trusted)
        return await self._get(request=request, trusted=trusted)

    async def _create(
        self,
        *,
        request: ResearchMissionCreateRequest,
        trusted: TrustedPlatformContext,
    ) -> ResearchMission:
        if request.tenant_scope in (TenantScope.GLOBAL, TenantScope.PLATFORM):
            raise CapabilityAccessDeniedError(
                "tenant-bound capability invocation cannot create global/platform research missions"
            )
        if request.classification not in (
            Classification.PUBLIC,
            Classification.BAOBAB_INTERNAL,
            Classification.TENANT,
        ):
            raise CapabilityAccessDeniedError(
                "P-CAP-04 does not grant CONFIDENTIAL/RESTRICTED mission authority"
            )

        mission = ResearchMission(
            id=new_id("rms"),
            title=request.title,
            research_question=request.research_question,
            tenant_scope=request.tenant_scope,
            tenant_context=TenantContext(
                tenant_id=trusted.tenant_id,
                context_id=str(trusted.context_id),
                organisation_id=trusted.organisation_id,
            ),
            classification=request.classification,
            confidence_requirement=request.confidence_requirement,
        )
        mission.check_tenant_context()
        await self._repository.add(mission)
        return mission

    async def _get(
        self,
        *,
        request: ResearchMissionGetRequest,
        trusted: TrustedPlatformContext,
    ) -> ResearchMission:
        mission = await self._repository.get_for_tenant(
            request.research_mission_id,
            tenant_id=trusted.tenant_id,
        )
        if mission is None:
            raise ResearchMissionNotFoundError(
                "research mission is unavailable to this caller"
            )
        return mission

    async def _trusted_context(
        self,
        *,
        context_id: UUID,
        caller: AuthenticatedCaller,
    ) -> TrustedPlatformContext:
        try:
            return await self._context_authority.redeem(
                context_id=context_id,
                caller=caller,
            )
        except ContextAuthenticationError as exc:
            raise CapabilityAuthenticationError(
                "the caller could not be verified for the referenced context"
            ) from exc
        except ContextAccessDeniedError as exc:
            raise CapabilityAccessDeniedError(
                "the caller is not authorised for the referenced context"
            ) from exc
        except ContextNotFoundError as exc:
            raise CapabilityContextNotFoundError(
                "the referenced context is unavailable to this caller"
            ) from exc
        except ContextAuthorityUnavailableError as exc:
            raise CapabilityAuthorityUnavailableError(
                "Control Plane context validation is unavailable"
            ) from exc


__all__ = [
    "DurableResearchMissionRepository",
    "ResearchMissionManageCapabilityService",
]
