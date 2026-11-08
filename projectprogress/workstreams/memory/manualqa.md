# Memory QA

Offline PASS: .venv/bin/python -m unittest discover -s tests/memory -v (7 tests).
A child Python process reopens a temporary DB and recalls an invoice fact; other
projects/scopes see no entries. Concurrent writers cannot exceed five entries.
All fixtures are temporary, no production state or model calls used.
Live Codex integration: not run; shared hook is not wired.
