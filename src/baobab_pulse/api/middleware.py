"""Tenant-context and correlation-id propagation (item 48, 57, 77).

Legacy routes may bind a :class:`TenantContext` from the historical tenant
header. Canonical capability routes never use that header as authority:
``/evidence/search`` obtains its tenant exclusively from caller-bound
Control Plane context validation in P-CAP-03. A request with no resolvable tenant is not rejected here (some
resources, e.g. ``/healthz``, are legitimately tenant-free) — it simply
never gets a bound context, and any handler downstream that needs one gets
a :class:`~baobab_pulse.domain.shared.errors.TenantContextMissingError` if
it tries.
"""

from __future__ import annotations

from contextlib import nullcontext
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from baobab_pulse.domain.shared.value_objects import TenantContext
from baobab_pulse.tenancy.context import bind_tenant_context

_TENANT_HEADER = "X-Baobab-Tenant-Id"
_CORRELATION_HEADER = "X-Correlation-Id"


class TenancyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get(_CORRELATION_HEADER, str(uuid4()))
        request.state.correlation_id = correlation_id

        # P-CAP-03: the canonical evidence capability must not even transiently
        # bind caller-selected tenant authority. Its application adapter binds
        # the Control-Plane-validated tenant in a nested, request-local context.
        canonical_context_bound = request.url.path in {
            "/evidence/search",
            "/research-missions/manage",
        }
        tenant_id = None if canonical_context_bound else request.headers.get(_TENANT_HEADER)
        context = bind_tenant_context(TenantContext(tenant_id=tenant_id)) if tenant_id else nullcontext()
        with context:
            response = await call_next(request)
        response.headers[_CORRELATION_HEADER] = str(
            getattr(request.state, "correlation_id", correlation_id)
        )
        return response
