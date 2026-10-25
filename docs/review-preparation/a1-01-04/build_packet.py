#!/usr/bin/env python3
"""Build a byte-exact, pinned preparation packet; never imports Django or opens a DB.

Run from any directory: .venv/bin/python docs/review-preparation/a1-01-04/build_packet.py
Only writes within its own documentation directory. Source content is not edited.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = '8d3a41d9aa61cbf074caff602d53b22920ca3efa'

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def raw(path):
    return git('show', f'{BASE}:{path}')

def parsed(path):
    text = raw(path).decode('utf-8')
    return json.loads(text) if path.endswith('.json') else yaml.safe_load(text)

def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def walk(value, pointer=''):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from walk(v, pointer + '/' + str(k).replace('~','~0').replace('/','~1'))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, pointer + '/' + str(i))
    elif isinstance(value, str):
        yield pointer, value

paths = git('ls-tree','-r','--name-only',BASE).decode().splitlines()
pathset = set(paths)
manifest = {}
missing = []

def include(path, role):
    if path not in pathset:
        missing.append({'path':path, 'reason':'Not present in pinned Git tree; no source fabricated', 'requested_role':role})
        return None
    if path not in manifest:
        data = raw(path)
        target = OUT/'snapshot'/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        manifest[path] = {
            'source_path':path, 'snapshot_path':'snapshot/'+path,
            'source_commit':BASE, 'git_blob_sha':git('rev-parse',f'{BASE}:{path}').decode().strip(),
            'sha256':hashlib.sha256(data).hexdigest(), 'bytes':len(data),
            'lines':len(data.splitlines()), 'roles':[],
            'source_url':f'https://github.com/konstantin532/English-Encyclopedia/blob/{BASE}/{path}',
            'full_source':True, 'truncated':False,
        }
    if role not in manifest[path]['roles']:
        manifest[path]['roles'].append(role)
    return path

lessons = [(p,parsed(p)) for p in paths if p.startswith('content/seed_lessons/') and p.endswith('.yaml')]
lessons.sort(key=lambda pair:({'A1':0,'A1+':1}.get(pair[1]['level'],99),pair[1]['order']))
selected = [(p,d) for p,d in lessons if d['level']=='A1' and 1<=d['order']<=4]
assert len(selected)==4
slugs = {d['slug'] for _,d in selected}
weekly_plan = parsed('content/manifests/weeks_plan.yaml')['weeks']
course_plan = parsed('content/manifests/course_map.yaml')
lexicon = {}
for p in paths:
    if p.startswith('content/seed_lexicon/') and p.endswith('.yaml'):
        pack=parsed(p)
        for unit in pack['units']:
            assert unit['uid'] not in lexicon, unit['uid']
            lexicon[unit['uid']]={'source_path':p,'source_pointer':'/units/'+str(pack['units'].index(unit)),
                'internal_level':pack['level'],'introduction_week':pack.get('week'),'record':unit}

related_data = {}
for p in ['content/manifests/a1_retry_guidance.json','content/manifests/a1_understanding_checks.json',
          'content/manifests/a1_scaffold_transfer.json','content/active_a1/topics_01_08.json',
          'content/active_a1/scenarios_01_06.json','content/active_a1/error_repairs_01_18.json']:
    include(p,'full source of target-linked supplement (also contains other lesson records)')
    related_data[p]=parsed(p)
for n in range(1,5):
    p=f'content/manifests/a1_delayed_review_{n:02d}.json'
    related_data[p]=parsed(p)
    include(p,'five delayed questions per target exercise, matched by slug then exercise order')

weeks = {}
for n in [1,2]:
    p=f'content/seed_weeks/a1_w{n:02d}.yaml'
    include(p,'full week dialogue, translations, mission and twister')
    weeks[n]={'source_path':p,'source':parsed(p),'plan':next(x for x in weekly_plan if x['level']=='A1' and x['week']==n)}

stories=[]; poems=[]
for kind,folder,target in [('stories','seed_stories',stories),('poems','seed_poems',poems)]:
    for entry in course_plan[kind]:
        if entry['level']=='A1' and entry['week'] in [1,2]:
            matches=[p for p in paths if p.startswith('content/'+folder+'/') and p.endswith('.yaml') and parsed(p).get('number')==entry['number']]
            assert len(matches)==1,(kind,entry,matches)
            p=matches[0]; include(p,f'full {kind} source bound to A1 week {entry["week"]} by course_map.yaml number')
            target.append({'source_path':p,'plan_entry':entry,'source':parsed(p),
                           'relationship':'same scheduled week, not a direct lesson foreign key'})

for p in ['AGENTS.md','CLAUDE.md','pyproject.toml','uv.lock','package.json','pnpm-lock.yaml','pnpm-workspace.yaml','.python-version',
          '.github/workflows/ci.yml','.github/workflows/quality-evolution.yml','.github/workflows/atlas-browser.yml',
          'content/manifests/course_map.yaml','content/manifests/weeks_plan.yaml','content/manifests/characters.yaml','content/manifests/voices.yaml',
          'docs/specs/2026-10-14-foundation.md','docs/specs/2026-10-14-situation-weeks.md',
          'docs/plans/2026-10-14-situation-weeks.md','docs/plans/2026-10-14-situation-weeks.progress.md',
          'docs/reference-curriculum/EDITORIAL_POLICY.md','docs/reference-curriculum/LEVEL_MAP_A1_A1PLUS.md',
          'docs/pilots/a1-four-weeks/guide.md','docs/pilots/a1-four-weeks/assessment.yaml']:
    include(p,'reference/instruction/lockfile/authoring plan (not automatically current learning content)')

runtime_paths = '''config/urls.py
config/settings/base.py
config/settings/local.py
config/settings/test.py
apps/lessons/urls.py
apps/lessons/views.py
apps/lessons/models.py
apps/api/urls.py
apps/api/views.py
apps/api/validation.py
apps/drills/models.py
apps/drills/retry_guidance.py
apps/core/urls.py
apps/core/a1_active.py
apps/core/management/commands/load_content.py
apps/learning/urls.py
apps/learning/services.py
apps/learning/mistake_review.py
apps/learning/micro_review.py
apps/learning/understanding.py
apps/learning/independent_views.py
apps/learning/speech_practice.py
apps/learning/delayed_review_views.py
apps/learning/transfer_pilot.py
apps/learning/cafe_mission.py
apps/learning/models.py
apps/curriculum/urls.py
apps/curriculum/views.py
apps/curriculum/models.py
apps/curriculum/registry.py
apps/stories/urls.py
apps/stories/views.py
apps/stories/script.py
apps/stories/models.py
apps/poems/models.py
apps/lexicon/urls.py
apps/lexicon/views.py
apps/lexicon/models.py
apps/lexicon/phonetics.py
apps/core/templatetags/ru.py
apps/taxonomy/registry.py
apps/taxonomy/markup.py
apps/taxonomy/templatetags/markers.py
apps/publishing/audit.py
apps/publishing/audit_weeks.py
apps/publishing/management/commands/audit_course.py
templates/base.html
templates/lessons/detail.html
templates/components/drill.html
templates/components/translate_drill.html
templates/components/contractions.html
templates/components/sound_legend.html
templates/components/speech_studio_controls.html
templates/components/script_player.html
templates/components/twister_trainer.html
templates/components/a1_rubric_form.html
templates/core/a1_active_topic.html
templates/learning/independent_check.html
templates/learning/mistake_review.html
templates/learning/speech_review.html
templates/learning/transfer_pilot.html
templates/curriculum/week.html
templates/lexicon/detail.html
templates/stories/detail.html
templates/poems/detail.html
static/js/learning-player.js
static/js/a1-active.js
static/js/a1-learning-route.js
static/js/speech-studio.js
static/js/speech-review.js
static/js/independent-check.js
static/js/studio-reader.js
static/js/audio-player.js
static/js/story-player.js
scripts/audio_readiness.py
scripts/generate_story_audio.py
scripts/audit_cefr_evidence.py
tests/runner.py
tests/test_a1_editorial_week01_02.py
tests/test_a1_translation.py
tests/test_a1_mistake_review.py
tests/test_a1_retry_feedback.py
tests/test_a1_scaffold_variants.py
tests/test_a1_independent_understanding.py
tests/test_a1_transfer_retention_pilot.py
tests/test_content_and_learning.py
tests/test_adversarial_content.py
tests/test_atomic_exercise_review.py
apps/taxonomy/urls.py
apps/taxonomy/views.py
apps/taxonomy/models.py
templates/taxonomy/legend.html
templates/learning/dashboard.html
static/js/speech-shadowing.js
static/js/speech-stress.js
scripts/verify_atlas.cjs
tests/test_grammar_answer_integrity.py
tests/test_player.py
tests/test_speech_review.py
tests/test_speech_shadowing.py
tests/test_speech_studio.py
tests/test_a1_active_studio.py
tests/test_a1_active_quality.py
tests/js/a1-active.test.cjs
tests/js/a1-active-browser.test.cjs
tests/js/a1-learning-route.test.cjs
tests/js/independent-check.test.cjs
tests/js/speech-studio.test.cjs
tests/js/speech-studio-browser.test.cjs
tests/js/speech-review.test.cjs
tests/js/speech-review-browser.test.cjs
tests/js/audio-player.test.cjs
tests/js/audio-player-keyboard.test.cjs
tests/js/speech-shadowing.test.cjs
tests/js/story-player-accessibility.test.cjs'''.splitlines()
for p in runtime_paths:
    include(p,'runtime renderer, answer checking, loader, supporting code or existing regression test')

# Every lexicon pack assigned to week 1/2 is context: lesson.units is NOT a first-introduction list.
for uid,entry in lexicon.items():
    if entry['internal_level']=='A1' and entry['introduction_week'] in [1,2]:
        include(entry['source_path'],'whole dictionary packet introduced in target weeks')

records=[]
for p,d in lessons:
    target=d['slug'] in slugs
    entry={
        'level':d['level'],'week':d.get('week'),'order':d['order'],'slug':d['slug'],'title':d['title'],
        'source_path':p,'source_commit':BASE,'git_blob_sha':git('rev-parse',f'{BASE}:{p}').decode().strip(),
        'editorial_status':'NOT_REVIEWED','preparation_scope':'A1-01-04' if target else 'INVENTORY_ONLY',
        'detail':None,
    }
    if not target:
        records.append(entry);continue
    include(p,'full canonical lesson, all seven layers, exercises, practice, hints and keys')
    slug=d['slug']; n=d['order']
    topic=next(x for x in related_data['content/active_a1/topics_01_08.json'] if x['slug']==slug)
    assert topic['n']==n
    scenario=next(x for x in related_data['content/active_a1/scenarios_01_06.json'] if x['n']==n)
    repair=next(x for x in related_data['content/active_a1/error_repairs_01_18.json'] if x['n']==n)
    guide=next(x for x in related_data['content/manifests/a1_understanding_checks.json']['lessons'] if x['slug']==slug)
    scaffold=next(x for x in related_data['content/manifests/a1_scaffold_transfer.json']['lessons'] if x['slug']==slug)
    retry=related_data['content/manifests/a1_retry_guidance.json'][slug]
    delayedpath=next(p for p,v in related_data.items() if p.startswith('content/manifests/a1_delayed_review_') and slug in v)
    delayed=related_data[delayedpath][slug]
    by_order={x['order']:x for x in d['exercises']}
    cards={str(ex['order']):[
        {'source_index':i,'raw_card':card,'prompt_ru':card[0],'prompt_en':card[1],
         'options':card[2],'correct_index':card[3],'answer':card[2][card[3]],
         'explanation_ru':card[4] if len(card)>4 else None,
         'source_exercise_uid':ex['uid'],'source_exercise_order':ex['order']}
        for i,card in enumerate(delayed[str(ex['order'])])]
        for ex in d['exercises']}
    assert set(delayed)=={str(x) for x in by_order}
    practice_links=[{'practice_order':x['order'],'review_of_exercise_order':x['review_of'],
                     'review_of_exercise_uid':by_order[x['review_of']]['uid']} for x in d.get('practice',[])]
    linkage={
        'week':{'source_path':weeks[d['week']]['source_path'],'level':d['level'],'week':d['week'],'basis':'YAML level+week, load_content._week; lesson_detail selects lesson.week'},
        'stories':[{'number':s['plan_entry']['number'],'source_path':s['source_path'],'basis':s['relationship']} for s in stories if s['plan_entry']['week']==d['week']],
        'poems':[{'number':s['plan_entry']['number'],'source_path':s['source_path'],'basis':s['relationship']} for s in poems if s['plan_entry']['week']==d['week']],
        'active_topic':{'source_path':'content/active_a1/topics_01_08.json','match':{'slug':slug,'n':n},'basis':'apps.lessons.views.lesson_detail + apps.core.a1_active._load_topics'},
        'spoken_missions':{'source_path':'content/active_a1/scenarios_01_06.json','match':{'n':n},'basis':'active topics indexed by lesson.order, slug checked; content_details lesson key','count':len(scenario['missions'])},
        'error_repair':{'source_path':'content/active_a1/error_repairs_01_18.json','match':{'n':n},'basis':'_load_topics attaches repair by n'},
        'retry_guidance':{'source_path':'content/manifests/a1_retry_guidance.json','match':{'slug':slug},'basis':'retry_guidance: slug then str(exercise.order)'},
        'delayed_review':{'source_path':delayedpath,'match':{'slug':slug},'basis':'question_bank: slug then str(exercise.order), five cards per exercise','card_count':sum(len(x) for x in cards.values())},
        'understanding':{'source_path':'content/manifests/a1_understanding_checks.json','match':{'slug':slug},'basis':'understanding_bank/get_guide by slug'},
        'scaffold':{'source_path':'content/manifests/a1_scaffold_transfer.json','match':{'slug':slug},'basis':'understanding_bank merges steps and transfer_variants by slug'},
        'practice_review_links':practice_links,
        'browser_retrieval':{'source_code':'static/js/a1-active.js','selector':'retrievalLine(topic): (topic.n - 1) % topic.dialogue.length',
            'dialogue_index':(n-1)%len(topic['dialogue']),'selected_line':topic['dialogue'][(n-1)%len(topic['dialogue'])],
            'tasks':['dictation','back_translation'],'persistence':'browser only; not a PracticeItem database row','phonetic_quality':'NOT_VERIFIED'},
        'optional_transfer_pilot':{'source_path':'apps/learning/transfer_pilot.py','present':slug in {'a1-verb-be','a1-have-like-can-do'},'basis':'literal PILOTS dict keys; linked via learning/dashboard.html, separate opt-in workflow, not ordinary lesson tasks'},
    }
    body={
        'source_commit':BASE,'lesson_source_path':p,'editorial_status':'NOT_REVIEWED',
        'lesson_full':d,'week_full':weeks[d['week']],
        'scheduled_stories':[x for x in stories if x['plan_entry']['week']==d['week']],
        'scheduled_poems':[x for x in poems if x['plan_entry']['week']==d['week']],
        'active_topic_full':topic,'spoken_scenarios_full':scenario,'error_repair_full':repair,
        'retry_guidance_full':retry,'delayed_review_full':cards,
        'understanding_full':guide,'scaffold_full':scaffold,'links':linkage,
        'answer_checking':{'main':'Exercise.normalize/is_correct; API uses is_open_pilot_response for open A1 fill/transfer tasks',
            'practice':'PracticeItem.normalize/is_correct expands configured contractions; accepted in source is finite, not all English answers',
            'open_tasks':'Guide transfer/explain and spoken missions are model/self/teacher review, not an exhaustive grammar validator',
            'listen_dictation':'DB PracticeItem permits only translate. The active A1 lab separately generates one dictation and one back-translation from a selected dialogue line in browser JavaScript; see browser_retrieval below'},
        'browser_retrieval':linkage['browser_retrieval'],
        'prerequisites':{'prior_lessons_in_course_order':[x['slug'] for _,x in selected if x['order']<n],
            'status':'ORDER_ONLY_NOT_A_PEDAGOGICAL_PROOF','grammar_dependencies_from_dictionary':[],
            'reviewer_questions':['Does the learner encounter unknown grammar before it is explained?',
                                  'Are early full sentences explicitly taught as chunks rather than presumed prior knowledge?']},
    }
    refs={}
    for pointer,text in walk(body):
        for uid in re.findall(r'LX-\d{5}',text):
            refs.setdefault(uid,[]).append(pointer)
    dictionary=[]
    for uid,pointers in sorted(refs.items()):
        if uid not in lexicon:
            raise ValueError('Unresolved explicit dictionary ref '+uid)
        lu=lexicon[uid];include(lu['source_path'],'whole dictionary packet containing an explicit target reference')
        dictionary.append({'uid':uid,**lu,'referenced_at_json_pointers':pointers})
        if lu['record'].get('grammar_dependencies'):
            body['prerequisites']['grammar_dependencies_from_dictionary'].append({'uid':uid,'grammar_dependencies':lu['record']['grammar_dependencies'],'source_path':lu['source_path']})
    body['explicit_dictionary_records']=dictionary
    body['dictionary_caveat']='Explicit UID references are exact. Implicit mentions in free prose are not exhaustive semantic links. Full target-week dictionary packets are included for contextual lookup.'
    outpath=f'extracts/A1_{n:02d}.json';dump(OUT/outpath,body)
    entry['detail']={'extract_path':outpath,'links':linkage,'lesson_units':d.get('units',[]),
        'layer_count':len(d.get('layers',[])),
        'exercises':d.get('exercises',[]),'practice':d.get('practice',[]),
        'sound_notes':d.get('sound_notes',[]),'contractions':d.get('contractions',[]),
        'explicit_dictionary_uids':sorted(refs),'dictionary_source_paths':sorted({x['source_path'] for x in dictionary}),
        'prerequisites':body['prerequisites']}
    records.append(entry)

dictionary_context = [dict(uid=uid, **entry) for uid,entry in sorted(lexicon.items())
                      if entry['internal_level']=='A1' and entry['introduction_week'] in [1,2]]
dump(OUT/'extracts'/'WEEK_01_02_DICTIONARY.json',{
    'source_commit':BASE,'selection':'all lexical packets with level=A1 and week=1 or2, not only lesson.units',
    'count':len(dictionary_context),'editorial_status':'NOT_REVIEWED','records':dictionary_context,
    'caveat':'Forms in the current lexical record may include forms taught in later lessons. Assignment to a week does not prove that every form was already explained.'})

counts={level:sum(d['level']==level for _,d in lessons) for level in sorted({d['level'] for _,d in lessons})}
dump(OUT/'COURSE_MAP.json',{
    'schema_version':1,'source_commit':BASE,'prepared_group':'A1-01-04','counts_from_parsed_yaml':counts,
    'editorial_status':'NOT_REVIEWED','meaning_of_null':'Not prepared in this group, not a claim that source material is absent',
    'inventory_scope':'All 60 lesson YAML headers parsed; only A1 lessons1–4 have detailed link extracts',
    'lessons':records,
})

# Human-readable, unabridged canonical texts. Original bytes remain authoritative in snapshot/.
fulltext=['# A1 01–04: полные канонические тексты\n',f'Источник: `{BASE}`. Редакторская проверка: NOT_REVIEWED.\n',
          'Здесь нет пересказа. Полные дополнительные JSON и код находятся в snapshot/; связи и выборки — в extracts/A1_XX.json.\n']
for p in [x[0] for x in selected]+[weeks[x]['source_path'] for x in [1,2]]+[x['source_path'] for x in stories+poems]:
    info=manifest[p]
    fulltext.extend([f'## {p}\n',f'Git blob `{info["git_blob_sha"]}`; {info["bytes"]} bytes; {info["lines"]} lines.\n',
                     '```yaml\n'+raw(p).decode('utf-8')+'\n```\n'])
(OUT/'extracts'/'A1_01_04_FULL_TEXT.md').write_text('\n'.join(fulltext),encoding='utf-8')

# Verify every copy after writing. Git object hash and cryptographic byte digest both retained.
for p,info in manifest.items():
    copy=(OUT/info['snapshot_path']).read_bytes()
    assert copy==raw(p),p
    actual=hashlib.sha1(b'blob '+str(len(copy)).encode()+b'\0'+copy).hexdigest()
    assert actual==info['git_blob_sha'],p

# Check the three YAML blocks actually handed over in the old partial document.
# Restore the single trailing LF omitted by the Markdown fence delimiter only.
historical_text=(OUT/'inputs'/'English_Encyclopedia_A1_01_02_PARTIAL_PACKET.md').read_text(encoding='utf-8')
comparison=[]
for m in re.finditer(r'^## (content/[^\n]+)\n(.*?)```yaml\n(.*?)\n```',historical_text,re.M|re.S):
    path,header,text=m.groups(); embedded=text.encode('utf-8'); original=raw(path)
    claimed=re.search(r'Git blob: `([^`]+)`',header).group(1)
    actual=git('rev-parse',f'{BASE}:{path}').decode().strip()
    comparison.append({'path':path,'claimed_blob_sha':claimed,'actual_blob_sha':actual,
        'claimed_sha_matches':claimed==actual,'embedded_exact_bytes':embedded==original,
        'embedded_matches_after_one_final_lf':embedded+b'\n'==original,'source_bytes':len(original)})
assert len(comparison)==3
assert all(row['claimed_sha_matches'] and (row['embedded_exact_bytes'] or row['embedded_matches_after_one_final_lf']) for row in comparison)
dump(OUT/'extracts'/'HISTORICAL_SOURCE_COMPARISON.json',comparison)

inputs=[]
for p in sorted((OUT/'inputs').glob('*.md')):
    b=p.read_bytes()
    inputs.append({'path':str(p.relative_to(OUT)),'bytes_local':len(b),'sha256':hashlib.sha256(b).hexdigest(),
                   'role':'Received historical input, not a fresh verification log'})
dump(OUT/'SOURCE_MANIFEST.json',{
    'schema_version':1,'source_commit':BASE,'source_tree':git('rev-parse',BASE+'^{tree}').decode().strip(),
    'snapshot_file_count':len(manifest),'snapshot_total_bytes':sum(x['bytes'] for x in manifest.values()),
    'byte_verification':'All snapshot files compared to git show; all Git blob hashes verified',
    'files':list(sorted(manifest.values(),key=lambda x:x['source_path'])),
    'historical_input_files':inputs,
    'not_found_requested_paths':missing,
    'audio_boundary':{'production':'NOT_ACCESSED','tracked_audio_files':[p for p in paths if p.startswith('static/audio/')],
        'expected_target_manifests':['static/audio/weeks/a1-w01/manifest.json','static/audio/weeks/a1-w02/manifest.json',
                                     'static/audio/stories/s01/manifest.json','static/audio/twisters/t001/manifest.json','static/audio/twisters/t002/manifest.json'],
        'caveat':'Git absence is not proof of absence on the separately deployed site; fresh audio diagnostic is recorded by root in evidence/'},
})
lines=['# SOURCE_LINKS — реальные связи пакета A1 1–4',f'\nИсточник: `{BASE}`. Это подготовка, не лингвистическая приёмка.\n',
       '## Как проверены связи\n',
       '- Канонический урок: YAML `slug`, `level`, `week`, `order`; загрузка в `apps/core/management/commands/load_content.py`.',
       '- Упражнения: постоянный `uid`; повторные карточки и retry guidance используют `slug` + номер упражнения. `practice.review_of` — номер упражнения того же урока, не UID и не order перевода.',
       '- Дополнительная практика: `lesson_detail` берёт `active_topics()[lesson.order]`, затем проверяет совпадение slug. Сценарии и исправления присоединяются по `n` в `_load_topics`.',
       '- Guide/scaffold: записи выбираются по slug; `understanding_bank()` объединяет три шага и два дополнительных transfer варианта.',
       '- История и стих: реальные строки `course_map.yaml` связывают номер1 с A1 неделей2; отдельного FK «урок → история/стих» нет. На неделе1 их не выдумываем.',
       '- Устные миссии: шесть на урок из scenarios; недельная mission_ru и собственная фраза скороговорки — отдельные задания. Не подменять self-rating автоматической проверкой речи.',
       '- Опциональный transfer pilot есть для уроков 2 и 4 в `PILOTS`, не для всех четырёх; ссылка находится в `templates/learning/dashboard.html`, это отдельный сбор свидетельств.',
       '- Словарные `units` урока — явные связи, а не доказанный набор впервые изучаемых слов. Все пакеты словаря недель1–2 включены целиком; явные LX-ссылки разрешены до полной записи.',
       '- Неявные слова в свободном тексте не получают автоматически доказанную семантическую связь. Проверку понимания и последовательности должен выполнить рецензент.',
       '- `extracts/WEEK_01_02_DICTIONARY.json` содержит все полные записи словаря недель1–2. Поле forms отражает текущую запись и может содержать формы, объясняемые позднее; это не доказательство раннего введения всех форм.',
       '\n## Контроль полноты\n',
       f'- Инвентарь: {counts}. Подробные выборки: ровно 4 урока.',
       f'- Полные источники: {len(manifest)} файлов, {sum(x["bytes"] for x in manifest.values())} байт. SHA и размеры: SOURCE_MANIFEST.json.',
       '- YAML в snapshot/ побайтно совпадают с pinned Git blob. JSON-выборки — удобное представление, оригинал хранится отдельно без обрезки.',
       '- `extracts/A1_01_04_FULL_TEXT.md`: четыре полных урока, две недели, история 1, стих 1. `extracts/A1_01.json` … `A1_04.json`: все связанные задания и ключи целиком.',
       '\n## Реестр уроков\n',
       '| Урок | slug | упражнений | переводов | delayed cards | словарь, явные UID |',
       '|---|---|---:|---:|---:|---:|']
for e in records:
    if e['detail']:
        x=e['detail'];lines.append(f'| {e["order"]} | {e["slug"]} | {len(x["exercises"])} | {len(x["practice"])} | {x["links"]["delayed_review"]["card_count"]} | {len(x["explicit_dictionary_uids"])} |')
lines.extend(['\n## Ограничения\n','- Грамматические предпосылки в COURSE_MAP помечены ORDER_ONLY_NOT_A_PEDAGOGICAL_PROOF; порядок уроков не доказывает доступность каждого примера.',
              '- Разработческий snapshot не содержит данных учеников, рабочей БД или секретов. Приложение и учебные исходники не изменены.',
              '- Свежие runtime проверки и доступность аудио: отдельные журналы evidence/; не выводить PASS из наличия исходников.'])
(OUT/'SOURCE_LINKS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
validation_rows=[]
for record in records:
    if record['detail'] is None:
        continue
    detail=record['detail']
    extract=json.loads((OUT/detail['extract_path']).read_text(encoding='utf-8'))
    source=parsed(record['source_path'])
    assert extract['lesson_full']==source
    assert detail['exercises']==source['exercises'] and detail['practice']==source['practice']
    assert all(len(cards)==5 for cards in extract['delayed_review_full'].values())
    validation_rows.append({'order':record['order'],'slug':record['slug'],'all_source_fields_retained':True,
        'exercises':len(source['exercises']),'translations':len(source['practice']),
        'delayed_cards':sum(len(cards) for cards in extract['delayed_review_full'].values()),
        'spoken_missions':len(extract['spoken_scenarios_full']['missions']),
        'explicit_uid_references_resolved':len(extract['explicit_dictionary_records'])})
assert len(validation_rows)==4 and not missing
dump(OUT/'extracts'/'PACKET_VALIDATION.json',{
    'source_commit':BASE,'status':'PASS',
    'validation_scope':'Packet byte/hash integrity and exact data retention; NOT linguistic or pedagogical verification',
    'full_snapshots_verified':len(manifest),'snapshot_total_bytes':sum(x['bytes'] for x in manifest.values()),
    'inventory_lesson_count':len(records),'inventory_counts':counts,'prepared_lesson_count':len(validation_rows),
    'dictionary_context_records':len(dictionary_context),'unresolved_explicit_uid_refs':[],
    'missing_requested_source_paths':missing,'lessons':validation_rows,
})
print(json.dumps({'base':BASE,'lesson_counts':counts,'prepared_lessons':len(selected),'snapshot_files':len(manifest),
                  'snapshot_bytes':sum(x['bytes'] for x in manifest.values()),'not_found':missing},ensure_ascii=False,indent=2))
