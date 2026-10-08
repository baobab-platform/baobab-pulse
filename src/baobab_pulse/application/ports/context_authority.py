"""Trusted Control Plane context boundary for Pulse capability execution."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from baobab_pulse.application.ports.authentication import AuthenticatedCaller


@dataclass(frozen=True, slots=True)
class TrustedPlatformContext:
    """Minimum caller-bound context Pulse requires for tenant-scoped search."""

    context_id: UUID
    tenant_id: str
    organisation_id: str | None = None
    market_id: str | None = None

    def __post_init__(self) -> None:
        if not self.tenant_id.strip():
            raise ValueError("trusted tenant_id must not be empty")


class ContextAuthenticationError(PermissionError):
    """Control Plane could not independently authenticate the subject token."""


class ContextAccessDeniedError(PermissionError):
    """The authenticated caller cannot use the requested context."""


class ContextNotFoundError(LookupError):
    """Context is unknown, expired, unbounded, or not owned by this caller."""


class ContextAuthorityUnavailableError(RuntimeError):
    """The authoritative Control Plane context service is unavailable."""


class ContextAuthorityPort(Protocol):
    """Validate a stored PlatformContext against the actual authenticated caller."""

    async def redeem(
        self,
        *,
        context_id: UUID,
        caller: AuthenticatedCaller,
    ) -> TrustedPlatformContext: ...


__all__ = [
    "ContextAccessDeniedError",
    "ContextAuthenticationError",
    "ContextAuthorityPort",
    "ContextAuthorityUnavailableError",
    "ContextNotFoundError",
    "TrustedPlatformContext",
]
