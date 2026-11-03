# DEV10-R3 — Pulse Python 3.14.10 qualification

Native test suite runs with **exact CPython 3.14.10**, a frozen `uv.lock`
without downloading a different interpreter, PostgreSQL 17.11 and Qdrant.
Provider-only API tests stay out of the default gate: external evidence
requires true provider credentials and a distinct approved scenario.

Source-only Actions success does not qualify the ARM64/AMD64 full baobab-dev
candidate image or actual user's Codespace; no new evidence is accepted until
the exact owner source head, CI and image/provenance are reviewed.

## Security reconciliation (3 November 2026)

Foundation previously failed two mandatory gates: pip-audit detected locked
`msgpack==1.2.2` (GHSA-j586-36cw-2gc2) and the built runtime contained
`msgpack==1.2.2` (CVE-2026-114613). The owner-resolver job
`125269496778` from workflow `41443084207` generated the complete
`msgpack==1.2.4` uv.lock stanza directly from PyPI, with wheel and sdist
hashes. The exact full stanza is now committed. The Dockerfile no longer
forcibly reinstalls the vulnerable 1.2.2 over the frozen build.

The one-time resolver step is removed after evidence custody; the normal
pip-audit, real runtime Trivy scan, exact CPython 3.14.10, native PostgreSQL
17 and Qdrant tests must independently pass on the final PR head. No scanner
waiver, default image major update, protected provisioning or real AI model
provider acceptance is claimed.
