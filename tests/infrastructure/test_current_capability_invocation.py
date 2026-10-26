"""Closed current-binding HTTP decisions; these mocks do not qualify INT-07."""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest

from baobab_pulse.application.ports.authentication import AuthenticatedCaller
from baobab_pulse.application.ports.context_authority import TrustedPlatformContext
from baobab_pulse.domain.shared.errors import CapabilityAccessDeniedError, CapabilityAuthorityUnavailableError
from baobab_pulse.infrastructure.control_plane.capability_invocation import HttpCapabilityInvocationAuthority

_CONTEXT = TrustedPlatformContext(context_id=UUID("11111111-1111-4111-8111-111111111111"), tenant_id="tn_own")
_CALLER = AuthenticatedCaller(subject="wl_caller", access_token="actual-subject-token")
_CLIENT = httpx.AsyncClient


@pytest.mark.parametrize(
    "capability", ["intelligence.evidence.search", "intelligence.research-mission.manage"]
)
@pytest.mark.parametrize(
    "mutation",
    [
        "current",
        "absent-subscription",
        "retired-binding",
        "unentitled-resource",
        "wrong-context",
        "wrong-provider",
        "boolean-contract",
        "wrong-instance",
        "wrong-reference",
        "wrong-correlation",
        "expired",
        "future",
        "oversized",
        "redirect",
        "unavailable",
    ],
)
async def test_every_invocation_requires_a_fresh_matching_resolution(
    monkeypatch: pytest.MonkeyPatch, mutation: str, capability: str
) -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        body = json.loads(request.content)
        now = datetime.now(UTC)
        response = {
            "resolution_id": "res_" + "1" * 32,
            "context_id": body["context_id"],
            "capability_key": capability,
            "correlation_id": body["correlation_id"],
            "decision": "RESOLVED",
            "contract_version": 1,
            "grant_id": "grant_" + "2" * 32,
            "binding_id": "bind_" + "3" * 32,
            "resolved_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=20)).isoformat(),
            "invocation": {
                "provider_id": "provider_" + "4" * 32,
                "engine_instance_id": "ei_" + "5" * 32,
                "service_reference": "service://baobab-pulse/capabilities",
                "protocol": "http",
                "contract_version": 1,
            },
        }
        if mutation in ("absent-subscription", "retired-binding", "unentitled-resource"):
            response["decision"] = "DENIED"
        elif mutation == "wrong-context":
            response["context_id"] = str(UUID(int=2))
        elif mutation == "wrong-correlation":
            response["correlation_id"] = str(UUID(int=2))
        elif mutation == "boolean-contract":
            response["invocation"]["contract_version"] = True
        elif mutation == "wrong-provider":
            response["invocation"]["provider_id"] = "provider_" + "9" * 32
        elif mutation == "wrong-instance":
            response["invocation"]["engine_instance_id"] = "ei_" + "9" * 32
        elif mutation == "wrong-reference":
            response["invocation"]["service_reference"] = "service://other/data"
        elif mutation == "expired":
            response["expires_at"] = (now - timedelta(seconds=1)).isoformat()
        elif mutation == "future":
            response["resolved_at"] = (now + timedelta(seconds=10)).isoformat()
        elif mutation == "oversized":
            return httpx.Response(200, content=b" " * 16385)
        elif mutation == "redirect":
            return httpx.Response(307, headers={"Location": "https://foreign.invalid"})
        elif mutation == "unavailable":
            return httpx.Response(503)
        return httpx.Response(200, json=response)

    def client(**kwargs: object) -> httpx.AsyncClient:
        return _CLIENT(transport=httpx.MockTransport(handler), **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", client)
    authority = HttpCapabilityInvocationAuthority(
        resolution_url="https://cp.example.test/v1/capabilities/resolve",
        provider_id="provider_" + "4" * 32,
        engine_instance_id="ei_" + "5" * 32,
        capability_key=capability,
    )
    if mutation == "current":
        await authority.authorise(context=_CONTEXT, caller=_CALLER)
        await authority.authorise(context=_CONTEXT, caller=_CALLER)
        assert len(calls) == 2
        assert calls[0].headers["Authorization"] == "Bearer actual-subject-token"
        assert (
            json.loads(calls[0].content)["correlation_id"] != json.loads(calls[1].content)["correlation_id"]
        )
    else:
        error = (
            CapabilityAccessDeniedError
            if mutation in ("absent-subscription", "retired-binding", "unentitled-resource")
            else CapabilityAuthorityUnavailableError
        )
        with pytest.raises(error):
            await authority.authorise(context=_CONTEXT, caller=_CALLER)
        assert len(calls) == 1
