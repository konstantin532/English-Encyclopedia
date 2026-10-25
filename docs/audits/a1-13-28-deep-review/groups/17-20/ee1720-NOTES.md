# A1 17–20: independent editorial implementation

Base: 5826785ee3f665fac765783ba9a95a5dd3b52655. Detached worktree /tmp/ee-a1-17-20. No commit, publication, merge, migrations/schema changes, auth changes, global grading normalization, registry/color/ID changes. Parent integrates patch.

## Scope and decisions

Four lessons17–20, four corresponding lexicon packages, weeks9–10, poem5, actual course map (no story scheduled at9/10), active topics/scenarios/error-repairs, guide, scaffold, micro/delayed review rows, existing grading and UnitProgress APIs. Existing good explanations (do/be/modal distinction, subject questions, never/dialect scope, like -ing/to, play guitar alternative) retained.

Confirmed changes:
- L17 cafe-opening build no longer awards entire shop-opening phrase. Genuine work+home credits retained (home is LX-00005).
- L18 identifying E / spelling TOM no longer awards entire alphabet, nor word spell when never produced. Latin BEL ОVA letter sequence remains Latin in Russian gloss. Seven-digit teaching fragment explicitly distinguished from usual full ten-digit grouping.
- L19 unrelated weekend/read/never whole phrases removed from translations; a one-word always slot no longer awards entire Saturday-reading phrase. Primary/secondary stress distinguished. Day/month/preposition notes scoped; ordinary American omission of on not prohibited by active mission.
- L20 I-speaker prompt now explicitly asks learner to play Anna and speak about self; corresponding delayed review agrees. Only actual jacket answer credited, not clothing distractors. Music answer no longer credits I play the guitar. Unrelated whole phrases removed from translations. Silent-e note limited to its examples. Dictionary play card now agrees with main lesson about play guitar.
- Scaffold17 uses known work, every day instead of future live/week12 and Sundays/week10. Scaffold20 swimming/week13→walking; guide20 drawing/week13→walking. Micro17 future read/week10 and live/week12 replaced with have dinner/work. Micro20 future sing/swim/week13, hat/coat/week14, white/week12 replaced with known cooking/watching/clothing/colors. Five distinct cases and stable source exercise order retained. Micro20 malformed distractor attached ing to object noun; replaced with incorrect agreement likes, preserving meaningful verb target.
- Twister9 phone is a communication verb D5 in this imperative context; ordinary noun phone remains S2 elsewhere. Temporal in in twister10 and its warmups uses P3. Twister10 Russian translation describes activities, avoiding false equivalence reading=I read. English spoken text/IPA preserved.
- When vs what time dictionary note no longer forbids clock-time answers to when; which need not select a small set. Email definition no longer limits message device; first-name definition no longer requires birth/current-order assumption; wrong final /ŋ/ not rendered as Russian /n/. Call me later need not imply a repeat call.

## Evidence

- /tmp/ee1720-semantic-ledger.json: full per-field before/after with stable paths, base and SHA256 of changed files. /tmp/ee1720-reviewed-source-hashes.json: broader read-source inventory.
- /tmp/ee1720-before-final.log and /tmp/ee1720-after.log: identical frozen test module on untouched base versus changed content. Test hash documented in checks file.
- /tmp/ee1720-migrate.log, -load.log, -audit.log: new isolated SQLite runs, not historic CI.
- /tmp/ee1720-db-guard.py: asserts backend and exact /tmp DB before management commands. Both URLs explicitly local; settings.test.
- /tmp/ee1720-audio.log: readiness diagnostic only; real audio unavailable. No listening claim.

Test draft corrections, not production fixes: early jacket API test supplied a whole sentence where choice expects jacket; corrected to actual option. Initially suspected home credit proved legitimate after lookup LX-00005 and was retained; expected set corrected identically on both base and after. A temporary command ran from baseline cwd; all baseline tracked changes restored with git restore content before final run. Final base tracked tree clean; new test file is the only addition. Ignore earlier draft logs.

## Sources consulted 2026-10-25

- https://dictionary.cambridge.org/grammar/british-grammar/at-on-in-time (search retrieval supports AmE on the weekend, day/month time prepositions; direct open403).
- https://dictionary.cambridge.org/uk/grammar/british-grammar/british-english (search retrieval: section At the weekend/on the weekend).
- https://www.merriam-webster.com/dictionary/email (opened: electronic email-system sense).
- https://www.merriam-webster.com/dictionary/first%20name (opened: first name, given-name synonym; no birth constraint).
- Existing lexical IPA /ˈwikˌɛnd/ supplies primary vs secondary stress distinction; no pronunciation generated or heard.
- Internal chronology confirmed directly against seed lexicon UID/week fields; progress behavior demonstrated through actual signed-in API calls, not text-presence assertions.

## Limits

Not final course acceptance; parent must integrate, run full suite/CI, and inspect browser desktop/390px. No browser launched in this subtask (root owns browser). HTML rendering exercised with Django client and all7layers counted, API cases cover accepted answers and wrong meaning/owner/polarity/agreement/ordinary question order/spelling order. Actual audio files under static/audio absent. Week dialogues and twister spoken English unchanged, hence no recorded line replacement introduced; scaffold/guide/micro English changed and any separately cached/generated supplementary audio must be refreshed if supplied externally. Audio readiness does not prove sound quality. PostgreSQL/full suite deliberately delegated to parent.
