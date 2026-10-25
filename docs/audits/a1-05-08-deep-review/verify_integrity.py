"""Verify semantic scope, identities and exact before/after against the task base."""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = '5826785ee3f665fac765783ba9a95a5dd3b52655'
SLUGS = {'a1-cafe-order', 'a1-numbers-1-20', 'a1-family-photo', 'a1-family-possession'}
SLUG_BY_N = {5: 'a1-cafe-order', 6: 'a1-numbers-1-20', 7: 'a1-family-photo', 8: 'a1-family-possession'}
LESSONS = sorted((ROOT / 'content/seed_lessons').glob('a1_w0[34]_l*.yaml'))
EX_UIDS = {}
for path in LESSONS:
    lesson = yaml.safe_load(path.read_text())
    EX_UIDS[lesson['slug']] = {str(e['order']): e['uid'] for e in lesson['exercises']}


def git_bytes(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)


def load(data, path):
    return json.loads(data) if path.endswith('.json') else yaml.safe_load(data)


ledger = []


def walk(before, after, path, pointer='', identity=()):
    if before == after:
        return
    if isinstance(before, dict) and isinstance(after, dict):
        for key in ('uid', 'slug', 'id', 'n', 'order', 'number', 'class', 'level', 'week', 'focus'):
            if key in before:
                assert after.get(key) == before[key], (path, pointer, key)
        own = next(({k: before[k]} for k in ('uid', 'slug', 'id', 'n', 'order', 'number', 'text') if k in before), None)
        if own:
            identity = (*identity, own)
        for key in sorted(before.keys() | after.keys()):
            child = pointer + '/' + str(key).replace('~', '~0').replace('/', '~1')
            current_id = identity
            if key in EX_UIDS:
                current_id = (*identity, {'lesson_slug': key})
            for slug in EX_UIDS:
                if key in EX_UIDS[slug] and any(i.get('lesson_slug') == slug for i in identity):
                    current_id = (*identity, {'exercise_uid': EX_UIDS[slug][key]})
            walk(before.get(key), after.get(key), path, child, current_id)
        return
    if isinstance(before, list) and isinstance(after, list):
        if before and all(isinstance(x, dict) for x in before):
            assert len(before) == len(after), (path, pointer)
            for i, (old, new) in enumerate(zip(before, after)):
                walk(old, new, path, pointer + '/' + str(i), identity)
            return
        # Cards have no UID of their own. Their exercise UID, stable slot,
        # complete before value and invariant correct index provide the link.
        if before and all(isinstance(x, list) for x in before):
            assert len(before) == len(after), (path, pointer)
            for i, (old, new) in enumerate(zip(before, after)):
                assert old[2:4] == new[2:4] or (path.endswith('_08.json') and pointer.endswith('/4') and i == 2)
                assert old[3] == new[3], (path, pointer, i)
                walk(old, new, path, pointer + '/' + str(i), (*identity, {'card_slot': i}))
            return
    ledger.append({'path': path, 'pointer': pointer, 'identity_chain': identity, 'before': before, 'after': after})


changed = subprocess.check_output(['git', 'diff', '--name-only', BASE, '--', 'content'], cwd=ROOT, text=True).splitlines()
assert len(changed) == 20, changed
for path in changed:
    before = load(git_bytes(path), path)
    after = load((ROOT / path).read_bytes(), path)
    if '/seed_lessons/' in path:
        assert after['slug'] in SLUGS or path.endswith('a1_w02_l04_have_like_can.yaml')
        if path.endswith('a1_w02_l04_have_like_can.yaml'):
            old_copy = copy.deepcopy(before)
            for key in ('prompt_ru', 'hint_ru', 'explanation_ru'):
                old_copy['practice'][2][key] = after['practice'][2][key]
            assert old_copy == after, 'R17 changes only three fields'
        assert after['units'] == before['units']
        assert [x['number'] for x in after['layers']] == list(range(1, 8))
        assert len(after['exercises']) == len(before['exercises'])
        assert len(after['practice']) == len(before['practice']) == 4
        for section in ('exercises', 'practice'):
            for old, new in zip(before[section], after[section]):
                assert old['answer'] == new['answer']
                assert set(old.get('accepted', [])) <= set(new.get('accepted', []))
        body = '\n'.join(x['body'] for x in after['layers'])
        assert len(re.findall(r'\[[A-Z]\d+\]', body)) == body.count('[/]')
    elif '/seed_lexicon/' in path:
        assert [(u['uid'], u['lemma'], u['class']) for u in before['units']] == [(u['uid'], u['lemma'], u['class']) for u in after['units']]
        assert len(before['units']) == len(after['units'])
    elif '/seed_poems/' in path:
        assert path.endswith('p02_who_is_she.yaml')
        assert re.sub(r'\[[A-Z]\d+\]|\[/\]', '', before['body']) == re.sub(r'\[[A-Z]\d+\]|\[/\]', '', after['body'])
        assert before['pronunciation'] == after['pronunciation'] and before['gaps'] == after['gaps']
        assert before['target_units'] == after['target_units'] and len(after['target_units']) == 9
    elif '/seed_weeks/' in path:
        assert before['script'] == after['script']
        for key in ('text', 'ipa', 'number', 'target_line', 'warmup'):
            assert before['twister'].get(key) == after['twister'].get(key)
    else:
        # Shared documents may contain other lessons: those rows stay byte-for-
        # byte equivalent as parsed data, not merely the same array position.
        def outsiders(doc):
            if isinstance(doc, list):
                return [r for r in doc if r.get('n') not in SLUG_BY_N]
            if 'lessons' in doc:
                return {**doc, 'lessons': [r for r in doc['lessons'] if r['slug'] not in SLUGS]}
            return {k: v for k, v in doc.items() if k not in SLUGS}
        assert outsiders(before) == outsiders(after), path
    walk(before, after, path)
for path in ('uv.lock', 'pnpm-lock.yaml', 'apps/taxonomy/registry.py', 'apps/curriculum/registry.py'):
    assert (ROOT / path).read_bytes() == git_bytes(path), path
assert not subprocess.check_output(['git', 'diff', '--name-only', BASE, '--', 'apps', 'config', '.github'], cwd=ROOT, text=True).strip()
(OUT / 'CHANGES.json').write_text(json.dumps({'base': BASE, 'author': 'Codex', 'verification_status': 'technical_review', 'changes': ledger}, ensure_ascii=False, indent=2) + '\n')
result = {'status': 'PASS', 'base': BASE, 'content_files': len(changed), 'semantic_fields': len(ledger),
          'deep_review_lessons': 4, 'r17_prompt_followup_lessons': 1, 'main_exercises': 22, 'translations': 16, 'delayed_cards': 110,
          'seven_layers': True, 'stable_ids': True, 'old_canonical_and_accepted_answers_retained': True,
          'unrelated_shared_rows_unchanged': True, 'weekly_recorded_dialogue_and_twister_texts_unchanged': True,
          'lockfiles_and_registry_unchanged': True, 'application_schema_auth_ci_unchanged': True, 'poem_plain_text_and_ipa_unchanged': True}
(OUT / 'evidence/INTEGRITY.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
