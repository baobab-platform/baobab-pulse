"""Architecture guards for ADR-PULSE-013 / RTD-09."""

from __future__ import annotations

import ast
from pathlib import Path

from baobab_pulse.contracts.events import build_event_type
from baobab_pulse.domain.projections import UpstreamFactProjection
from baobab_pulse.domain.shared.base import CanonicalEntity
from baobab_pulse.domain.shared.value_objects import ValueObject

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "baobab_pulse"

_FORBIDDEN_FOREIGN_AGGREGATES = {
    "RegulatoryInstrument",
    "RegulatoryRule",
    "RegulatoryDecision",
    "DocumentRequirement",
    "PermitRequirement",
    "EvidenceRequirement",
    "TradeDocument",
    "DocumentVersion",
    "CustomsCase",
}

_FORBIDDEN_PROJECTOR_IMPORT_PREFIXES = (
    "httpx",
    "requests",
    "asyncpg",
    "sqlalchemy",
    "haystack",
    "qdrant_client",
    "haystack_integrations",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def test_rtd09_projector_has_no_synchronous_upstream_or_provider_dependency() -> None:
    path = SRC_ROOT / "application" / "services" / "upstream_fact_projection_service.py"
    violations = [
        module
        for module in _imports(path)
        if module.startswith(_FORBIDDEN_PROJECTOR_IMPORT_PREFIXES)
    ]
    assert not violations, f"RTD-09 projector imported forbidden dependencies: {violations}"


def test_upstream_fact_projection_is_a_value_object_not_a_canonical_aggregate() -> None:
    assert issubclass(UpstreamFactProjection, ValueObject)
    assert not issubclass(UpstreamFactProjection, CanonicalEntity)


def test_pulse_domain_does_not_define_foreign_canonical_aggregate_classes() -> None:
    found: set[str] = set()
    for path in (SRC_ROOT / "domain").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found.update(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name in _FORBIDDEN_FOREIGN_AGGREGATES
        )
    assert not found, f"Pulse must not define foreign canonical aggregates: {sorted(found)}"


def test_future_local_event_scaffold_uses_intelligence_not_repository_name() -> None:
    event_type = build_event_type("insight", "published")
    assert event_type == "com.baobab-platform.intelligence.insight.published.v1"
    assert ".pulse." not in event_type
