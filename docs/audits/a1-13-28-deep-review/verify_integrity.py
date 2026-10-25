from pathlib import Path
import subprocess,json,yaml,re,hashlib
r=Path(__file__).resolve().parents[3];b='8788aac996c5010060b47cca6f12f0480c2d492c';out=r/'docs/audits/a1-13-28-deep-review';results={}
files=subprocess.check_output(['git','diff','--name-only',b],cwd=r,text=True).splitlines()
def old(f):return subprocess.check_output(['git','show',b+':'+f],cwd=r,text=True)
def parse(f,s):return json.loads(s) if f.endswith('.json') else yaml.safe_load(s)
def strip(x):
 if isinstance(x,str):return re.sub(r'\[[^\]]*\]','',x)
 if isinstance(x,list):return [strip(v) for v in x]
 if isinstance(x,dict):return {k:strip(v) for k,v in x.items()}
 return x
# Audio scripts: compare only known recorded payloads; explanatory English may change.
for f in files:
 if f.startswith('content/seed_weeks/'):
  a=parse(f,old(f));z=parse(f,(r/f).read_text());assert [{k:strip(v) for k,v in x.items() if k in ('text','spoken','speaker','emotion','music')} for x in a.get('script',[])]==[{k:strip(v) for k,v in x.items() if k in ('text','spoken','speaker','emotion','music')} for x in z.get('script',[])],(f,'recorded_script');results[f]='recorded_script_plain_text_unchanged'
 if f.startswith('content/seed_poems/'):
  a=parse(f,old(f));z=parse(f,(r/f).read_text())
  for k in ('body','pronunciation','gaps','target_units'):assert strip(a.get(k))==strip(z.get(k)),(f,k)
  results[f]='plain_body_pronunciation_gaps_targets_unchanged'
# Content identities, including targets and contextual tags, cannot be conflated.
identities=('uid','slug','order','number','kind','stage','review_of')
changes=[]
def walk(a,z,path):
 if isinstance(a,dict) and isinstance(z,dict):
  for k in identities:
   if k in a:assert a[k]==z.get(k),(path,k)
  for k in set(a)|set(z):walk(a.get(k),z.get(k),path+'/'+k)
 elif isinstance(a,list) and isinstance(z,list):
  # Validate record lists. Answer/units arrays can intentionally grow or narrow.
  if a and isinstance(a[0],dict):
   assert len(a)==len(z),(path,'record_count')
   for i,(x,y) in enumerate(zip(a,z)):walk(x,y,path+'/'+str(i))
  elif a!=z:changes.append(dict(path=path,before=a,after=z))
 elif a!=z:changes.append(dict(path=path,before=a,after=z))
for f in files:
 if f.startswith('content/'):
  a=parse(f,old(f));z=parse(f,(r/f).read_text());walk(a,z,f)
results['record_identities']='PASS';results['changed_parsed_fields']=len(changes)
# All grading-policy code, accounts, registries, migrations and dependency versions unchanged.
assert not any(x.startswith(('apps/accounts/','apps/taxonomy/','apps/curriculum/')) or '/migrations/' in x or x.endswith('lock') or x.endswith('lock.yaml') for x in files)
assert [x for x in files if x.startswith('apps/')]==['apps/publishing/audit.py']
results['protected_scope']='PASS'
(out/'CONSOLIDATED_CHANGES.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n');(out/'INTEGRITY_EXTRA.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(results)
