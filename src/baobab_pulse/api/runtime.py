"""Runtime dependencies for canonical Pulse capability routes."""

from dataclasses import dataclass

from baobab_pulse.application.ports.authentication import WorkloadAuthenticatorPort
from baobab_pulse.application.services.evidence_search_capability import EvidenceSearchCapabilityService
from baobab_pulse.application.services.research_mission_manage_capability import (
    ResearchMissionManageCapabilityService,
)


@dataclass(frozen=True, slots=True)
class CapabilityApiRuntime:
    """Dependencies required before canonical intelligence routes can serve traffic."""

    authenticator: WorkloadAuthenticatorPort
    evidence_search: EvidenceSearchCapabilityService
    research_missions: ResearchMissionManageCapabilityService | None = None


__all__ = ["CapabilityApiRuntime"]
