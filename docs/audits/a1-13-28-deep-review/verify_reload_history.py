"""Run with manage.py shell; refuses non-isolated SQLite test settings."""
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from apps.drills.models import Exercise, PracticeItem
from apps.lessons.models import Lesson
from apps.lexicon.models import LexicalUnit
from apps.learning.models import ExerciseAttempt, IndependentAttempt, UnitProgress, SpeechPracticeProgress
assert settings.SETTINGS_MODULE == 'config.settings.test'
d = settings.DATABASES['default']
assert d['ENGINE'] == 'django.db.backends.sqlite3'
assert str(Path(d['NAME']).resolve()).startswith('/tmp/ee-a1-13-28-verification-')
print('GUARD', d['ENGINE'], d['NAME'])
u = get_user_model().objects.create_user(email='reload-history-fixture@example.test', password=None)
e = Exercise.objects.get(uid='EX-00113'); lesson = e.lesson
old = ExerciseAttempt.objects.create(user=u, exercise=e, answer='I like playing the guitar.', is_correct=True)
p = UnitProgress.objects.create(user=u, unit=LexicalUnit.objects.get(uid='LX-00203'), correct_count=7, contexts_used=['old:evidence'], stage=2)
i = IndependentAttempt.objects.create(user=u, lesson=lesson, skill='build', submitted='old submitted answer', prompt_snapshot='original prompt preserved', model_snapshot='original model preserved', outcome='needs_review')
s = SpeechPracticeProgress.objects.create(user=u, content_key='lesson:'+lesson.slug, fragment=1, attempts=3)
def identities():
 return {'units':list(LexicalUnit.objects.order_by('uid').values_list('uid','pk')), 'lessons':list(Lesson.objects.order_by('slug').values_list('slug','pk')), 'exercises':list(Exercise.all_objects.order_by('uid').values_list('uid','pk')), 'practice':list(PracticeItem.objects.order_by('lesson_id','order').values_list('lesson_id','order','pk'))}
def history():
 return [list(m.objects.filter(pk=x.pk).values()) for m,x in ((ExerciseAttempt,old),(UnitProgress,p),(IndependentAttempt,i),(SpeechPracticeProgress,s))]
ids=identities(); recorded=history()
for run in (1,2):
 call_command('load_content')
 assert identities()==ids, 'primary key identity changed'
 assert history()==recorded, 'history/progress changed'
 e.refresh_from_db(); assert set(e.units.values_list('uid',flat=True))=={'LX-00034'}
 print('PASS reload',run,'all primary keys and four types of historical record unchanged; future EX113 unit=like')
print('PASS', {k:len(v) for k,v in ids.items()})
