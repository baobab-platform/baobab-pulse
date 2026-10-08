"""Repository ports.

ADR-PULSE-002 §76 names one repository interface per aggregate root
(``SourceRepository``, ``ObservationRepository``, ...). Rather than hand-write
fifteen near-identical interfaces, this module defines one generic
``Repository[T]`` ``Protocol`` and then binds it to each named alias the ADR
specifies — the contract is identical to writing them out by hand, without
the duplication. A concrete infrastructure adapter still implements one
``Protocol`` per aggregate (e.g. ``InMemoryObservationRepository``), it just
does so against ``Repository[Observation]`` rather than a bespoke ABC.

Query-side interfaces (ADR-PULSE-002 §77, e.g. ``EvidenceTraceQuery``,
``DecisionAuditQuery``) are intentionally not stubbed here — they cut across
aggregates and should be designed once a real read-model/query need exists,
not speculatively (req. 128: no decorative boilerplate).
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from baobab_pulse.domain.analysis import Analysis
from baobab_pulse.domain.decisions import Decision
from baobab_pulse.domain.evidence import EvidenceSet
from baobab_pulse.domain.forecasting import Forecast
from baobab_pulse.domain.insights import Insight
from baobab_pulse.domain.models import Model
from baobab_pulse.domain.observations import Observation
from baobab_pulse.domain.opportunities import Opportunity
from baobab_pulse.domain.products import IntelligenceProduct
from baobab_pulse.domain.recommendations import Recommendation
from baobab_pulse.domain.research import ResearchMission
from baobab_pulse.domain.risks import Risk
from baobab_pulse.domain.signals import Signal
from baobab_pulse.domain.sources import Source

T = TypeVar("T")


class Repository(Protocol[T]):
    """Minimal persistence port every aggregate repository implements.

    Deliberately narrow: Pulse's application services express intent
    (``record_observation``, ``freeze_evidence_set``, ...), not generic CRUD,
    so ``Repository[T]`` only needs to get an aggregate by id and persist one.
    """

    async def get(self, entity_id: str) -> T | None: ...

    async def add(self, entity: T) -> None: ...


SourceRepository = Repository[Source]
ObservationRepository = Repository[Observation]
EvidenceSetRepository = Repository[EvidenceSet]
SignalRepository = Repository[Signal]
AnalysisRepository = Repository[Analysis]
InsightRepository = Repository[Insight]
OpportunityRepository = Repository[Opportunity]
RiskRepository = Repository[Risk]
ForecastRepository = Repository[Forecast]
RecommendationRepository = Repository[Recommendation]
DecisionRepository = Repository[Decision]
ModelRepository = Repository[Model]
IntelligenceProductRepository = Repository[IntelligenceProduct]
ResearchMissionRepository = Repository[ResearchMission]


class EvidenceSetHydrationPort(Protocol):
    """Extends the plain ``EvidenceSetRepository`` with the text-resolution
    read ``application.services.evidence_retrieval_service`` needs to
    hydrate a canonical ``EvidenceSet`` *and* the text its Evidence entries
    were projected/embedded from (Qdrant refactor item 28-29) — Evidence
    itself carries no text, so canonical hydration means resolving both.

    A separate ``Protocol`` rather than adding this to ``Repository[T]``:
    every other aggregate's repository has no equivalent need today, and
    ``Repository[T]`` stays the minimal, uniform shape ADR-PULSE-002 §76
    describes."""

    async def get_with_text(self, entity_id: str) -> tuple[EvidenceSet, dict[str, str]] | None: ...

    async def current_version(self, entity_id: str) -> int | None: ...
