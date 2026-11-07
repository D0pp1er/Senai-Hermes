# Main task: Sentien SWE project

Source: Sentien SWE Project.pdf (four pages). This file records requirements,
not permission to use accounts, contact people, publish, or disclose credentials.
No credentials are copied into this repository.

## Required product workflow

| ID | Task | Status | Verifiable approach / TDD |
| --- | --- | --- | --- |
| R1 | Accept user input through a simple interface | Done | Red: CLI invocation has no handler. Green: quoted request reaches the adapter; empty input fails. Tests: tests/test_cli.py. |
| R2 | Process input and pass appropriate context/instructions to Codex CLI | Done | Red: missing context or wrong cwd. Green: prompt boundaries, workspace, and stdin delivery match expectations. Mock subprocess; inspect exact arguments. |
| R3 | Capture Codex output and return it to the user | Done | Red: missing final message/errors lost. Green: final-response capture and nonzero/missing executable/empty response tests. Live create/edit checks recorded in CHANGELOG.md. |
| R4 | Extend the wrapper with selected Hermes-like capabilities | Partial | Reuse native Codex skills and session mechanisms first. Each added capability starts with a failing behavior test and ends with one feature commit. Custom memory/scheduling is optional, not yet implemented. |

## Research and development requirements

| ID | Task | Status | Verifiable approach / TDD |
| --- | --- | --- | --- |
| D1 | Research Hermes and compare it with Codex CLI and Claude Code | Pending | Documentation acceptance check: primary sources, comparison of persistence/skills/autonomy/channels, and dated findings. Verify links and distinguish observed behavior from claims. TDD applies to code examples, not prose. |
| D2 | Build on Codex CLI and reuse its existing functionality | In progress | Test argument forwarding against installed CLI help; verify a real local run. Keep adapters small and document unsupported combinations. |
| D3 | Disclose language and open-source tools | Done | README and pyproject.toml disclose Python, unittest, setuptools, Git, and Codex CLI. Check that dependency list matches installed runtime needs. |
| D4 | Use only the permitted AI tools (ChatGPT/ChatGPT Work/Codex CLI) | Ongoing | Record tools used in development history; no other AI service integration. This is a process audit, not a unit-test claim. |
| D5 | Preserve complete development chat history | Pending export | Keep this chat and Codex session history; include an authentic exported transcript in submission. Do not substitute CHANGELOG.md for complete chat history. Verify export completeness manually. |
| D6 | Work within the stated 24-hour window and manage usage | Ongoing | Prioritize the minimum workflow and log completed verification; do not fabricate a deadline/start time. Review timestamps and remaining user-provided deadline. |
| D7 | Clarify material misunderstandings with Sentien | As needed | Record unresolved questions for the user. No external message is sent without explicit user authorization. |

## Optional Hermes-like capabilities (choose deliberately)

| ID | Task | Status | Verifiable approach / TDD |
| --- | --- | --- | --- |
| H1 | Persistent memory across conversations | Optional backlog | Red: saved fact missing after restart. Green: store/retrieve relevant facts, test isolation, deletion, corrupt storage. Native resume is context continuity, not automatic semantic memory. |
| H2 | Skills created/updated from experience | Optional backlog | Red: successful workflow cannot be reused. Green: versioned skill persistence/retrieval; test failed-run exclusion and revisions. Selecting an existing Codex skill does not implement automatic learning. |
| H3 | Autonomous execution / scheduling | Optional backlog | Red: due task not run or duplicates after restart. Green: persistent schedule, controlled execution, retries/idempotency tests using a fake clock. |
| H4 | Multi-channel access (Telegram, Slack, email, etc.) | Optional backlog | Red: incoming event not routed. Green: adapter contract, identity isolation, deduplication, mocked sends; live checks require account setup. |
| H5 | Install/experiment with Hermes | Optional backlog | Optional only; isolate installation and document observations. Do not use supplied account credentials automatically. |

## Submission deliverables

| ID | Task | Status | Verifiable approach / TDD |
| --- | --- | --- | --- |
| S1 | Source code plus setup/execution instructions | Done, maintain | Fresh editable install, senai --help, tests, and disposable live demo. |
| S2 | Architecture, features, decisions, and limitations | Partial | README covers implementation; add research/tradeoffs and final implemented-vs-unimplemented matrix. Follow documented commands and compare claims with tests. |
| S3 | Complete development chat history | Pending export | Same acceptance check as D5; export and review for completeness before submission. |
| S4 | Google Slides demonstration and design discussion | Pending | Create deck covering demonstration, decisions, successes, and failures; verify each claim with demo evidence. Check rendering/readability and user account access for upload. No unit tests for slide prose. |

## Other document conditions to retain

- Materials are confidential; keep the repository local unless the user explicitly authorizes sharing.
- The document describes payment after a valid submission (BDT 1000) and optional food reimbursement up to BDT 500 with a receipt. These are submission notes, not software features or payment guarantees.
- The document includes account credentials and an authentication-contact instruction. Keep credentials out of code/logs and leave account access or contacting the team to explicitly authorized work.
- Evaluation favors research, prioritization, engineering, problem-solving, and clear communication. A small verified system is preferred.

## User requirements and current compatibility milestones

- WSL checkout is authoritative: /home/rk/SentiensHermes/senai.
- Generated product files belong under outputs/; package source, tests, and progress records remain outside it.
- Use the installed senai command, tests/, and projectprogress/.
- Keep short commit messages; one newly achieved Codex capability per commit.
- [x] Existing write/edit workflow.
- [x] Explicit model/configuration selection (tests/test_options.py).
- [x] Image attachments (tests/test_images.py).
- [x] Web search (tests/test_search.py).
- [ ] Explicit installed-skill selection.
- [ ] Session resumption.
- [ ] Interactive Codex workflow (native slash commands and tools).
- [ ] Native command compatibility (review, MCP/plugin management, help, future flags).

Compatibility means preserving supported installed Codex behavior, not rebuilding
its tools or claiming every plugin/account/model is available. Distinguish unit
transport verification, installed-CLI parser checks, and live model checks.
