"""Production Control Plane context-validation adapter for Pulse."""

from __future__ import annotations

import asyncio
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from datetime import UTC, datetime
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.context_authority import (
    ContextAccessDeniedError,
    ContextAuthenticationError,
    ContextAuthorityUnavailableError,
    ContextNotFoundError,
    TrustedPlatformContext,
)


@dataclass(frozen=True, slots=True)
class _ValidatorToken:
    access_token: str
    expires_at: float


class ClientCredentialsTokenProvider:
    """Short-lived validator-token source; tokens are cached only in memory."""

    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str = "context:validate",
        timeout_seconds: float = 5.0,
        early_refresh_seconds: int = 30,
    ) -> None:
        if not client_id.strip() or not client_secret:
            raise ValueError("client_id and client_secret are required")
        self._token_url = _validated_http_endpoint(token_url, name="token_url")
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._timeout_seconds = timeout_seconds
        self._early_refresh_seconds = early_refresh_seconds
        self._cached: _ValidatorToken | None = None
        self._lock = threading.Lock()

    async def access_token(self) -> str:
        return await asyncio.to_thread(self._access_token_sync)

    def _access_token_sync(self) -> str:
        now = time.monotonic()
        cached = self._cached
        if cached is not None and now < cached.expires_at:
            return cached.access_token
        with self._lock:
            now = time.monotonic()
            cached = self._cached
            if cached is not None and now < cached.expires_at:
                return cached.access_token

            encoded = urllib.parse.urlencode(
                {
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": self._scope,
                }
            ).encode("ascii")
            request = urllib.request.Request(
                self._token_url,
                data=encoded,
                method="POST",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            try:
                with urllib.request.urlopen(  # nosec B310 -- URL validated by _validated_http_endpoint
                    request,
                    timeout=self._timeout_seconds,
                ) as response:
                    payload = _read_json_object(response.read())
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                raise ContextAuthorityUnavailableError(
                    "validator token authority is unavailable"
                ) from exc

            token = payload.get("access_token")
            token_type = payload.get("token_type")
            expires_in = payload.get("expires_in")
            granted_scope = payload.get("scope", self._scope)
            if (
                not isinstance(token, str)
                or len(token) < 20
                or token_type != "Bearer"
                or not isinstance(expires_in, int)
                or isinstance(expires_in, bool)
                or not 60 <= expires_in <= 86400
                or not isinstance(granted_scope, str)
                or self._scope not in granted_scope.split()
            ):
                raise ContextAuthorityUnavailableError(
                    "validator token response violates the canonical workload profile"
                )
            usable_for = max(1, expires_in - self._early_refresh_seconds)
            self._cached = _ValidatorToken(
                access_token=token,
                expires_at=time.monotonic() + usable_for,
            )
            return token


class HttpControlPlaneContextAuthority:
    """Redeem caller-bound PlatformContext through canonical CP validation."""

    def __init__(
        self,
        *,
        validation_url: str,
        validator_tokens: ClientCredentialsTokenProvider,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._validation_url = _validated_http_endpoint(
            validation_url,
            name="validation_url",
        )
        self._validator_tokens = validator_tokens
        self._timeout_seconds = timeout_seconds

    async def redeem(
        self,
        *,
        context_id: UUID,
        caller: AuthenticatedCaller,
    ) -> TrustedPlatformContext:
        subject_token = caller.access_token
        if subject_token is None:
            raise ContextAuthenticationError(
                "authenticated caller lacks subject-token evidence"
            )
        validator_token = await self._validator_tokens.access_token()
        return await asyncio.to_thread(
            self._redeem_sync,
            context_id,
            subject_token,
            validator_token,
        )

    def _redeem_sync(
        self,
        context_id: UUID,
        subject_token: str,
        validator_token: str,
    ) -> TrustedPlatformContext:
        body = json.dumps(
            {
                "context_id": str(context_id),
                "subject_token": subject_token,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            self._validation_url,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {validator_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(  # nosec B310 -- URL validated by _validated_http_endpoint
                request,
                timeout=self._timeout_seconds,
            ) as response:
                payload = _read_json_object(response.read())
        except urllib.error.HTTPError as exc:
            # Never include response bodies: they may contain infrastructure
            # diagnostics and must never echo subject-token evidence.
            if exc.code == 404:
                raise ContextNotFoundError("context is unavailable") from exc
            if exc.code == 403:
                raise ContextAccessDeniedError("context validation was denied") from exc
            if exc.code == 401:
                raise ContextAuthenticationError(
                    "validator authentication failed"
                ) from exc
            if exc.code == 503:
                raise ContextAuthorityUnavailableError(
                    "Control Plane context validation is unavailable"
                ) from exc
            raise ContextAuthorityUnavailableError(
                "Control Plane context validation failed"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise ContextAuthorityUnavailableError(
                "Control Plane context validation is unavailable"
            ) from exc

        returned_context = payload.get("context_id")
        tenant_id = payload.get("tenant_id")
        expires_at = payload.get("expires_at")
        if returned_context != str(context_id):
            raise ContextAuthorityUnavailableError(
                "Control Plane returned a mismatched context identity"
            )
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise ContextAuthorityUnavailableError(
                "Control Plane returned an invalid tenant identity"
            )
        if not isinstance(expires_at, str) or not expires_at:
            raise ContextAuthorityUnavailableError(
                "Control Plane returned an unbounded context"
            )
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ContextAuthorityUnavailableError(
                "Control Plane returned an invalid context expiry"
            ) from exc
        if expiry.tzinfo is None or expiry <= datetime.now(UTC):
            raise ContextNotFoundError("context is unavailable")
        organisation_id = payload.get("organisation_id")
        market_id = payload.get("market_id")
        if organisation_id is not None and not isinstance(organisation_id, str):
            raise ContextAuthorityUnavailableError(
                "Control Plane returned an invalid organisation identity"
            )
        if market_id is not None and not isinstance(market_id, str):
            raise ContextAuthorityUnavailableError(
                "Control Plane returned an invalid market identity"
            )
        return TrustedPlatformContext(
            context_id=context_id,
            tenant_id=tenant_id,
            organisation_id=organisation_id,
            market_id=market_id,
        )


def _validated_http_endpoint(value: str, *, name: str) -> str:
    """Permit only explicit HTTP(S) authority endpoints.

    Local/dev deployments may use HTTP; production deployment policy can require
    HTTPS at configuration admission. Userinfo and fragments are never valid
    authority endpoints and custom/file schemes are rejected before urlopen.
    """

    candidate = value.strip()
    parsed = urllib.parse.urlsplit(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError(
            f"{name} must be an absolute HTTP(S) URL without userinfo or fragment"
        )
    return candidate


def _read_json_object(raw: bytes) -> Mapping[str, Any]:
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("response body must be a JSON object")
    return value


__all__ = [
    "ClientCredentialsTokenProvider",
    "HttpControlPlaneContextAuthority",
]
