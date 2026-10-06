"""Evidence and EvidenceSet.

"Evidence references one or more observations, source artefacts, events or
documents used to support a later analytical conclusion... Evidence MUST
remain independently inspectable." (ARCH-PULSE-001 §29). Evidence "does not
copy the underlying item. It references and contextualises it."
(ARCH-PULSE-CIM-001 §31-33).

AGG-PULSE-006: EvidenceSets used for published intelligence SHALL be
historically frozen — hence ``frozen=True`` and a ``freeze()`` factory rather
than an in-place append after ``frozen_at`` is set.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict

from baobab_pulse.domain.shared.base import CanonicalEntity, GovernedEntity
from baobab_pulse.domain.shared.enums import ConfidenceBand, EvidenceDirection
from baobab_pulse.domain.shared.errors import InvariantViolation
from baobab_pulse.domain.shared.value_objects import CrossEngineObjectReference, Reference


class Evidence(CanonicalEntity):
    """A single contextualised reference within an :class:`EvidenceSet`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["evidence"] = "evidence"
    referenced_object: Reference | CrossEngineObjectReference
    role: str | None = None
    relevance: ConfidenceBand = ConfidenceBand.UNKNOWN
    direction: EvidenceDirection = EvidenceDirection.CONTEXTUAL
    weight: float | None = None
    quality: ConfidenceBand = ConfidenceBand.UNKNOWN
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    metadata: dict[str, str] = {}


class EvidenceSet(GovernedEntity):
    """Aggregate root. Invariants (ADR-PULSE-002 §2.2): a published
    EvidenceSet SHALL contain >= 1 entry, contain no dangling references,
    and record its classification and contextual scope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["evidence_set"] = "evidence_set"
    purpose: str
    scope: str | None = None
    entries: tuple[Evidence, ...] = ()
    frozen_at: datetime | None = None
    version: int = 1

    def check_invariants(self) -> None:
        if self.frozen_at is not None and not self.entries:
            raise InvariantViolation("a frozen EvidenceSet must contain at least one entry")

    def freeze(self, *, at: datetime) -> EvidenceSet:
        """Return a frozen copy — never mutate ``entries`` after freezing."""
        if not self.entries:
            raise InvariantViolation("cannot freeze an EvidenceSet with no entries")
        return self.model_copy(update={"frozen_at": at})
