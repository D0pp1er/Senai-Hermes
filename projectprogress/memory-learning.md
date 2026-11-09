# Confirmed outcome learning

Integrated feature/memory through 929a2ea (merge b6c56f7). Coordinator wiring: 4ffc1aa.
Branch readiness and 248 offline tests passed. Combined suite: 370 passed, including
13 evaluator tests and 12 new confirmation/event-source integration tests.

## Personal facts
With one configured SENAI_INSTALLATION_ROOT, ordinary single-line personal observations
such as "I prefer concise replies", "I like Python" or "My habit: Checks tests" are
candidates only. In the ordinary interactive CLI, a successful execution is followed
by a prompt showing the exact fact. Only the user's y/yes input confirms retention.
Decline, EOF, noninteractive input or JSON mode does not save an inferred fact.
Unconfirmed candidates are not persisted; there are no repetition counters or
pending personal-fact files. Repeating a statement never grants confirmation.

Explicit requests count as the user's confirmation:
    Remember my preference: Prefers concise replies
    Remember my habit: Checks tests before commits
    Remember my like: Likes Python
    Remember my dislike: Dislikes noisy output
    Remember my choice: Chose a local-first architecture

Those facts go to USER.md. An explicitly retained choice is treated as significant
to its owner. Existing "Remember in USER.md: FACT", "Remember in MEMORY.md: FACT"
and "Remember that FACT" remain explicit save requests. They are not automatic
learning from ordinary responses. In Telegram/noninteractive use, send an explicit
save request; a detached child does not ask an unreadable terminal question.

## Trusted app milestones
OutcomeLearning is the default successful-outcome callback and invokes
evaluate_noteworthy with current global USER.md/MEMORY.md for duplicate/capacity
checks. Response text and uploaded JSON never set evidence flags.

Apps can inject OutcomeLearning(memory, checks=(MilestoneCheck(...),)).
Each MilestoneCheck specifies an app-controlled event ID, concise fact, command argv,
significant=True and a deadline (default 30 seconds, max 300). It runs without a
shell in the authorized task workspace after successful execution. Only integer
exit code zero verifies it; missing commands, timeout, failed checks and insignificant
events do not qualify. The model cannot select commands or assert significance.
No output is treated as proof just because it says "verified" or "success".

Only validator-sourced, verified significant milestones qualify automatically for
MEMORY.md. Stock CLI does not invent release events or configure verification
commands from model output. Trusted callers configure those business-event checks
explicitly. No autonomous classifier is introduced.

Legacy injected LearningDecision callbacks must carry confirmed/kind/source metadata
for personal facts and kind='milestone', source='validator', significant=True for
automatic milestones, in addition to noteworthy=True and verified=True. Explicit
user_requested=True remains a trusted assertion of an actual authorized save request.
The complete decision batch is checked before applying any member.

## Lifecycle and verification
Failed tasks never prompt, evaluate or run checks. SOUL.md cannot be an automatic
target. One configured installation still shares USER.md/MEMORY.md across projects;
saved facts appear in fresh snapshots, not in an already-frozen native session.
No profile/session schema migration, new dependency or production action was needed.

Verification logs:
- feature worktree outputs/qa-integration/evaluator-review.log
- main outputs/outcome-learning-red.log
- main outputs/outcome-learning-green.log
- main outputs/noteworthy-combined-regression.log

Tests cover confirmation acceptance/decline, real CLI input, all personal categories,
unconfirmed repetition, forged model flags, failed tasks/checks, insignificant events,
an actual bounded subprocess artifact check, legacy bypass rejection, separate
installations, frozen snapshots and unchanged SOUL.md. No live bot/API state was used.
