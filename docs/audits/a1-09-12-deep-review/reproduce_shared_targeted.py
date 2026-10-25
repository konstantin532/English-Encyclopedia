import subprocess,os,tempfile,json,time,hashlib
from pathlib import Path
py='/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python'
for label,cwd in [('before','/tmp/ee-a1-09-12-shared-before'),('after','/tmp/ee-a1-09-12-shared')]:
 db=Path(tempfile.mkdtemp(prefix='ee-a1-09-12-shared-'+label+'-'))/'fixture.sqlite3'
 env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','LANG','LC_ALL']}; env.update(DJANGO_SETTINGS_MODULE='config.settings.test',DATABASE_URL='sqlite:///'+str(db),TEST_DATABASE_URL='sqlite:///'+str(db),DJANGO_SECRET_KEY='isolated-shared-tests',DJANGO_ALLOWED_HOSTS='localhost,testserver',DJANGO_TEST_PROCESSES='2',PYTHONUNBUFFERED='1')
 cmd=[py,'manage.py','test','tests.test_a1_deep_09_12_shared','--noinput'];t=time.monotonic()
 with open('/tmp/a1-09-12-shared-'+label+'.log','w') as log:r=subprocess.run(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
 meta={'command':cmd,'cwd':cwd,'database':str(db),'baseline':'5826785ee3f665fac765783ba9a95a5dd3b52655','exit_code':r.returncode,'seconds':round(time.monotonic()-t,3),'test_sha256':hashlib.sha256((Path(cwd)/'tests/test_a1_deep_09_12_shared.py').read_bytes()).hexdigest()}
 Path('/tmp/a1-09-12-shared-'+label+'.json').write_text(json.dumps(meta,indent=2)+'\n');print(label,meta,flush=True)
