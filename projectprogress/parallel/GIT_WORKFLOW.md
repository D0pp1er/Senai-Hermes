# Local Git integration and push workflow

Main preserves reviewed feature merge commits and coordinator conflict resolutions.
Do not rebase main to upload already-integrated work.

## Before pushing main

Run from /path/to/workspace/senai:

    git status
    git fetch origin
    git merge-base --is-ancestor origin/main main
    git push origin main

The ancestor check exits 0 when a normal fast-forward push is possible.
If it fails, review the newly fetched commits and integrate deliberately; do not
force-push, reset, or automatically replay the complete integration history.
If a pull is needed, use git pull --ff-only origin main.

Repository-local settings for this checkout are pull.rebase=false and pull.ff=only.
These live in .git/config and are not distributed by cloning this document.
They do not change global Git preferences.

## Update an already-integrated feature worktree

Confirm a clean tree on its expected branch, then git merge --ff-only main.
Reinstall the editable package only in that worktree's .venv, run pip check,
the full test suite and its ownership/readiness check.
If fast-forward refuses, stop and review new commits instead of rebasing automatically.

## Recovery performed on 2026-11-09

An interrupted pull --tags origin main was rebasing main onto 1357cdd and
replaying reviewed cron and voice commits. It conflicted in Telegram CLI startup.
The pre-rebase main was already the integrated, tested 80c9cb4 and descended
from origin/main, so no history rewrite was required.

Saved staged/unmerged patches, rebase metadata and reflog under
outputs/git-recovery/20261108T215118Z before aborting the rebase.
refs/recovery/interrupted-main-rebase retains the interrupted rewritten HEAD.
Restored the existing reviewed merge history with git rebase --abort.
No feature commits, production bot state or credentials were changed.
Remote state was not written. Full regression evidence:
outputs/git-recovery-regression.log.
