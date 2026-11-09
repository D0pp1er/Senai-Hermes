# Confirmed outcome learning

See [usage](../README.md#3-human-memory-preferences-and-identity) and [manual demonstrations](all-features-demonstration.md#4-memory-user-and-soul-profiles-m01m12).

## Personal facts
With one saved installation root (or an explicit SENAI_INSTALLATION_ROOT), ordinary single-line personal observations
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

