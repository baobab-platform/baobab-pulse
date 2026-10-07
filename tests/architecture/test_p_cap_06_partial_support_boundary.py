"""P-CAP-06 promotion ceiling: PARTIAL must remain an honest runtime claim."""

from pathlib import Path

import yaml

from baobab_pulse.api.main import app

ROOT = Path(__file__).resolve().parents[2]


def test_repository_is_active_because_it_now_declares_real_provider_support() -> None:
    repository = yaml.safe_load((ROOT / ".baobab" / "repository.yaml").read_text())
    assert repository["repository"]["lifecycle"] == "active"
    assert "engine" in repository["capabilities"]


def test_default_asgi_composition_has_no_canonical_capability_runtime_yet() -> None:
    # Repository lifecycle active means this is a real engine repository under
    # Foundation governance. It does not mean its PARTIAL provider support is
    # runtime ACTIVE in Control Plane.
    assert app.state.capability_runtime is None
