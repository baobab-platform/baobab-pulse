"""P-CAP-06 promotion ceiling: PARTIAL must remain an honest runtime claim."""

from baobab_pulse.api.main import app


def test_default_asgi_composition_has_no_canonical_capability_runtime_yet() -> None:
    # P-CAP-06 is repository implementation evidence, not proof that the
    # production ASGI composition has IAM/Control Plane adapters wired.
    assert app.state.capability_runtime is None
