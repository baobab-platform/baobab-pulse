"""Validates ``PulseEventEnvelope`` against the vendored ``baobab-platform/shared``
event-envelope JSON Schema (item 98-99).

The vendored copy lives at ``tests/fixtures/contracts/events/v1/`` in the
same relative layout as the real repository (with
``contracts/control-plane/v1/domain.schema.json`` alongside it, since the
envelope schema ``$ref``s that file for ``tenantid``) — re-copy both files
from ``baobab-platform/shared`` whenever that repository's contract changes.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from baobab_pulse.contracts.events import PulseEventEnvelope, build_event_type

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "contracts"


def _validator() -> Draft202012Validator:
    envelope_schema = json.loads((FIXTURES / "events" / "v1" / "envelope.schema.json").read_text())
    domain_schema = json.loads((FIXTURES / "control-plane" / "v1" / "domain.schema.json").read_text())

    registry = Registry().with_resources(
        [
            (envelope_schema["$id"], Resource.from_contents(envelope_schema)),
            (domain_schema["$id"], Resource.from_contents(domain_schema)),
        ]
    )
    return Draft202012Validator(envelope_schema, registry=registry)


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    return _validator()


def test_tenant_scoped_envelope_matches_the_org_schema(validator: Draft202012Validator) -> None:
    envelope = PulseEventEnvelope(
        id=uuid4(),
        type=build_event_type("insight", "published"),
        source="urn:baobab-platform:service:baobab-pulse",
        subject="ins_123",
        time="2026-01-01T00:00:00Z",
        dataschema="https://contracts.baobab-platform.com/pulse/events/v1/insight.published.schema.json",
        baobabscope="tenant",
        correlationid=uuid4(),
        tenantid="tn_acme01",
        data={"insight_id": "ins_123"},
    )
    instance = json.loads(envelope.to_wire_json())
    validator.validate(instance)


def test_platform_scoped_envelope_matches_the_org_schema(validator: Draft202012Validator) -> None:
    envelope = PulseEventEnvelope(
        id=uuid4(),
        type=build_event_type("source", "registered"),
        source="urn:baobab-platform:service:baobab-pulse",
        subject="src_123",
        time="2026-01-01T00:00:00Z",
        dataschema="https://contracts.baobab-platform.com/pulse/events/v1/source.registered.schema.json",
        baobabscope="platform",
        correlationid=uuid4(),
        data={"source_id": "src_123"},
    )
    instance = json.loads(envelope.to_wire_json())
    validator.validate(instance)


def test_tenant_scope_without_tenantid_is_rejected_before_it_ever_reaches_the_schema() -> None:
    with pytest.raises(ValueError, match="tenantid is required"):
        PulseEventEnvelope(
            id=uuid4(),
            type=build_event_type("insight", "published"),
            source="urn:baobab-platform:service:baobab-pulse",
            subject="ins_123",
            time="2026-01-01T00:00:00Z",
            dataschema="https://contracts.baobab-platform.com/pulse/events/v1/insight.published.schema.json",
            baobabscope="tenant",
            correlationid=uuid4(),
            data={},
        )
