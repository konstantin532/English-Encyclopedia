# SDD ledger — plan: docs/superpowers/plans/2026-10-26-educational-typography.md

Execution: inline, approved by user. Spec and plan read; existing isolated codex/lesson-design-pilot worktree reused. Windows PowerShell execution; ledger retained here alongside plan rather than invoking POSIX task wrappers. This does not change implementation or review gates.

Pre-flight 1→2: fresh-base templates and existing --font-* roles consumed by scoped stylesheet; verify cascade after rebase.
Pre-flight 2→3→4: data-educational-reading plus theme roles consistent; script DOM and poem rows stay unchanged.
Pre-flight 4→5: final tested HEAD must match remote PR head; no merge.

Task1: pilot preserved as9f8453e then rebased to25c9653 on origin/main ce533e12. Resolved three conflicts by retaining main bookpage attribute/style and feedback fallback, new pilot overrides only when scoped root present; retained both sets of tests. Source8000 checkout untouched.
Task1 checks: Node133/133. Django6 actual route/pilot tests passed; extra guessed module tests.test_lesson_bookpage caused ImportError and is being corrected to discovered real filename, not counted as passing.

Ruling: preserve main bookpage hooks alongside the approved two-page pilot — avoids deleting merged behavior; cost if wrong is visual cascade conflict, checked explicitly on first lesson before rollout.

Task1: complete — rebased25c9653 on ce533e12; Node133/133, Django6/6. The guessed nonexistent module was corrected; no tests weakened.
Task2/3: base stylesheet and three template hooks committed b56c8f4. RED missing stylesheet/root observed; GREEN Node palette contract and3 Django preservation tests. Real wide story viewed; remaining responsive/state review continues before completion.
Task4 in progress: RED root scale undefined observed; fix shares --reader-scale on nearest educational root while retaining practice fallback. RED missing transfer_pilot root observed; main wrappers corrected. Node136/136 and initial11 Django tests passed before extending dialogue checks to all30.
Ruling: preview-only pilot.sqlite3 reloaded from fresh main seed — necessary to show current content after rebase; source/user DB untouched, cost if wrong limited to disposable guest preview state.

Task2/3/4 implementation complete at15d920c plus final translation fix. RED→GREEN legacy ex-ru .62em replaced with shared scale after real browser showed13.547px. Reload showed17px, A+20 produced17.8947px and matching sibling input/practice18.9474px. Node138/138, CSS19/19, Django targeted11/11. Independent fresh-context whole-branch review found no new P0–P3 findings; no deferred minors.
Ruling: add pinned django-csp4.0 only to an executor-local target directory — fresh main requires it and sharedvenv predates it; cost if wrong limited to verification runtime, source8000 environment unchanged. CSP5/5 pass.
Final broad run before dependency correction:958 tests,4 missing-csp errors,8 skipped. Rerunning final product tree with isolated dependency; no tests weakened.
Browser QA stopped by Windows URL-policy capability restriction. No retry/automation bypass. Remaining visual coverage is explicitly recorded in docs/educational-typography-validation.md; draft PR will remain unmerged.

Broad corrected run at c97509f:958 tests in259.609s, OK(skipped=8), exit0. Author read of existing CI browser acceptance found stale old-navigation expectation. Updated test to enforce user-approved disabled annotated TOC and available navigation retaining essentials; legacy fallback assertion retained. Restored visible4/6/7-of7 counts in pilot feedback under RED→GREEN Node test. No browser automation launched locally for this change. Final Node138/138.
Task4: complete implementation and independent review; visual gaps remain BLOCKED as documented rather than claimed passed.
Task5 in progress: final commit + full suite + authorized push/draftPR + exact-SHA CI.

Task5: first published draftPR128 head001ab4c. Local full958 in265.138s OK(skipped8), Node138, styles19. Remote head confirmed. CI Atlas failed at geometry of display:contents aside, not at reading mode/contrast. RED→GREEN visibleLayoutBounds test now preserves actual x/width assertions for visible box and rejects missing child; no local browser retry. Other CI runs still in progress.
Ruling: measure first visible child for a display:contents wrapper — wrapper has no layout box and cannot represent the user-visible boundary; cost if wrong is a missed child alignment, guarded by unchanged1px x/width comparison and positive-width/missing-child checks.

Full4014614 local958 tests in266.162s OK(skipped8). CI confirmed real chapter chrome regression41px. Fix excludes cinematic-week article chrome/rootfont bleed, narrows paragraph/heading scopes so nested cards retain existing typography. Node142/142, CSS19/19, diff clean. New pure geometry contract keeps shell/all card dimensions except flow-y strict, reading x/width strict, home/catalogue all4 strict.
Ruling: permit y/height changes only for the authored chapter story text, and downstream card-y — typography necessarily changes reading flow; cost if wrong is unreviewed vertical rhythm, explicitly left in manual-visual limitations. Shell/hero/card size/columnwidth are still enforced.

CIe104 wide1440/1280 protected geometry delta0; mobile failed downstream route-y and1.4px toc-height. Excluded chapter toc lineheight override; mobile route retains size/x, y must follow article within128px. Review P2 fixed: explicit visible/nonzero/contained lines and bounded vertical card/container/order gaps; evil hidden/zero/±9999 fixtures RED→GREEN; helper/test paths triggerAtlas. Node144, styles19, independent follow-up found no new concrete issues. No browser retry.
Ruling refinement: vertical equality is replaced by bounded relational layout checks, not dropped; downside of an arbitrary displacement is guarded by visibility, containment, flow and card-size assertions.
