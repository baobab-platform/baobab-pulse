"""Canonical Shared-v1 ResearchMission capability request/response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from baobab_pulse.domain.research import ResearchMission, ResearchMissionStatus
from baobab_pulse.domain.shared.enums import Classification, ConfidenceBand, TenantScope


class ResearchMissionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["CREATE"]
    title: str = Field(min_length=1, max_length=300)
    research_question: str = Field(min_length=1, max_length=4000)
    tenant_scope: TenantScope
    classification: Classification
    confidence_requirement: ConfidenceBand


class ResearchMissionGetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["GET"]
    research_mission_id: str = Field(min_length=1, max_length=128)


ResearchMissionManageRequest = ResearchMissionCreateRequest | ResearchMissionGetRequest


class ResearchMissionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=300)
    research_question: str = Field(min_length=1, max_length=4000)
    status: ResearchMissionStatus
    tenant_scope: TenantScope
    classification: Classification
    confidence_requirement: ConfidenceBand

    @classmethod
    def from_domain(cls, mission: ResearchMission) -> ResearchMissionResponse:
        return cls(
            id=mission.id,
            title=mission.title,
            research_question=mission.research_question,
            status=mission.status,
            tenant_scope=mission.tenant_scope,
            classification=mission.classification,
            confidence_requirement=mission.confidence_requirement,
        )
