"""Redeem the actual caller through CP's normal recorded capability resolver."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.capability_invocation import CapabilityInvocation
from baobab_pulse.application.ports.context_authority import TrustedPlatformContext
from baobab_pulse.domain.shared.errors import (
    CapabilityAccessDeniedError,
    CapabilityAuthenticationError,
    CapabilityAuthorityUnavailableError,
    CapabilityContextNotFoundError,
)
from baobab_pulse.infrastructure.control_plane.context_authority import _validated_http_endpoint


class HttpCapabilityInvocationAuthority:
    """No positive cache, redirects, supplied authority IDs or alternate route."""

    def __init__(
        self,
        *,
        resolution_url: str,
        provider_id: str,
        engine_instance_id: str,
        capability_key: str = "intelligence.evidence.search",
    ) -> None:
        if capability_key not in {"intelligence.evidence.search", "intelligence.research-mission.manage"}:
            raise ValueError("canonical Pulse capability required")
        self._capability = capability_key
        self._url = _validated_http_endpoint(resolution_url, name="resolution_url")
        if not re.fullmatch(r"provider_[0-9a-f]{32}", provider_id):
            raise ValueError("canonical provider_id is required")
        if not re.fullmatch(r"ei_[0-9a-f]{32}", engine_instance_id):
            raise ValueError("canonical engine_instance_id is required")
        self._provider = provider_id
        self._instance = engine_instance_id

    async def authorise(
        self, *, context: TrustedPlatformContext, caller: AuthenticatedCaller
    ) -> CapabilityInvocation:
        if not caller.access_token:
            raise CapabilityAuthenticationError("actual caller token is required")
        correlation = str(uuid4())
        try:
            async with (
                asyncio.timeout(3),
                httpx.AsyncClient(timeout=httpx.Timeout(2), follow_redirects=False) as client,
                client.stream(
                    "POST",
                    self._url,
                    headers={"Authorization": "Bearer " + caller.access_token, "Cache-Control": "no-store"},
                    json={
                        "context_id": str(context.context_id),
                        "capability_key": self._capability,
                        "required_contract_version": 1,
                        "correlation_id": correlation,
                    },
                ) as response,
            ):
                if response.status_code == 401:
                    raise CapabilityAuthenticationError("caller cannot redeem capability authority")
                if response.status_code == 403:
                    raise CapabilityAccessDeniedError("capability resolution denied")
                if response.status_code == 404:
                    raise CapabilityContextNotFoundError("context unavailable")
                if response.status_code != 200:
                    raise CapabilityAuthorityUnavailableError("current CP resolution unavailable")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > 16384:
                        raise ValueError("oversized resolution")
                    body.extend(chunk)
                result = json.loads(body)
            if not isinstance(result, dict):
                raise ValueError("invalid resolution")
            if result.get("decision") != "RESOLVED":
                raise CapabilityAccessDeniedError("no current entitled binding for the resource")
            invocation = result.get("invocation")
            if not isinstance(invocation, dict):
                raise ValueError("missing invocation")
            now = datetime.now(UTC)
            resolved = datetime.fromisoformat(result["resolved_at"].replace("Z", "+00:00"))
            expires = datetime.fromisoformat(result["expires_at"].replace("Z", "+00:00"))
            if (
                result.get("context_id") != str(context.context_id)
                or result.get("capability_key") != self._capability
                or result.get("correlation_id") != correlation
                or type(result.get("contract_version")) is not int
                or result["contract_version"] != 1
                or type(invocation.get("contract_version")) is not int
                or invocation.get("contract_version") != 1
                or invocation.get("provider_id") != self._provider
                or invocation.get("engine_instance_id") != self._instance
                or invocation.get("service_reference") != "service://baobab-pulse/capabilities"
                or invocation.get("protocol") != "http"
                or resolved.tzinfo is None
                or expires.tzinfo is None
                or not now - timedelta(seconds=5) <= resolved <= now + timedelta(seconds=1)
                or not expires > now
                or not expires > resolved
            ):
                raise ValueError("mismatched or stale resolution")
            for key, prefix in (("resolution_id", "res"), ("grant_id", "grant"), ("binding_id", "bind")):
                if not re.fullmatch(prefix + r"_[0-9a-f]{32}", result.get(key, "")):
                    raise ValueError("invalid canonical authority id")
            return CapabilityInvocation(
                result["resolution_id"],
                result["grant_id"],
                result["binding_id"],
                self._provider,
                self._instance,
                expires,
            )
        except (httpx.HTTPError, TimeoutError, ValueError, KeyError, TypeError) as error:
            raise CapabilityAuthorityUnavailableError(
                "current CP capability authority unavailable"
            ) from error
