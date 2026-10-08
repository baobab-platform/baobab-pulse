"""The Baobab cross-engine event envelope (CloudEvents 1.0 profile).

Field-for-field mirror of ``baobab-platform/shared``'s
``contracts/events/v1/envelope.schema.json`` (vendored for offline contract
testing at ``tests/fixtures/contracts/envelope.schema.json`` — see
``tests/contract/test_event_envelope_contract.py``). Do not add, rename, or
loosen a field here without updating that vendored copy and re-confirming
against the live schema in ``baobab-platform/shared`` — this module has no authority
of its own over the shape, it only implements it.

Pulse never emits an event without going through
``infrastructure.messaging.outbox`` — an application service never
constructs a :class:`PulseEventEnvelope` inline in a request handler.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_TYPE_PATTERN = re.compile(r"^com\.baobab-platform\.[a-z0-9]+(?:[.-][a-z0-9]+)*\.v[1-9][0-9]*$")
_TRACEPARENT_PATTERN = re.compile(
    r"^00-(?!00000000000000000000000000000000)[0-9a-f]{32}-(?!0000000000000000)[0-9a-f]{16}-[0-9a-f]{2}$"
)
_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_TENANT_ID_PATTERN = re.compile(r"^tn_[a-z0-9]+$")
"""Control Plane-minted tenant id shape (``baobab-platform/shared``
``contracts/control-plane/v1/domain.schema.json#/$defs/tenantId``) — Pulse
never mints this identifier itself, it only carries what the Control Plane
issued (INV-PULSE-004)."""


class PulseEventEnvelope(BaseModel):
    """A local Pulse envelope for a future ``com.baobab-platform.intelligence.<entity>.<verb>.vN`` event.

    RTD-09 reserves the intelligence context but activates no producer event.
    P-CAP-05 may persist an envelope-shaped candidate only when its durable
    outbox state is HELD_UNREGISTERED; this model does not itself authorize
    publication.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    specversion: Literal["1.0"] = "1.0"
    id: UUID
    type: str = Field(pattern=_TYPE_PATTERN.pattern, max_length=255)
    source: str = Field(max_length=255)
    subject: str = Field(min_length=1, max_length=255)
    time: datetime
    datacontenttype: Literal["application/json"] = "application/json"
    dataschema: str = Field(max_length=512)
    baobabscope: Literal["platform", "tenant"]
    correlationid: UUID
    causationid: UUID | None = None
    tenantid: str | None = Field(default=None, pattern=_TENANT_ID_PATTERN.pattern, min_length=6, max_length=63)
    idempotencykey: str | None = Field(
        default=None, pattern=_IDEMPOTENCY_KEY_PATTERN.pattern, min_length=16, max_length=128
    )
    traceparent: str | None = None
    tracestate: str | None = Field(default=None, min_length=1, max_length=512)
    data: dict[str, Any]

    @field_validator("traceparent")
    @classmethod
    def _validate_traceparent(cls, value: str | None) -> str | None:
        # pydantic-core's Rust regex engine has no look-around support, and
        # the org's traceparent pattern needs it (excluding the all-zero
        # trace/span ids) — validated here with Python's `re` instead of a
        # `Field(pattern=...)` constraint.
        if value is not None and not _TRACEPARENT_PATTERN.match(value):
            raise ValueError("traceparent does not match the W3C Trace Context v00 format")
        return value

    @model_validator(mode="after")
    def _tenant_scope_rule(self) -> PulseEventEnvelope:
        if self.baobabscope == "tenant" and self.tenantid is None:
            raise ValueError("tenantid is required when baobabscope is 'tenant'")
        if self.baobabscope == "platform" and self.tenantid is not None:
            raise ValueError("tenantid must not be set when baobabscope is 'platform'")
        return self

    def to_wire_json(self) -> str:
        """The only correct serialization for this envelope.

        The org schema's optional fields (``causationid``, ``tenantid``,
        ``idempotencykey``, ``traceparent``, ``tracestate``) are typed
        ``string``, not ``["string", "null"]`` — an absent key is valid, an
        explicit JSON ``null`` is not (its own docstring: "do not send
        null"). Plain ``model_dump_json()`` would include those as ``null``
        and fail schema validation; every real emission path (the outbox)
        MUST use this method instead.
        """
        return self.model_dump_json(exclude_none=True)


def build_event_type(entity: str, verb: str, *, version: int = 1) -> str:
    """Build a future ``com.baobab-platform.intelligence.<entity>.<verb>.vN`` type.

    Shared currently reserves, but does not activate, the intelligence event
    context. This helper is therefore local scaffold only until a future
    Shared event-registration decision lands.
    """
    event_type = f"com.baobab-platform.intelligence.{entity}.{verb}.v{version}"
    if not _TYPE_PATTERN.match(event_type):
        raise ValueError(f"constructed event type {event_type!r} does not match the org's event-type pattern")
    return event_type
