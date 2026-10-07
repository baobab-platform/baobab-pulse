"""``/evidence/search`` request/response schemas (Qdrant refactor item 42).

Deliberately exposes only ``canonical_object_id``/``evidence_set_id``/
``score``/``is_stale`` — never a Qdrant point id, payload, or raw vector
(item 14: no Qdrant SDK type in a canonical contract).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EvidenceSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_text: str = Field(min_length=1, max_length=2000)
    evidence_set_id: str | None = Field(default=None, min_length=1, max_length=128)
    top_k: int = Field(default=10, ge=1, le=100)


class EvidenceCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_object_id: str = Field(min_length=1, max_length=128)
    evidence_set_id: str = Field(min_length=1, max_length=128)
    score: float
    is_stale: bool


class EvidenceSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: tuple[EvidenceCandidateResponse, ...] = Field(max_length=100)
