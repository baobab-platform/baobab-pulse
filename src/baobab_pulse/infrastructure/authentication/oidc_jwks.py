"""Production OIDC/JWKS resource-server authenticator for Pulse."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    PyJWKClientConnectionError,
    PyJWKClientError,
    PyJWKError,
)

from baobab_pulse.application.ports.authentication import (
    AuthenticatedCaller,
    WorkloadAuthenticationError,
    WorkloadAuthenticationUnavailableError,
)


class OidcJwksWorkloadAuthenticator:
    """Verify provider-neutral workload JWTs against a configured OIDC JWKS."""

    def __init__(
        self,
        *,
        issuer: str,
        jwks_url: str,
        audience: str = "baobab-pulse",
        algorithms: tuple[str, ...] = ("RS256",),
        max_token_lifetime_seconds: int = 900,
        clock_skew_seconds: int = 30,
        http_timeout_seconds: float = 5.0,
    ) -> None:
        if not issuer.strip() or not jwks_url.strip() or not audience.strip():
            raise ValueError("issuer, jwks_url and audience are required")
        if not algorithms or any(not item.strip() for item in algorithms):
            raise ValueError("at least one explicit JWT algorithm is required")
        if max_token_lifetime_seconds < 60:
            raise ValueError("max_token_lifetime_seconds must be at least 60")
        if clock_skew_seconds < 0:
            raise ValueError("clock_skew_seconds must not be negative")

        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._algorithms = algorithms
        self._max_token_lifetime_seconds = max_token_lifetime_seconds
        self._clock_skew_seconds = clock_skew_seconds
        self._jwks = PyJWKClient(
            jwks_url,
            cache_keys=True,
            cache_jwk_set=True,
            lifespan=300,
            timeout=http_timeout_seconds,
            cooldown_duration=30,
        )

    async def authenticate(self, access_token: str) -> AuthenticatedCaller:
        if not 16 <= len(access_token) <= 8192:
            raise WorkloadAuthenticationError("access token length is invalid")
        try:
            claims = await asyncio.to_thread(self._decode, access_token)
        except PyJWKClientConnectionError as exc:
            raise WorkloadAuthenticationUnavailableError(
                "OIDC JWKS authority is unavailable"
            ) from exc
        except (InvalidTokenError, PyJWKClientError, PyJWKError, ValueError, TypeError) as exc:
            raise WorkloadAuthenticationError(
                "access token failed canonical workload verification"
            ) from exc

        actor_type = claims.get("actor_type")
        if actor_type != "workload":
            raise WorkloadAuthenticationError("access token actor_type must be workload")

        subject = claims.get("sub")
        jti = claims.get("jti")
        iat = claims.get("iat")
        exp = claims.get("exp")
        if not isinstance(subject, str) or not subject.strip():
            raise WorkloadAuthenticationError("access token subject is invalid")
        if not isinstance(jti, str) or not jti.strip():
            raise WorkloadAuthenticationError("access token jti is invalid")
        if not isinstance(iat, int) or isinstance(iat, bool):
            raise WorkloadAuthenticationError("access token iat is invalid")
        if not isinstance(exp, int) or isinstance(exp, bool):
            raise WorkloadAuthenticationError("access token exp is invalid")
        lifetime = exp - iat
        if lifetime < 1 or lifetime > self._max_token_lifetime_seconds:
            raise WorkloadAuthenticationError("access token lifetime exceeds policy")

        now = int(time.time())
        if iat > now + self._clock_skew_seconds:
            raise WorkloadAuthenticationError("access token iat is in the future")

        raw_scope = claims.get("scope", "")
        if not isinstance(raw_scope, str):
            raise WorkloadAuthenticationError("access token scope is invalid")
        scopes = frozenset(item for item in raw_scope.split() if item)

        client_id = claims.get("azp")
        if client_id is not None and not isinstance(client_id, str):
            raise WorkloadAuthenticationError("access token azp is invalid")

        tenant_id = claims.get("tenant_id")
        if tenant_id is not None and not isinstance(tenant_id, str):
            raise WorkloadAuthenticationError("access token tenant_id is invalid")

        return AuthenticatedCaller(
            subject=subject,
            access_token=access_token,
            client_id=client_id,
            tenant_id=tenant_id,
            scopes=scopes,
        )

    def _decode(self, access_token: str) -> Mapping[str, Any]:
        signing_key = self._jwks.get_signing_key_from_jwt(access_token)
        decoded = jwt.decode(
            access_token,
            signing_key.key,
            algorithms=list(self._algorithms),
            audience=self._audience,
            issuer=self._issuer,
            leeway=self._clock_skew_seconds,
            options={
                "require": ["exp", "iat", "sub", "jti", "iss", "aud"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
        if not isinstance(decoded, Mapping):
            raise WorkloadAuthenticationError("access token claims are invalid")
        return decoded


__all__ = ["OidcJwksWorkloadAuthenticator"]
