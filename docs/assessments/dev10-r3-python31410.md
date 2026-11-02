# DEV10-R3 — Pulse Python 3.14.10 qualification

Native test suite runs with **exact CPython 3.14.10**, a frozen `uv.lock`
without downloading a different interpreter, PostgreSQL 17.11 and Qdrant.
Provider-only API tests stay out of the default gate: external evidence
requires true provider credentials and a distinct approved scenario.

Source-only Actions success does not qualify the ARM64/AMD64 full baobab-dev
candidate image or actual user's Codespace; no new evidence is accepted until
the exact owner source head, CI and image/provenance are reviewed.
