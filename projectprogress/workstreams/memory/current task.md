# Current task

Branch feature/memory; scoped implementation and offline executor transport verified.
411d8b0 adds three tests using real run_codex and an isolated fake child executable.
170 full offline tests pass: 126 original + 10 coordinator + 34 memory tests.
Full exact-commit evidence: outputs/qa-project/memory-transport-tests.log.
No live model, production state or Telegram poller used. Working APIs unchanged.

Next: coordinator applies the proposed session lifecycle/CLI hooks in integration-notes.md,
then runs cross-feature and separately authorized live acceptance checks.
This feature chat must not edit shared files or merge under MERGE_POLICY.md.
