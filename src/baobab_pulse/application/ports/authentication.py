"""Provider-neutral inbound authentication boundary for Pulse capability routes."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AuthenticatedCaller:
    """Verified caller presented to the Pulse resource server."""

    subject: str
    access_token: str | None = field(default=None, repr=False, compare=False)
    client_id: str | None = None
    tenant_id: str | None = None
    scopes: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise ValueError("authenticated caller subject must not be empty")
        if self.access_token is not None and not self.access_token.strip():
            raise ValueError("access_token must not be empty when supplied")


class WorkloadAuthenticationError(PermissionError):
    """The presented bearer token could not be verified."""


class WorkloadAuthenticationUnavailableError(RuntimeError):
    """The configured IAM/token verification authority is unavailable."""


class WorkloadAuthenticatorPort(Protocol):
    """Verify issuer, expiry, audience and actor semantics for a Pulse caller."""

    async def authenticate(self, access_token: str) -> AuthenticatedCaller: ...


__all__ = [
    "AuthenticatedCaller",
    "WorkloadAuthenticationError",
    "WorkloadAuthenticationUnavailableError",
    "WorkloadAuthenticatorPort",
]
