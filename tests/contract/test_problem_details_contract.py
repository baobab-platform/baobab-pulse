"""Validates ``ProblemDetails`` against the vendored ``baobab-platform/shared``
problem-details JSON Schema."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator

from baobab_pulse.contracts.errors import ProblemDetails

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "contracts"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads((FIXTURES / "errors" / "v1" / "problem-details.schema.json").read_text())
    return Draft202012Validator(schema)


def test_problem_details_matches_the_org_schema(validator: Draft202012Validator) -> None:
    problem = ProblemDetails(
        type="https://contracts.baobab-platform.com/errors/v1/domain_invariant_violation",
        title="InvariantViolation",
        status=422,
        detail="an EvidenceSet must contain at least one entry",
        code="DOMAIN_INVARIANT_VIOLATION",
        correlation_id=uuid4(),
        retryable=False,
    )
    instance = json.loads(problem.model_dump_json(exclude_none=True))
    validator.validate(instance)


def test_problem_details_with_field_errors_matches_the_org_schema(validator: Draft202012Validator) -> None:
    problem = ProblemDetails(
        type="https://contracts.baobab-platform.com/errors/v1/validation_error",
        title="Validation Error",
        status=400,
        code="VALIDATION_ERROR",
        correlation_id=uuid4(),
        retryable=False,
        errors=(
            {"code": "FIELD_REQUIRED", "field": "tenant_id", "message": "tenant_id is required"},
        ),
    )
    instance = json.loads(problem.model_dump_json(exclude_none=True))
    validator.validate(instance)
