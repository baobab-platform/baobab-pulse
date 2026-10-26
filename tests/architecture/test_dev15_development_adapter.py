"""DEV-15 adapter remains strictly owner-only until connected runtime proof."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[2] / ".baobab" / "development_adapter.py"
SPEC = importlib.util.spec_from_file_location("pulse_dev15", PATH)
assert SPEC and SPEC.loader
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)


class Dev15AdapterTests(unittest.TestCase):
    def test_unwired_authority_and_cleanup_never_pass(self):
        for phase in ("seed", "exercise", "cleanup"):
            with self.subTest(phase=phase):
                code, row = ADAPTER.run(phase)
                self.assertEqual(code, 2)
                self.assertEqual(row["result"], "BLOCKED")
                self.assertFalse(row["runtime_eng_onb_qualified"])
                self.assertFalse(row["protected_acceptance"])

    def test_untrusted_health_endpoint_is_refused(self):
        self.assertFalse(ADAPTER.observe_ready("https://example.com/readyz"))

    def test_missing_disposable_db_never_runs_migrations(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(ADAPTER.subprocess, "run") as proc:
            status, row = ADAPTER.run("migrate")
        proc.assert_not_called()
        self.assertEqual(status, 2)
        self.assertEqual(row["result"], "BLOCKED")

    def test_non_native_readiness_does_not_claim_validity(self):
        with patch.object(ADAPTER, "observe_ready", return_value=True):
            code, row = ADAPTER.run("readiness")
        self.assertEqual(code, 0)
        self.assertEqual(row["result"], "PASS")
        self.assertFalse(row["runtime_eng_onb_qualified"])
        self.assertFalse(row["native_effect_observed"])

    def test_migration_refuses_external_postgres_even_if_dev_flag_is_present(self):
        safe_flags = {"BAOBAB_DEV14_PRIVATE_RUN": "1", "BAOBAB_ENVIRONMENT": "development"}
        for endpoint in (
            "postgresql://admin:pw@production-db:5432/pulse",
            "postgresql://admin:pw@127.0.0.1:5432/pulse",
            "postgresql://admin:pw@pulse-db:5432/production",
            "postgresql://admin:pw@pulse-db:5432/pulse?sslmode=disable",
            "postgresql:///pulse",
        ):
            with self.subTest(endpoint=endpoint), patch.dict(
                "os.environ", {**safe_flags, "PULSE_DATABASE_URL": endpoint}, clear=True
            ), patch.object(ADAPTER.subprocess, "run") as proc:
                self.assertFalse(ADAPTER.migrate())
                proc.assert_not_called()

    def test_health_requires_real_ready_database_response(self):
        import io

        class Response:
            status = 200

            def __init__(self, payload):
                self._data = io.BytesIO(payload)

            def read(self, length):
                return self._data.read(length)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        for raw, expected in (
            (b'{"status":"ready","dependencies":{"database":true,"semantic_retrieval":false}}', True),
            (b'{"status":"not_ready","dependencies":{"database":false}}', False),
            (b'{"status":"ready","dependencies":{"database":false}}', False),
            (b'{"status":"ready"}', False),
            (b'not-json', False),
        ):
            with self.subTest(raw=raw), patch.object(ADAPTER.urllib.request, "urlopen", return_value=Response(raw)):
                self.assertEqual(ADAPTER.observe_ready("http://127.0.0.1:8000/readyz"), expected)

    def test_invalid_phase_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_OWNER_PHASE"):
            ADAPTER.run("approve")


if __name__ == "__main__":
    unittest.main()
