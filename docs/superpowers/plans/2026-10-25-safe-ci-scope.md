# Safe CI Scope Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Fast checks only where impact is demonstrably bounded.
**Architecture:** Fail-closed selector and exact independent exclusions; preserve
existing job names and full non-PR runs.
**Tech Stack:** Python standard library, pytest, Git, GitHub Actions.
**Spec:** docs/superpowers/specs/2026-10-25-safe-ci-scope-design.md

## Global Constraints
No skipped required checks, protection edits, merge, deploy, credentials or AI bot.
No general seed-level/A2 isolation claim. Unknown paths and new tests fail broad.

## Review Focus
- Runtime data hidden in docs must not take prose route.
- Renames/deletes/additions and ambiguous Git bases must fail broad.
- Inputs must not become shell commands or pytest options.
- New shared dependencies must invalidate independent exclusions.
- Existing job contexts and full coverage ratchet must remain reliable.

### Task 1: Selector and contract tests
Files: scripts/ci_scope.py, tests/test_ci_scope.py.
- [x] Write failing eligibility, diff, fallback, event and command tests.
- [x] Run tests and record expected missing-feature failure.
- [x] Implement classifier, Git diff parsing, fingerprint and fixed pytest argv.
- [x] Run focused tests and adversarial cases.

### Task 2: Workflow routing and documentation
Files: .github/workflows/{ci,quality-evolution}.yml, tests/test_ci_workflows.py.
- [x] Write failing workflow contract tests preserving names/full paths.
- [x] Add checkout history, event/base/head environment and scope planning.
- [x] Route steps, keep real same-name checks and explicit scoped evidence.
- [x] Run workflow contract tests and selector tests.

### Task 3: Verification and publication
- [x] Run full Django suite, JS, course load/audit and diff checks.
- [x] Independently review entire diff and address substantive findings.
- [ ] Commit, publish separate draft PR and verify remote exact head.
- [ ] Track full CI for that head; disclose any blocked verification.

## Verification ledger
- Baseline main 2a35c04: 921 Django tests, OK, skipped=2 (264s).
- Final reviewed code: 943 Django tests, OK, skipped=2 (296s), parallel=4.
- Focused selector/workflow suite: 22 passed, 9 subtests; docs route: 26 passed,
  22 subtests; active collection: 896/947 selected, exactly 51 deselected.
- JS124, CSS17, Django check/migration-drift check, compileall, load/audit,
  mutation4/4 and fuzz76 (seed20261025): PASS. Existing course warnings remain.
- Ruling: fingerprint every unknown tracked path, not only known code folders;
  this closes independently reproduced root-hook false-green risk and deliberately
  sacrifices future scoped acceleration until dependencies are re-reviewed.
- Browser: N/A for workflow-only changes. Windows and local PostgreSQL: not run.
  Exact remote head's full PostgreSQL/coverage CI remains pending publication.
