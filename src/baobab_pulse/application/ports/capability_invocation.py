"""Current CP binding authority and durable resource-read audit boundaries."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.context_authority import TrustedPlatformContext


@dataclass(frozen=True, slots=True)
class CapabilityInvocation:
    resolution_id: str
    grant_id: str
    binding_id: str
    provider_id: str
    engine_instance_id: str
    expires_at: datetime


class CapabilityInvocationAuthority(Protocol):
    async def authorise(
        self, *, context: TrustedPlatformContext, caller: AuthenticatedCaller
    ) -> CapabilityInvocation: ...


class EvidenceReadAudit(Protocol):
    async def record(
        self,
        *,
        context: TrustedPlatformContext,
        caller: AuthenticatedCaller,
        invocation: CapabilityInvocation,
        evidence_set_id: str | None,
        result_count: int,
    ) -> None: ...
