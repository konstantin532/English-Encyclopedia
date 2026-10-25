# Conservative CI selection

## Intent and authority
The user approved change-impact-based CI with a separate reliable full run.
This first rollout deliberately does not claim general A2/A2+ selection: current
populated course content is A1/A1+, and canonical seed dependencies are shared.
No model credentials, AI review service, protection change, merge or deployment.

## Baseline
Base: `2a35c04` (main, 25 October 2026). Successful Actions run 40211767451
spent 18m15s in SQLite pytest and 25m38s in PostgreSQL pytest. Quality run
40211767447 spent 25m09s in covered pytest. Setup took seconds, not minutes.
The runs execute the same suite three times; CI wall time is not their sum.

## Approaches
- Filename-based level selection rejected: vocabulary, week/lesson contracts,
  story identity and recycling cross levels; synthetic tests use real fixtures.
- General dependency graph deferred: too broad to prove in a small change.
- Selected: explicit safe scope, reviewed independent exclusions, full fallback.
  Unknown tests run by default. Narrow scope trades some potential speed for safety.

## Routing
Only pull requests can take a fast path, using an unambiguous Git merge base and
complete NUL-delimited changed paths. Missing refs, unsupported changes, new files,
renames, deletes, unsafe paths, or mixed/unmapped input fall back to full.
- Existing explicitly allowed prose: documentation contracts and selector tests.
  Runtime fixtures under docs (especially pilot assessment YAML) are not prose.
- Existing explicitly allowed active-A1 JSON: retain all tests except five
  reviewed independent classes, both SQLite/PostgreSQL, JS and full course audit.
- Canonical seed YAML, shared code, auth/models/templates, registries/manifests,
  selector/workflow/tests, dependencies and unknown input: full.
- Push, manual, scheduled and other events: full, regardless of changed paths.

Active JSON is read by the active studio, lesson views and speech practice;
none of these tests may be omitted. The independently reviewed classes are
InvalidSeedTests, WeekAuditTests, AuditSurfaceTests, StoryBeatTests and
DuplicateWordTests. Their loader/audit/week-rendering paths do not read active
JSON. Their historical covered time totals about 842s; this is not a measured
speedup. A fingerprint of all tracked files except the exact eligible prose/active JSON
and the selector script itself disables selection on drift until re-reviewed.
This includes root pytest hooks and unknown new support modules, not only apps/.

## Check contract
Keep existing job/check names and execute a real check in each mode; do not
skip whole required jobs or workflows with path filters. Selector failure fails
closed. Coverage ratchet compares complete suites only; scoped PR evidence is
explicitly labelled, never reported as full coverage. Full suite/coverage remains
on main, manual and scheduled Quality runs and broad-impact PRs. CI gets manual
full dispatch as well. Branch-protection read was blocked by GitHub integration
403; no protection settings are changed or asserted verified.

## Verification
TDD classifier tests include ambiguous/missing merge base, rename/delete/add,
unknown and runtime-doc inputs, mixed scopes, injection and event contexts.
Workflow tests preserve names, unconditional jobs and full-event behavior.
Run focused routing tests, full Django suite, JS, load/audit, independent review,
then publish one draft PR and check full CI for its exact head. No frontend change;
browser UI acceptance is not applicable to this workflow-only delivery.

## Maintenance and evidence
The scope JSON in the Quality artifact explains why a run was full or scoped.
After any other repository file changes on main, future fast paths intentionally
fall back to full. Do not blindly refresh REVIEWED_FINGERPRINT: trace the five
excluded classes and all new hooks/consumers again, then update it with tests in
a reviewed broad-impact PR. This constraint makes the first rollout conservative,
not a permanent automatic dependency graph.

Independent review reproduced a false-green counterexample using a new root
conftest.py. The fingerprint was expanded from selected directories to all tracked
files; root hooks/config/support-file tests were observed failing before the fix
and passing afterwards. Branch-protection administration remains inaccessible;
existing job contexts were preserved rather than changing protection settings.
