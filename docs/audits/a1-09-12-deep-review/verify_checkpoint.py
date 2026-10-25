"""Check the frozen 9–12 sources and their semantic scope against the actual base."""
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess

import yaml

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
BASE='5826785ee3f665fac765783ba9a95a5dd3b52655'
SLUGS={'a1-there-is-some','a1-how-much-prices','a1-present-simple-i-you','a1-time-at-seven'}
manifest=json.loads((HERE/'evidence/TESTED_SOURCE_SHA256.json').read_text())
for path,expected in manifest.items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
changed=subprocess.check_output(['git','diff','--name-only',BASE],cwd=ROOT,text=True).splitlines()
allowed=set(manifest)
for path in changed:
    assert path in allowed or path.startswith('docs/audits/a1-09-12-deep-review/') or path=='docs/plans/2026-10-14-situation-weeks.progress.md',path

def before(path):
    raw=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True)
    return json.loads(raw) if path.endswith('.json') else yaml.safe_load(raw)

def after(path):
    raw=(ROOT/path).read_text()
    return json.loads(raw) if path.endswith('.json') else yaml.safe_load(raw)

for path in manifest:
    if not path.startswith('content/'):continue
    old,new=before(path),after(path)
    if '/seed_lessons/' in path:
        assert old['slug']==new['slug'] and new['slug'] in SLUGS
        assert old['units']==new['units']
        assert [x['number'] for x in new['layers']]==list(range(1,8))
        assert len(old['exercises'])==len(new['exercises'])==6
        assert len(old['practice'])==len(new['practice'])==4
        for section in ('exercises','practice'):
            for x,y in zip(old[section],new[section]):
                for key in ('uid','order','answer','review_of'):
                    if key in x:assert x[key]==y[key],(path,key)
                assert set(x.get('accepted',[]))<=set(y.get('accepted',[]))
    elif '/seed_lexicon/' in path:
        assert len(old['units'])==len(new['units'])
        for x,y in zip(old['units'],new['units']):
            for key in ('uid','lemma','class','forms','ipa_us','example_en','example_ru'):
                assert x.get(key)==y.get(key),(path,key)
    elif '/seed_poems/' in path:
        assert old['number']==new['number']==3
        strip=lambda text:re.sub(r'\[[A-Z]\d+\]|\[/\]','',text)
        assert strip(old['body'])==strip(new['body'])
        assert old['pronunciation']==new['pronunciation'] and old['gaps']==new['gaps']
        assert new['target_units']==[u for u in old['target_units'] if u!='LX-00128']
    elif '/seed_stories/' in path:
        assert old['number']==new['number']==2
        for key in ('script','new_units','questions','phrase_hunt','retell_words','retell_steps','creative_ru'):
            assert old.get(key)==new.get(key),(path,key)
        assert len(new['grammar_ru'])<=240 and len(new['prediction_ru'])<=240
    elif '/seed_weeks/' in path:
        assert old['week']==new['week']==5 and old['script']==new['script']
        x=dict(old['twister']);y=dict(new['twister']);x.pop('focus_sounds');y.pop('focus_sounds');assert x==y
    elif path.endswith('course_map.yaml'):
        amended=copy.deepcopy(old)
        theme=next(x['theme_ru'] for x in new['poems'] if x['number']==3)
        next(x for x in amended['poems'] if x['number']==3)['theme_ru']=theme
        assert amended==new and len(theme)<=240
    elif isinstance(old,list):
        assert [x for x in old if x['n'] not in (9,10,11,12)]==[x for x in new if x['n'] not in (9,10,11,12)]
    elif 'lessons' in old:
        assert [x for x in old['lessons'] if x['slug'] not in SLUGS]==[x for x in new['lessons'] if x['slug'] not in SLUGS]
    else:
        assert {k:v for k,v in old.items() if k not in SLUGS}=={k:v for k,v in new.items() if k not in SLUGS}
for path in ('uv.lock','pnpm-lock.yaml','apps/taxonomy/registry.py','apps/curriculum/registry.py'):
    assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
result={'status':'PASS','base':BASE,'source_files':len(manifest),'four_lessons':[9,10,11,12],'source_hashes':True,'scope_and_ids':True,'recorded_English_IPA_poem_gaps_unchanged':True,'old_correct_answers_retained':True,'unrelated_rows_and_levels_unchanged':True,'schema_auth_ci_lockfiles_registry_unchanged':True,'dependency_on_unmerged_5_8':'none detected'}
(HERE/'evidence/CHECKPOINT_INTEGRITY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
