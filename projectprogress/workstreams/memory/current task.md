# Current task

Human profile UX ready for coordinator integration.
Tested code commit e5459f8: 393 full offline tests PASS, including 70 memory tests
and 17 focused shortcut tests. Exact-commit verbose log and subprocess/pseudo-TTY
QA retained at outputs/qa-project/memory-profile-ux-*.

Public exports: profile_main(kind, argv, *, installation, stdin, stdout, stderr) -> int
and setup_profiles(installation). Module README includes Usage and Architecture.
No shared source, root docs, packaging, Telegram files or defaults edited.

Next coordinator work: route human root memory/user/soul shortcuts using resolved
saved installation; keep advanced SQLite routes compatible; call setup_profiles from
explicit onboarding and compose integrations /new at the native-session boundary.
Helpers keep SOUL human-only and preserve confirmation/verified milestone policies.
No new dependency/schema; own editable .venv refreshed and pip check PASS.
