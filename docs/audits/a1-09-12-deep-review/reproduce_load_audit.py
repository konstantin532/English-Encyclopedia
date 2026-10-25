import os,subprocess,tempfile,json,time
from pathlib import Path
py='/workspace/scratch/6babac9ddb0c/English-Encyclopedia/.venv/bin/python'; db=Path(tempfile.mkdtemp(prefix='ee-a1-09-12-shared-load-audit-'))/'fixture.sqlite3';env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','LANG','LC_ALL']};env.update(DJANGO_SETTINGS_MODULE='config.settings.test',DATABASE_URL='sqlite:///'+str(db),TEST_DATABASE_URL='sqlite:///'+str(db),DJANGO_SECRET_KEY='isolated-shared-audit',DJANGO_ALLOWED_HOSTS='localhost,testserver')
manage=[py,'manage.py'];cmds=[('guard',manage+['shell','-c',"from django.conf import settings;d=settings.DATABASES['default'];assert d['ENGINE']=='django.db.backends.sqlite3' and d['NAME']=="+repr(str(db))+";print(d['ENGINE'],d['NAME'])"]),('migrate',manage+['migrate','--noinput','-v0']),('load-content',manage+['load_content']),('audit-course',manage+['audit_course'])];rows=[]
for name,cmd in cmds:
 t=time.monotonic()
 with open('/tmp/a1-09-12-shared-'+name+'.log','w') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 rows.append({'name':name,'command':cmd,'exit_code':r.returncode,'seconds':round(time.monotonic()-t,3)})
 if r.returncode:break
Path('/tmp/a1-09-12-shared-load-audit.json').write_text(json.dumps({'database':str(db),'commands':rows},indent=2)+'\n');print(rows)
