# Independent final integrated challenge (read only)

Tree /tmp/ee-a1-13-28, base8788aac996c5010060b47cca6f12f0480c2d492c. No source edits or new tests/run performed. This is a narrow integration challenge, not a repeated broad course audit.

## Confirmed remaining semantic risk
EX-00113 in a1_w10_l20_like_doing.yaml binds LX-00203 music, yet accepts guitar-only responses (I like playing the guitar; I like to play guitar, with/without the). Successful such response grants music progress without using music. Removing old LX-00211 phrase binding fixed one issue but leaves this alternate-answer-dependent credit. Preserve legitimate accepted answers; minimal current-schema correction is no lexical binding for this mixed-target question, or a separately scoped conditional binding implementation (not required here). Parent notified. This risk predates integration and remains in edited record.

## Checked invariants / scope
Recursive id/uid/slug/number identities and their order identical before/after across all changed JSON/YAML. No main exercise canonical answer or review_of changed; five main accepted-answer arrays only extended, with all original variants retained. Lexical UID, lemma and primary class retained; meaning edits refine existing senses (nurse/farmer/between/across from/which/email/first name/call later/sleep/white/trip), not new homonymous senses. Full machine extraction in companion JSON; UID-keyed comparison is supplemented by recursive ordered identifier comparison.

Inspected all17 changed main exercise unit bindings against actual answer/accepted and lexicon meanings. Except EX113 above, removed bindings are supplied prompt words, incorrect whole phrases, absent alternate forms or distractors; remaining targets are present in correct production/recognition. Existing phrase-vs-slot credit is preserved where learner actually completes whole phrase. Progress histories/UIDs were not reassigned.

Outside13–28: only café/cafés forms on existing LX-00131 week6 (supports new legitimate EX83 accepted answer); topics09_13 change touches lesson13 record only; auditUnicode helper; verify_atlas adds pages to existing checks without removing geometry gates. No accounts/auth/schema/registry/grading normalizer/other level edits found in tracked diff. Shared manifest filenames cover broader ranges, but scope is target lesson records.

Audit helper byte-identical to separately reviewed frozen helper. All3 direct WORD consumers routed through text_tokens; NFC preserves accents; résumé differs from resume; mixed-script with Latin retained as unknown; pure Russian ignored. No new thresholds/whitelists or changes to answer grading. Existing completed evidence (not a new run): frozen10 before8fail→after10PASS; related42PASS; isolated actual audit_course false caf warning removed, unrelated warnings preserved.

Frozen own15 tests identical: editorial13 SHAde2e0b41e5b0cfead4740de9932f6299573acf62aa3ed30b48858ec97b519188; contextual2 SHA84d4e218f23a440ebe4e7a6fbe99977f72c4391e12023cb5ab4a59d8c8337ba2. Helper10 SHA608ffc2a07e5af1a7a1d8b74cbf73f763d17a606309c2187d31d37c39d360211. Source helper and tests exact byte equality with own frozen worktrees confirmed.

Limitations: no new DB/test/browser/audio check in this challenge; root executes integrated verification. Exercise binding semantics examined main changed records, not every unchanged shared record. No claim of complete final acceptance.
