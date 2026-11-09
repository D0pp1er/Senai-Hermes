# Four module sequence diagrams

These describe the integrated execution paths. Message labels avoid literal semicolons,
which Mermaid treats as statement separators. For component/storage boundaries, see
[architecture](architecture.md); for exact commands, see [README](../README.md).

## 1. Chat and integrations: Senai owns input, history and response

```mermaid
sequenceDiagram
    actor User
    participant UI as CLI chat / Telegram
    participant State as Local chat DB / Telegram jobs
    participant Pipe as Senai request pipeline
    participant Context as Memory + selected skills
    participant Codex as Native Codex executor
    alt CLI chat
        User->>UI: senai chat, enter request
        UI->>State: Lock project chat, select saved local session
        UI->>State: Persist pending user turn
        UI->>Pipe: execute_request with exact saved native UUID
    else Authorized Telegram
        User->>UI: Private request
        UI->>State: Check pairing, persist authorized job
        State->>Pipe: CommandRunner invokes Senai child CLI
    end
    Pipe->>Pipe: Validate outputs workspace and execution options
    Pipe->>Context: Load frozen memory / selected package context
    Context-->>Pipe: Bounded instructions and exact digests
    Pipe->>Codex: Fresh exec or exact UUID resume
    Codex-->>Pipe: thread.started UUID
    Pipe->>Context: Bind or validate frozen native snapshot
    Pipe->>State: Persist native UUID through adapter callback/events
    Codex-->>Pipe: Final response
    Pipe->>Context: Record skill outcomes, approved/trusted memory learning
    Pipe-->>UI: Response through Senai
    UI->>State: Save completed response before display/delivery
    UI-->>User: CLI response or authorized Telegram delivery
    Note over UI,State: CLI chat DB and Telegram shared-session DB stay separate.
    Note over State,Codex: Failed/interrupted work remains recorded, no automatic replay of uncertain effects.
```

## 2. Memory: fresh profiles, frozen resume and confirmed learning

```mermaid
sequenceDiagram
    actor User
    participant Pipe as Senai pipeline
    participant Runtime as InstallationRuntime
    participant Store as Profiles + native snapshot DB
    participant Codex as Executor
    participant Learn as OutcomeLearning / trusted checks
    User->>Pipe: Request (fresh or saved session)
    Pipe->>Runtime: execute(request, options)
    alt Fresh native session
        Runtime->>Store: Read installation SOUL, USER, MEMORY and facts
        Store-->>Runtime: Bounded snapshot + revisions
    else Exact native resume
        Runtime->>Store: Load existing frozen snapshot for UUID
        Store-->>Runtime: Original snapshot (not current edited profiles)
    end
    Runtime->>Codex: Managed profiles + snapshot + request context
    Codex-->>Runtime: thread.started(UUID)
    Runtime->>Store: Bind snapshot or validate exact resumed identity
    Codex-->>Runtime: Successful final response
    Runtime->>Learn: Evaluate successful outcome with trusted evidence
    alt Explicit user save or confirmed personal observation
        Learn-->>User: Ask retention confirmation when needed
        User-->>Learn: Explicit yes (or prior explicit save request)
        Learn->>Store: Validated append to USER or MEMORY
    else Verified significant app milestone
        Learn->>Learn: Run app-controlled bounded validation
        Learn->>Store: Append verified milestone to MEMORY
    else Decline, repetition, failure or unverified assertion
        Learn-->>Runtime: No write
    end
    Note over Runtime,Store: Automatic learning never edits SOUL. Fresh sessions see later edits, resumed snapshots stay frozen.
```

## 3. Cron: guided schedule to durable execution and independent delivery

```mermaid
sequenceDiagram
    actor User
    participant Wizard as CLI / Telegram wizard
    participant Store as Account cron store
    participant Worker as Serialized execution worker
    participant Gate as Shared execution/session gate
    participant Pipe as Existing authorized Senai pipeline
    participant Delivery as Independent delivery loop
    participant Telegram as Authorized transport
    User->>Wizard: Name, task, friendly time, repeat
    Wizard->>Wizard: Parse time, resolve zone, select authorized destination
    Wizard-->>User: Fixed preview with destination and retry policy
    User->>Wizard: Confirm
    Wizard->>Store: Reauthorize and commit schedule once
    Note over Store,Worker: Management alone starts no worker, operator explicitly starts service.
    Worker->>Gate: Enter shared gate
    Worker->>Store: Atomically claim due eligible occurrence
    Worker->>Pipe: Execute using pinned project/installation/shared UUID
    Pipe-->>Worker: Result or uncertain execution
    alt Completed execution
        Worker->>Store: Commit result + outbox intent atomically
    else Deadline or unknown effects
        Worker->>Store: Record unknown, pause schedule, fence automatic repeat
    end
    Worker->>Gate: Release gate
    Delivery->>Store: Read pending durable delivery independently
    Delivery->>Telegram: Recheck recipient authorization, send saved text
    alt Confirmed accepted
        Telegram-->>Delivery: Message acceptance ID
        Delivery->>Store: Mark delivered
    else Certified not accepted
        Delivery->>Store: Bounded safe retry
    else Ambiguous or partially accepted
        Delivery->>Store: Mark unknown, require review
    end
    Note over Store,Delivery: Restart resumes pending delivery without rerunning completed Codex work.
```

## 4. Skills: explicit selection, auditable outcomes, checked improvement

```mermaid
sequenceDiagram
    actor User
    participant UI as Skill CLI
    participant Registry as Project registry
    participant Context as SkillContext
    participant Pipe as Existing Senai executor
    participant Check as Trusted host checks
    participant Vault as Obsidian projection
    User->>UI: import package / workflow, use name
    UI->>Registry: Validate and save accepted package, save project selection
    User->>Pipe: Ordinary coding or chat request
    Pipe->>Registry: Resolve explicit accepted selection
    Registry-->>Context: Exact version, digest and package resources
    Context->>Context: Verify/copy immutable resource snapshot
    Context->>Pipe: Bounded reference context, preserve memory/native UUID
    Pipe-->>Context: Response
    Context->>Registry: Digest-linked outcome (unverified without independent checks)
    User->>UI: Explicit authoring/stage or evidence-guided review
    UI->>Registry: Save inactive candidate/revision and linked evidence
    User->>Check: Request independent declared checks
    Check->>Registry: Store actual observed pass/fail evidence
    User->>UI: Explicit accept-learning / activate revision
    UI->>Registry: Require latest passing checks and valid current base
    Registry-->>UI: Accepted version + durable history
    opt Explicit rollback
        User->>UI: Rollback to accepted digest
        UI->>Registry: Restore intact accepted version, retain history
    end
    opt Explicit export/refresh
        User->>UI: skill export obsidian
        UI->>User: Ask vault path if unset
        UI->>Vault: One-way export, protect edited/personal notes
    end
    Note over UI,Registry: Advanced authoring reports are separate from ordinary chat runs. No automatic activation or weight training.
```
