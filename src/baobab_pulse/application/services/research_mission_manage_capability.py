"""Canonical intelligence.research-mission.manage adapter (P-CAP-04/05)."""

from typing import Protocol
from uuid import UUID

from baobab_pulse.application.intelligence_authority import (
    RESEARCH_MISSION_MANAGE_SCOPE,
    classification_clearance,
    permits_classification,
)
from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.context_authority import (
    ContextAccessDeniedError,
    ContextAuthenticationError,
    ContextAuthorityPort,
    ContextAuthorityUnavailableError,
    ContextNotFoundError,
    TrustedPlatformContext,
)
from baobab_pulse.application.ports.research_mission_mutation import (
    ResearchMissionCreateMutation,
    ResearchMissionMutationStore,
)
from baobab_pulse.contracts.api.research_missions import (
    ResearchMissionCreateRequest,
    ResearchMissionGetRequest,
    ResearchMissionManageRequest,
)
from baobab_pulse.contracts.mutations import (
    canonical_create_request_json,
    create_request_fingerprint,
)
from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.domain.shared.enums import Classification, TenantScope
from baobab_pulse.domain.shared.errors import (
    CapabilityAccessDeniedError,
    CapabilityAuthenticationError,
    CapabilityAuthorityUnavailableError,
    CapabilityContextNotFoundError,
    CapabilityInvalidRequestError,
    ResearchMissionNotFoundError,
)
from baobab_pulse.domain.shared.identifiers import new_id
from baobab_pulse.domain.shared.value_objects import TenantContext


class DurableResearchMissionRepository(Protocol):
    async def get_for_tenant(
        self,
        entity_id: str,
        *,
        tenant_id: str,
    ) -> ResearchMission | None: ...


class ResearchMissionManageCapabilityService:
    """Create/get ResearchMissions under trusted CP tenancy and mutation governance."""

    def __init__(
        self,
        *,
        context_authority: ContextAuthorityPort,
        repository: DurableResearchMissionRepository,
        mutation_store: ResearchMissionMutationStore,
    ) -> None:
        self._context_authority = context_authority
        self._repository = repository
        self._mutation_store = mutation_store

    async def manage(
        self,
        *,
        context_id: UUID,
        caller: AuthenticatedCaller,
        request: ResearchMissionManageRequest,
        correlation_id: UUID,
        idempotency_key: str | None,
        clearance: Classification,
    ) -> ResearchMission:
        trusted = await self._trusted_context(context_id=context_id, caller=caller)
        clearance = classification_clearance(
            caller,
            required_scope=RESEARCH_MISSION_MANAGE_SCOPE,
        )
        if isinstance(request, ResearchMissionCreateRequest):
            return await self._create(
                request=request,
                trusted=trusted,
                caller=caller,
                correlation_id=correlation_id,
                idempotency_key=idempotency_key,
                clearance=clearance,
            )
        return await self._get(
            request=request,
            trusted=trusted,
            clearance=clearance,
        )

    async def _create(
        self,
        *,
        request: ResearchMissionCreateRequest,
        trusted: TrustedPlatformContext,
        caller: AuthenticatedCaller,
        correlation_id: UUID,
        idempotency_key: str | None,
    ) -> ResearchMission:
        if idempotency_key is None:
            raise CapabilityInvalidRequestError(
                "Idempotency-Key is required for ResearchMission CREATE"
            )
        if request.tenant_scope in (TenantScope.GLOBAL, TenantScope.PLATFORM):
            raise CapabilityAccessDeniedError(
                "tenant-bound capability invocation cannot create global/platform research missions"
            )
        if not permits_classification(clearance, request.classification):
            raise CapabilityAccessDeniedError(
                "the requested ResearchMission classification exceeds caller clearance"
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
        commit = await self._mutation_store.commit_create(
            ResearchMissionCreateMutation(
                tenant_id=trusted.tenant_id,
                actor_subject=caller.subject,
                actor_client_id=caller.client_id,
                context_id=trusted.context_id,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                request_fingerprint=create_request_fingerprint(request),
                request_payload=canonical_create_request_json(request),
                mission=mission,
            )
        )
        return commit.mission

    async def _get(
        self,
        *,
        request: ResearchMissionGetRequest,
        trusted: TrustedPlatformContext,
        clearance: Classification,
    ) -> ResearchMission:
        mission = await self._repository.get_for_tenant(
            request.research_mission_id,
            tenant_id=trusted.tenant_id,
        )
        if mission is None or not permits_classification(
            clearance,
            mission.classification,
        ):
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
