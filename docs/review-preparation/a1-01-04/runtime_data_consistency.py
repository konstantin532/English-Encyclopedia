"""Check extracted supplemental records against the actual compiled runtime banks.

Read-only; requires the same explicitly marked isolated SQLite as runtime_smoke.
This verifies source selection/merging, not the correctness of English grammar.
"""
import argparse
import json
import os
from pathlib import Path
import sys

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser()
parser.add_argument('--database', required=True, type=Path)
args = parser.parse_args()
db = args.database.resolve(strict=True)
sha = '8d3a41d9aa61cbf074caff602d53b22920ca3efa'
assert db.parent.name.startswith('ee-preparation-test-')
assert (db.parent/'REVIEW_DATABASE_ONLY').read_text().strip() == sha
assert os.environ.get('DJANGO_SETTINGS_MODULE') == 'config.settings.test'
import django
django.setup()
from django.conf import settings
assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'
assert Path(settings.DATABASES['default']['NAME']).resolve() == db
from apps.learning.mistake_review import question_bank
from apps.learning.understanding import get_guide
from apps.core.a1_active import active_topics
from apps.lessons.models import Lesson

bank = question_bank()
topics = active_topics()
rows = []
for number in range(1,5):
    d = json.loads((P/f'extracts/A1_{number:02d}.json').read_text())
    slug = d['lesson_full']['slug']
    expected_cards = {key:[row['raw_card'] for row in cards] for key,cards in d['delayed_review_full'].items()}
    assert expected_cards == bank[slug], ('compiled delayed review mismatch',slug)
    guide = {**d['understanding_full'], 'steps':d['scaffold_full']['steps'],
             'transfer_variants':d['scaffold_full']['transfer_variants']}
    assert guide == get_guide(slug), ('compiled understanding guide mismatch',slug)
    topic = {**d['active_topic_full'],
             'missions':d['spoken_scenarios_full']['missions'],
             'twists':d['spoken_scenarios_full']['twists'],
             'repair':{key:d['error_repair_full'].get(key,[]) for key in ['wrong','correct','hint','reason','alternatives']}}
    assert topic == topics[number], ('compiled active topic mismatch',slug)
    lesson = Lesson.objects.get(slug=slug,level__code='A1')
    for source in d['lesson_full']['exercises']:
        loaded = lesson.exercises.get(uid=source['uid'])
        for key in ['answer','accepted','hint_ru','explanation_ru']:
            assert getattr(loaded,key) == source.get(key,[] if key=='accepted' else ''),(slug,source['uid'],key)
    for source in d['lesson_full']['practice']:
        loaded = lesson.practice_items.get(order=source['order'])
        for key in ['answer','accepted','hint_ru','explanation_ru','review_of']:
            assert getattr(loaded,key) == source.get(key,[] if key=='accepted' else ''),(slug,source['order'],key)
    rows.append({'slug':slug,'compiled_cards':sum(map(len,expected_cards.values())),
                 'guide_exact_match':True,'active_topic_exact_match':True,
                 'loaded_exercise_keys_hints_explanations_match':True,
                 'loaded_translation_keys_hints_explanations_match':True})
print(json.dumps({'source_commit':sha,'status':'PASS','scope':'Runtime source selection and compiled data equality; NOT language verification',
                  'database_mode':'read-only isolated fixture','lessons':rows},ensure_ascii=False,indent=2))
