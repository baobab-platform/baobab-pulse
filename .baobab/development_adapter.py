#!/usr/bin/env python3
"""DEV-15 Pulse native owner adapter; host-side, never a CP/IAM authority.

The common Infrastructure executor owns run leases, token issuance, grants,
image pins and teardown. This adapter observes actual Pulse health and runs
owner migrations only against a supplied disposable development database.
Unimplemented domain/authority phases remain BLOCKED, never manufactured PASS.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

PHASES = ("readiness", "migrate", "seed", "exercise", "cleanup")
REASONS = {
    "readiness": "NATIVE_PULSE_NOT_READY",
    "migrate": "NATIVE_PULSE_MIGRATION_FAILED",
    "seed": "CP_GOVERNED_SEED_NOT_WIRED",
    "exercise": "REAL_IAM_CP_DOMAIN_QUALIFIER_NOT_WIRED",
    "cleanup": "INDEPENDENT_CLEANUP_WITNESS_REQUIRED",
}


def refuse(phase: str, reason: str) -> dict:
    return {
        "schema": "baobab.engine-development-adapter-result.v1",
        "engine": "baobab-pulse",
        "phase": phase,
        "result": "BLOCKED",
        "reason": reason,
        "native_effect_observed": False,
        "runtime_eng_onb_qualified": False,
        "protected_acceptance": False,
        "production_authorized": False,
    }


def observe_ready(endpoint: str) -> bool:
    """Use only a fixed loopback endpoint: never allow an arbitrary SSRF URL."""
    if endpoint != "http://127.0.0.1:8000/readyz":
        return False
    try:
        with urllib.request.urlopen(endpoint, timeout=3) as response:  # noqa: S310
            return response.status == 200 and len(response.read(4097)) <= 4096
    except (OSError, urllib.error.URLError):
        return False


def migrate() -> bool:
    # No migration is permitted on a reused, protected or missing DB. The
    # trusted Infrastructure caller must supply an ephemeral native DB URL.
    if os.environ.get("BAOBAB_DEV14_PRIVATE_RUN") != "1":
        return False
    if os.environ.get("BAOBAB_ENVIRONMENT") != "development":
        return False
    if not os.environ.get("PULSE_DATABASE_URL", "").startswith("postgresql://"):
        return False
    script = Path(__file__).resolve().parents[1] / "scripts" / "migrate.py"
    if not script.is_file():
        return False
    try:
        result = subprocess.run(
            [sys.executable, "-B", str(script)],
            check=False, capture_output=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def run(phase: str) -> tuple[int, dict]:
    if phase not in PHASES:
        raise ValueError("UNKNOWN_OWNER_PHASE")
    if phase in {"readiness", "migrate"}:
        passed = observe_ready("http://127.0.0.1:8000/readyz") if phase == "readiness" else migrate()
        if passed:
            observation = refuse(phase, "OWNER_COMPONENT_OBSERVED")
            observation["result"] = "PASS"
            observation["reason"] = "OWNER_COMPONENT_OBSERVED"
            observation["native_effect_observed"] = phase == "migrate"
            return 0, observation
    return 2, refuse(phase, REASONS[phase])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=PHASES)
    args = parser.parse_args(argv)
    status, receipt = run(args.phase)
    print(json.dumps(receipt, sort_keys=True))
    return status


if __name__ == "__main__":
    sys.exit(main())
