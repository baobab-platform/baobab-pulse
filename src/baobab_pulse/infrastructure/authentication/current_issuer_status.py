"""N03 native Pulse PEP: signed bearer AND current issuer status.

Read-only RFC 7662 introspection is performed on every request, *after*
independent JWKS signature/audience validation. A cached JWT signature is
not a current-authority decision; issuer outage, revoked token, mismatched
client, scope or audience all veto the request. No status cache, fallback
credential, CP grant, provider activation or business authority is created.
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import cast

from baobab_pulse.application.ports.authentication import (
    AuthenticatedCaller,
    WorkloadAuthenticationError,
    WorkloadAuthenticationUnavailableError,
    WorkloadAuthenticatorPort,
)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(\n        self, request: urllib.request.Request, fp: object, code: int,\n        msg: str, headers: object, newurl: str,\n    ) -> None:
        return None


def _no_duplicate_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate introspection JSON field")
        result[name] = value
    return result


class CurrentIssuerStatusWorkloadAuthenticator:
    """Provider-neutral wrapper over a signature-verifying workload port.

    Introspection has its own IAM-registered confidential client; never
    reuses Pulse's context:validate CP workload identity or human bearer.
    """

    def __init__(
        self,
        *,
        signed: WorkloadAuthenticatorPort,
        issuer: str,
        audience: str,
        introspection_url: str,
        introspection_client_id: str,
        introspection_client_secret: str,
        timeout_seconds: float = 5.0,
        allow_development_loopback_http: bool = False,
    ) -> None:
        url = urllib.parse.urlsplit(introspection_url)
        expected = urllib.parse.urlsplit(issuer)
        if (
            not issuer or not audience
            or not expected.hostname or expected.username is not None
            or expected.password is not None or expected.query or expected.fragment
            or (url.scheme, url.netloc) != (expected.scheme, expected.netloc)
            or not introspection_client_id or not introspection_client_secret
            or len(introspection_client_secret) < 32
            or url.username is not None or url.password is not None
            or url.query or url.fragment or not url.hostname
            or url.path != "/oauth2/introspect"
            or url.scheme not in {"http", "https"}
            or (url.scheme == "http" and not (
                allow_development_loopback_http and url.hostname == "127.0.0.1"
            ))
            or not 0 < timeout_seconds <= 10
        ):
            raise ValueError("untrusted issuer status authority or client")
        self._signed = signed
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._url = introspection_url
        self._timeout = timeout_seconds
        credential = (
            urllib.parse.quote(introspection_client_id, safe="")
            + ":"
            + urllib.parse.quote(introspection_client_secret, safe="")
        ).encode("utf-8")
        self._basic = "Basic " + base64.b64encode(credential).decode("ascii")
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect()
        )

    async def authenticate(self, access_token: str) -> AuthenticatedCaller:
        signed_caller = await self._signed.authenticate(access_token)
        if (
            signed_caller.access_token != access_token
            or not isinstance(signed_caller.client_id, str)
            or not signed_caller.client_id.strip()
        ):
            raise WorkloadAuthenticationError("issuer-signed client binding missing")
        try:
            status = await asyncio.to_thread(self._status, access_token)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError,
                ValueError) as exc:
            raise WorkloadAuthenticationUnavailableError(
                "issuer current-status observation unavailable"
            ) from exc
        except WorkloadAuthenticationUnavailableError:
            raise
        if status.get("active") is not True:
            raise WorkloadAuthenticationError("issuer revoked or inactive bearer")
        aud = status.get("aud")
        audiences = [aud] if isinstance(aud, str) else aud
        scope = status.get("scope")
        expiry = status.get("exp")
        if (
            status.get("iss") != self._issuer
            or status.get("sub") != signed_caller.subject
            or status.get("client_id") != signed_caller.client_id
            or not isinstance(audiences, list)
            or audiences != [self._audience]
            or not isinstance(scope, str)
            or frozenset(scope.split()) != signed_caller.scopes
            or type(expiry) is not int or expiry <= int(time.time())
        ):
            raise WorkloadAuthenticationError("current issuer status differs from signed bearer")
        return signed_caller

    def _status(self, token: str) -> Mapping[str, object]:
        request = urllib.request.Request(
            self._url,
            data=urllib.parse.urlencode({
                "token": token, "token_type_hint": "access_token",
            }).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": self._basic,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Cache-Control": "no-store",
            },
        )
        with self._opener.open(request, timeout=self._timeout) as response:
            if response.status != 200:
                raise WorkloadAuthenticationUnavailableError(
                    "issuer current-status HTTP outcome unknown"
                )
            raw = response.read(8193)
        if len(raw) > 8192:
            raise ValueError("issuer status response exceeds limit")
        data = json.loads(raw, object_pairs_hook=_no_duplicate_fields)
        if not isinstance(data, dict):
            raise ValueError("issuer status is not a JSON object")
        return cast(Mapping[str, object], data)


__all__ = ["CurrentIssuerStatusWorkloadAuthenticator"]
