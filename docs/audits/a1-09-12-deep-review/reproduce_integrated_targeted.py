import subprocess,os,tempfile,json,time
from pathlib import Path
py='/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python';db=Path(tempfile.mkdtemp(prefix='ee-a1-09-12-integrated-targeted-'))/'fixture.sqlite3';env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','LANG','LC_ALL']};env.update(DJANGO_SETTINGS_MODULE='config.settings.test',DATABASE_URL='sqlite:///'+str(db),TEST_DATABASE_URL='sqlite:///'+str(db),DJANGO_SECRET_KEY='isolated-shared-targeted',DJANGO_ALLOWED_HOSTS='localhost,testserver',DJANGO_TEST_PROCESSES='2',PYTHONUNBUFFERED='1')
cmd=[py,'manage.py','test','tests.test_a1_deep_09_12_shared','tests.test_a1_editorial_deep_09_12','tests.test_a1_translation','tests.test_a1_scaffold_variants','tests.test_a1_microsteps','tests.test_a1_independent_understanding','--noinput'];t=time.monotonic()
with open('/tmp/a1-09-12-integrated-targeted.log','w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
Path('/tmp/a1-09-12-integrated-targeted.json').write_text(json.dumps({'command':cmd,'database':str(db),'exit_code':r.returncode,'seconds':round(time.monotonic()-t,3)},indent=2)+'\n');print(r.returncode)
