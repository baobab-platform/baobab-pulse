"""Translate every error into ``application/problem+json`` (item 120).

No Haystack, asyncpg, or other infrastructure exception structure ever
reaches an HTTP response — everything is mapped to
``contracts.errors.ProblemDetails`` here, at the outermost boundary.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from baobab_pulse.contracts.errors import ProblemDetails
from baobab_pulse.domain.shared.errors import (
    CapabilityAccessDeniedError,
    CapabilityAuthenticationError,
    CapabilityAuthorityUnavailableError,
    CapabilityContextNotFoundError,
    CapabilityInvalidRequestError,
    CapabilityRuntimeUnavailableError,
    InvariantViolation,
    ProjectionRebuildFailed,
    ResearchMissionNotFoundError,
    ProjectionWriteFailed,
    PulseError,
    SemanticRetrievalUnavailable,
    TenantContextMissingError,
    VectorStoreUnavailable,
)
from baobab_pulse.infrastructure.haystack.errors import PulseHaystackError

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: tuple[tuple[type[PulseError], int, str, bool], ...] = (
    (CapabilityInvalidRequestError, 400, "CAPABILITY_REQUEST_INVALID", False),
    (CapabilityAuthenticationError, 401, "AUTH_TOKEN_INVALID", False),
    (CapabilityAccessDeniedError, 403, "CAPABILITY_ACCESS_DENIED", False),
    (CapabilityContextNotFoundError, 404, "CONTEXT_NOT_FOUND", False),
    (ResearchMissionNotFoundError, 404, "RESEARCH_MISSION_NOT_FOUND", False),
    (CapabilityAuthorityUnavailableError, 503, "CAPABILITY_AUTHORITY_UNAVAILABLE", True),
    (CapabilityRuntimeUnavailableError, 503, "CAPABILITY_RUNTIME_UNAVAILABLE", True),
    (TenantContextMissingError, 400, "TENANT_CONTEXT_MISSING", False),
    (InvariantViolation, 422, "DOMAIN_INVARIANT_VIOLATION", False),
    # Semantic retrieval/projection failures are Qdrant-specific and
    # retryable — never confused with "Pulse is down" (item 36-37): a
    # canonical PostgreSQL write can still succeed while these are failing.
    (SemanticRetrievalUnavailable, 503, "SEMANTIC_RETRIEVAL_UNAVAILABLE", True),
    (VectorStoreUnavailable, 503, "VECTOR_STORE_UNAVAILABLE", True),
    (ProjectionWriteFailed, 502, "PROJECTION_WRITE_FAILED", True),
    (ProjectionRebuildFailed, 502, "PROJECTION_REBUILD_FAILED", True),
    (PulseHaystackError, 502, "INTELLIGENCE_ENGINE_UNAVAILABLE", True),
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PulseError)
    async def handle_pulse_error(request: Request, exc: PulseError) -> JSONResponse:
        status_code, code, retryable = 500, "PULSE_INTERNAL_ERROR", False
        for error_type, mapped_status, mapped_code, mapped_retryable in _STATUS_BY_ERROR:
            if isinstance(exc, error_type):
                status_code, code, retryable = mapped_status, mapped_code, mapped_retryable
                break
        problem = ProblemDetails(
            type=f"https://contracts.baobab-platform.com/errors/v1/{code.lower()}",
            title=type(exc).__name__,
            status=status_code,
            detail=str(exc),
            code=code,
            correlation_id=uuid4(),
            retryable=retryable,
        )
        return JSONResponse(
            status_code=status_code,
            content=problem.model_dump(mode="json", exclude_none=True),
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception")
        problem = ProblemDetails(
            type="https://contracts.baobab-platform.com/errors/v1/internal_error",
            title="Internal Server Error",
            status=500,
            detail="An unexpected error occurred.",
            code="INTERNAL_ERROR",
            correlation_id=uuid4(),
            retryable=False,
        )
        return JSONResponse(
            status_code=500,
            content=problem.model_dump(mode="json", exclude_none=True),
            media_type="application/problem+json",
        )
