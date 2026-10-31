"""N03 original proof runner: source-only negatives, NEVER connected evidence."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "n03_native_development.py"
SPEC = importlib.util.spec_from_file_location("pulse_n03_real_source", SCRIPT)
assert SPEC and SPEC.loader
native = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native)


@pytest.mark.parametrize("bad", [
    "http://iam.example.invalid", "file:///etc/passwd",
    "https://username:secret@iam.example.invalid",
    "https://iam.example.invalid/path", "https://iam.example.invalid/?x=1",
    "http://127.0.0.1.attacker.invalid",
])
def test_native_probes_refuse_untrusted_provider_origins(bad: str) -> None:
    with pytest.raises(native.Refused):
        native.origin(bad)


def test_https_and_exact_development_loopback_only() -> None:
    assert native.origin("https://iam.example.invalid") == "https://iam.example.invalid"
    assert native.origin("http://127.0.0.1:4444") == "http://127.0.0.1:4444"


def test_original_never_overwritten_or_misrepresented_as_protected() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        root.chmod(0o700)
        data = {
            "run_id": "a" * 32,
            "pulse_source_sha": "b" * 40,
            "iam_source_sha": "c" * 40,
            "cp_source_sha": "d" * 40,
            "shared_source_sha": "e" * 40,
        }
        statuses = dict.fromkeys(native.CASES, "OBSERVED")
        with patch.dict(os.environ, {"PULSE_N03_EVIDENCE_DIR": folder}):
            native.write_original(data, statuses)
            record = root / "native-observation.json"
            digest = root / "native-observation.sha256"
            assert stat.S_IMODE(record.stat().st_mode) == 0o600
            assert stat.S_IMODE(digest.stat().st_mode) == 0o600
            assert digest.read_text().strip() == hashlib.sha256(record.read_bytes()).hexdigest()
            payload = json.loads(record.read_text())
            assert payload["two_tenants_independently_attested"] is False
            assert payload["protected_accepted"] is False
            assert payload["classification"].endswith("_UNATTESTED")
            assert all("token" not in key for key in payload)
            with pytest.raises(FileExistsError):
                native.write_original(data, statuses)
            assert hashlib.sha256(record.read_bytes()).hexdigest() == digest.read_text().strip()


def test_skipped_or_missing_case_cannot_publish_original() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        root.chmod(0o700)
        data = dict.fromkeys(("run_id", "pulse_source_sha", "iam_source_sha",
                              "cp_source_sha", "shared_source_sha"), "a" * 40)
        cases = dict.fromkeys(native.CASES, "OBSERVED")
        cases[native.CASES[0]] = "BLOCKED"
        with patch.dict(os.environ, {"PULSE_N03_EVIDENCE_DIR": folder}):
            with pytest.raises(native.Refused):
                native.write_original(data, cases)
        assert list(root.iterdir()) == []


def test_missing_runtime_does_not_create_a_pass() -> None:
    record = {
        "hydra_origin": "https://iam.example.invalid",
        "pulse_origin": "https://pulse.example.invalid",
        "clients": [
            {"client_id": native.ALLOWED_CLIENTS[0], "secret_file": "/dev/null",
             "context_id": "11111111-1111-4111-8111-111111111111"},
            {"client_id": native.ALLOWED_CLIENTS[1], "secret_file": "/dev/null",
             "context_id": "22222222-2222-4222-8222-222222222222"},
        ],
        "issuer_observer": {"client_id": "distinct", "secret_file": "/dev/null"},
    }
    with patch.object(native, "issue", side_effect=native.Refused("N03_NO_REAL_HYDRA")):
        with pytest.raises(native.Refused, match="N03_NO_REAL_HYDRA"):
            native.execute(record)


def test_source_claim_mismatch_and_dirty_checkout_refuse() -> None:
    private = {
        "schema": "baobab.pulse.n03.native-dev.v1",
        "environment": "development",
        "protected_accepted": False,
        "run_id": "a" * 32,
        "pulse_source_sha": "b" * 40,
        "iam_source_sha": "c" * 40,
        "cp_source_sha": "d" * 40,
        "shared_source_sha": "e" * 40,
    }
    for revision, dirty in (("f" * 40, ""), ("b" * 40, " M scripts/n03_native_development.py")):
        with (
            patch.dict(os.environ, {
                "BAOBAB_ENVIRONMENT": "development",
                "PULSE_N03_PRIVATE_PROFILE": "/private/source.json",
            }),
            patch.object(native, "private_file", return_value=json.dumps(private).encode()),
            patch.object(native.subprocess, "run", side_effect=[
                SimpleNamespace(stdout=revision + "\n"),
                SimpleNamespace(stdout=dirty),
            ]),
        ):
            with pytest.raises(native.Refused, match="N03_LOCAL_SOURCE_PIN_DRIFT"):
                native.profile()
