"""Explicit source-test doubles; never native provider/INT-07 evidence."""

from datetime import UTC, datetime, timedelta

from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.capability_invocation import CapabilityInvocation
from baobab_pulse.application.ports.context_authority import TrustedPlatformContext


class AllowedInvocationAuthority:
    async def authorise(
        self, *, context: TrustedPlatformContext, caller: AuthenticatedCaller
    ) -> CapabilityInvocation:
        return CapabilityInvocation(
            "res_" + "1" * 32,
            "grant_" + "2" * 32,
            "bind_" + "3" * 32,
            "provider_" + "4" * 32,
            "ei_" + "5" * 32,
            datetime.now(UTC) + timedelta(seconds=10),
        )


class RecordingReadAudit:
    async def record(
        self,
        *,
        context: TrustedPlatformContext,
        caller: AuthenticatedCaller,
        invocation: CapabilityInvocation,
        evidence_set_id: str | None,
        result_count: int,
    ) -> None:
        pass
