"""Server-rendered HTTP checks; does not replace visual browser QA."""
import json
import django
from django.conf import settings
from django.test import Client
from django.urls import reverse

django.setup()
d = settings.DATABASES['default']
assert d['ENGINE'] == 'django.db.backends.sqlite3' and str(d['NAME']).startswith('/tmp/ee-a1-05-08-verification-')
client = Client(HTTP_HOST='localhost')
rows = []
for slug in ['a1-cafe-order', 'a1-numbers-1-20', 'a1-family-photo', 'a1-family-possession']:
    url = reverse('lessons:detail', args=[slug])
    response = client.get(url)
    assert response.status_code == 200
    assert response.content.count(b'lesson-diagnostic-answer') >= 1
    rows.append({'url': url, 'status': 200, 'diagnostic_reveal': True})
for number in [3, 4]:
    url = reverse('curriculum:week', args=['a1', number])
    response = client.get(url)
    assert response.status_code == 200
    rows.append({'url': url, 'status': 200})
url = reverse('stories:poem', args=[2])
response = client.get(url)
assert response.status_code == 200
rows.append({'url': url, 'status': 200})
print(json.dumps({'results': rows, 'visual_check': 'BLOCKED: Chromium unavailable'}, indent=2))
