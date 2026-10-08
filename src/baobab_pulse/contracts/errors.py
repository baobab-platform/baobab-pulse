"""RFC 9457 problem+json error contract.

Field-for-field mirror of ``baobab-platform/shared``'s
``contracts/errors/v1/problem-details.schema.json`` (vendored at
``tests/fixtures/contracts/problem-details.schema.json``). This is the only
shape Pulse's public API returns for an error response (item 120: Haystack
and provider exceptions are translated at the anti-corruption boundary and
SHALL NOT leak framework-specific exception structures through the public
API) — see ``api.error_handlers``.
"""

from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
_TRACE_ID_PATTERN = re.compile(r"^(?!00000000000000000000000000000000)[0-9a-f]{32}$")


class ProblemDetailError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(pattern=_CODE_PATTERN.pattern, max_length=100)
    field: str | None = Field(default=None, min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=500)


class ProblemDetails(BaseModel):
    """``application/problem+json`` response body."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: str
    title: str = Field(min_length=1, max_length=120)
    status: int = Field(ge=400, le=599)
    detail: str | None = Field(default=None, max_length=2048)
    instance: str | None = Field(default=None, max_length=512)
    code: str = Field(pattern=_CODE_PATTERN.pattern, max_length=100)
    correlation_id: UUID
    trace_id: str | None = None
    retryable: bool
    errors: tuple[ProblemDetailError, ...] | None = Field(default=None, max_length=50)

    @field_validator("trace_id")
    @classmethod
    def _validate_trace_id(cls, value: str | None) -> str | None:
        # See contracts.events for why this can't be a Field(pattern=...):
        # pydantic-core's Rust regex engine doesn't support the negative
        # look-ahead the org's schema uses to reject the all-zero trace id.
        if value is not None and not _TRACE_ID_PATTERN.match(value):
            raise ValueError("trace_id must be a 32-character lowercase hex string, not all zeros")
        return value
