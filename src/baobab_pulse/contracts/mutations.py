"""Transport-independent helpers for mutation idempotency semantics."""

from __future__ import annotations

import hashlib
import json
import re

from baobab_pulse.contracts.api.research_missions import ResearchMissionCreateRequest

IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
IDEMPOTENCY_KEY_MIN_LENGTH = 16
IDEMPOTENCY_KEY_MAX_LENGTH = 128


def validate_idempotency_key(value: str) -> str:
    candidate = value.strip()
    if not (
        IDEMPOTENCY_KEY_MIN_LENGTH
        <= len(candidate)
        <= IDEMPOTENCY_KEY_MAX_LENGTH
    ):
        raise ValueError("Idempotency-Key must contain 16 to 128 characters")
    if IDEMPOTENCY_KEY_PATTERN.fullmatch(candidate) is None:
        raise ValueError(
            "Idempotency-Key must match [A-Za-z0-9][A-Za-z0-9._:-]*"
        )
    return candidate


def canonical_create_request_json(request: ResearchMissionCreateRequest) -> str:
    return json.dumps(
        request.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def create_request_fingerprint(request: ResearchMissionCreateRequest) -> str:
    canonical = canonical_create_request_json(request)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "canonical_create_request_json",
    "create_request_fingerprint",
    "validate_idempotency_key",
]
