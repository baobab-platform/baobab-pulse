"""Canonical intelligence.evidence.search application adapter (P-CAP-03)."""

from datetime import UTC, datetime
from uuid import UUID

from baobab_pulse.application.intelligence_authority import (
    EVIDENCE_SEARCH_SCOPE,
    classification_clearance,
)
from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.capability_invocation import (
    CapabilityInvocationAuthority,
    EvidenceReadAudit,
)
from baobab_pulse.application.ports.context_authority import (
    ContextAccessDeniedError,
    ContextAuthenticationError,
    ContextAuthorityPort,
    ContextAuthorityUnavailableError,
    ContextNotFoundError,
)
from baobab_pulse.application.services.evidence_retrieval_service import (
    EvidenceRetrievalService,
    HydratedEvidenceCandidate,
)
from baobab_pulse.domain.shared.errors import (
    CapabilityAccessDeniedError,
    CapabilityAuthenticationError,
    CapabilityAuthorityUnavailableError,
    CapabilityContextNotFoundError,
)
from baobab_pulse.domain.shared.value_objects import TenantContext
from baobab_pulse.tenancy.context import bind_tenant_context


class EvidenceSearchCapabilityService:
    """Bind canonical evidence search to the authenticated caller's CP context."""

    def __init__(
        self,
        *,
        context_authority: ContextAuthorityPort,
        retrieval: EvidenceRetrievalService,
        invocation_authority: CapabilityInvocationAuthority | None = None,
        read_audit: EvidenceReadAudit | None = None,
    ) -> None:
        self._context_authority = context_authority
        self._retrieval = retrieval
        self._invocation_authority = invocation_authority
        self._read_audit = read_audit

    async def search(
        self,
        *,
        context_id: UUID,
        caller: AuthenticatedCaller,
        query_text: str,
        evidence_set_id: str | None,
        top_k: int,
    ) -> tuple[HydratedEvidenceCandidate, ...]:
        clearance = classification_clearance(
            caller,
            required_scope=EVIDENCE_SEARCH_SCOPE,
        )
        try:
            trusted = await self._context_authority.redeem(
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

        if self._invocation_authority is None or self._read_audit is None:
            raise CapabilityAuthorityUnavailableError(
                "current binding authority and durable audit are required"
            )
        invocation = await self._invocation_authority.authorise(context=trusted, caller=caller)

        tenant_context = TenantContext(
            tenant_id=trusted.tenant_id,
            context_id=str(trusted.context_id),
            organisation_id=trusted.organisation_id,
        )
        with bind_tenant_context(tenant_context):
            candidates = await self._retrieval.search(
                query_text,
                requester_clearance=clearance,
                evidence_set_id=evidence_set_id,
                top_k=top_k,
            )

        if invocation.expires_at <= datetime.now(UTC):
            raise CapabilityAccessDeniedError("capability authority expired during resource read")
        await self._read_audit.record(
            context=trusted,
            caller=caller,
            invocation=invocation,
            evidence_set_id=evidence_set_id,
            result_count=len(candidates),
        )
        if invocation.expires_at <= datetime.now(UTC):
            raise CapabilityAccessDeniedError("capability authority expired before resource delivery")
        return candidates


__all__ = ["EvidenceSearchCapabilityService"]
