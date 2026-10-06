"""Base types every canonical entity and domain event builds on.

``CanonicalIdentity`` fields per ARCH-PULSE-CIM-001 §4: every canonical
entity SHALL have ``id``, ``type``, ``created_at``, ``updated_at``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from baobab_pulse.domain.shared.enums import Classification, TenantScope
from baobab_pulse.domain.shared.value_objects import TenantContext


class CanonicalEntity(BaseModel):
    """Base for every Pulse canonical entity (aggregate root or subordinate).

    ``type`` is a serialized discriminator (e.g. ``"observation"``,
    ``"evidence_set"``) — every concrete subclass overrides it with a
    ``Literal`` default, per ARCH-PULSE-CIM-001 §4. It is a real field, not
    a Python-only class attribute, because it must survive serialization
    (events, persistence, API responses).

    Concrete entities that ADR-PULSE-002 §63 / CIM §63 require to be
    versioned/immutable (Dataset, Observation, EvidenceSet, Insight,
    Forecast, Recommendation, Model, IntelligenceProduct) additionally set
    ``model_config = ConfigDict(frozen=True)`` in their own class and expose
    ``supersedes_id`` / ``superseded_by_id`` rather than in-place mutation.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GovernedEntity(CanonicalEntity):
    """A :class:`CanonicalEntity` that additionally carries tenancy and
    classification context, i.e. every entity that participates in the
    evidence/intelligence chain rather than pure platform metadata.

    ``tenant_scope`` (ARCH-PULSE-CIM-001 §99) is the isolation-policy axis —
    how broadly this object may apply (a ``GLOBAL`` World Bank observation
    vs. a ``PRIVATE`` tenant record) — and is always set. ``tenant_context``
    (CIM §5) is the actual Control-Plane-minted reference; it is ``None``
    for ``GLOBAL``/``PLATFORM``-scoped objects (there is no single tenant to
    reference) and required for ``TENANT``/``CONTEXT``/``PRIVATE``-scoped
    ones — never the ``TenantScope`` enum value itself standing in for an
    identifier (INV-PULSE-004: Pulse never mints or fakes a Control Plane
    identity).
    """

    tenant_scope: TenantScope
    tenant_context: TenantContext | None = None
    classification: Classification

    def check_tenant_context(self) -> None:
        from baobab_pulse.domain.shared.errors import InvariantViolation

        requires_context = self.tenant_scope in (TenantScope.TENANT, TenantScope.CONTEXT, TenantScope.PRIVATE)
        if requires_context and self.tenant_context is None:
            raise InvariantViolation(
                f"tenant_scope={self.tenant_scope.value} requires a tenant_context reference"
            )


class DomainEvent(BaseModel):
    """Base for in-process domain events (ADR-PULSE-002 §71 gives the exact
    PascalCase event list, e.g. ``ObservationRecorded``, ``InsightPublished``).

    This is distinct from the wire event envelope in
    ``baobab_pulse.contracts.events`` (the CloudEvents-profile envelope
    ``baobab-platform/shared`` defines): a domain event is an in-process fact; a
    future publisher maps it to the reserved domain-oriented
    ``com.baobab-platform.intelligence.<entity>.<verb>.v1`` namespace. RTD-09
    activates no Pulse-produced event type. The domain never constructs the
    wire envelope itself — see ``infrastructure.messaging.outbox``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    subject_id: str
    tenant_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    payload: dict[str, Any] = {}
