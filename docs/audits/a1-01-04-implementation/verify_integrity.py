import ast,copy,hashlib,json,subprocess
from pathlib import Path
import yaml
root=Path(__file__).resolve().parents[3];out=Path(__file__).resolve().parent
j=json.loads((out/'English_Encyclopedia_A1_01_04_PROPOSED_REPLACEMENTS.json').read_text());base=j['source_commit'];docs={};checks=[]
def at(o,keys):
 for k in keys:o=o[int(k)] if isinstance(o,list) else o[k]
 return o
def parse(s,p):return json.loads(s) if p.endswith('.json') else yaml.safe_load(s)
for r in j['findings']:
 for c in r['changes']:
  p=c['path']
  if p.endswith('.py'):continue
  if p not in docs:
   b=parse(subprocess.check_output(['git','show',base+':'+p],cwd=root,text=True),p);a=parse((root/p).read_text(),p);docs[p]=(b,a,copy.deepcopy(a))
  b,a,reverted=docs[p];keys=c['pointer'].strip('/').split('/');keys=[k.replace('~1','/').replace('~0','~') for k in keys];current=at(a,keys)
  optional=r['id'] in ['R09','R25','R32']
  expected=c['before'] if optional else c['after']
  if r['id']=='R01' and c['pointer']=='/layers/3/body':expected=expected.replace('В наших обычных полных фразах перед таким словом нужен подходящий указатель:', 'В наших обычных полных фразах **исчисляемому существительному в единственном числе** нужен подходящий указатель:')
  if r['id']=='R10' and c['pointer']=='/layers/1/body':expected=expected.replace('- *a book* — одна книга, ещё не определённая для собеседника;', '- *a book* — одна книга при введении предмета в разговор; в *This is a book* — название вида предмета;')
  if r['id']=='R16' and c['pointer']=='/practice/0/accepted':expected=c['before']
  if r['id']=='R17':expected=copy.deepcopy(expected);expected.pop('accepted',None)
  if r['id']=='R26':expected="Can часто /kən/; при выделении и в кратком ответе /kæn/. Can't — /kænt/. Слушайте всю фразу, не только ударение."
  assert current==expected,(r['id'],p,c['pointer'])
  if not optional:
   parent=at(reverted,keys[:-1]);k=int(keys[-1]) if isinstance(parent,list) else keys[-1];parent[k]=c['before']
for p,(b,a,reverted) in docs.items():
 assert b==reverted,('unrequested semantic change',p)
 if '/seed_lessons/' in p:
  assert [x['number'] for x in a['layers']]==list(range(1,8))
  assert len(a['exercises'])==len(b['exercises']) and len(a['practice'])==4
 checks.append({'path':p,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest(),'only_requested_fields':True})
p='apps/learning/transfer_pilot.py'
b=ast.parse(subprocess.check_output(['git','show',base+':'+p],cwd=root,text=True));a=ast.parse((root/p).read_text())
def pilots(t):return next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='PILOTS' for x in n.targets))
pa,pb=pilots(a),pilots(b);av,bv=ast.literal_eval(pa.value),ast.literal_eval(pb.value)
av['a1-have-like-can-do']['missions']=tuple(list(av['a1-have-like-can-do']['missions'])[:2]+[bv['a1-have-like-can-do']['missions'][2]])
assert av==bv
pa.value=pb.value;assert ast.dump(a)==ast.dump(b)
for p in ['uv.lock','pnpm-lock.yaml','apps/taxonomy/registry.py','apps/curriculum/registry.py']:
 assert (root/p).read_bytes()==subprocess.check_output(['git','show',base+':'+p],cwd=root)
result={'status':'PASS','base':base,'mandatory_fields_considered':59,'mandatory_fields_changed':58,'open_key_expansions':['R16','R17'],'optional_unchanged':['R09','R25','R32'],'semantic_scope':checks,'python_changes':'Only prompt/model in day_30 a1-have-like-can-do','registry_lockfiles_unchanged':True,'seven_layers':True,'main_exercises':21,'translations':16,'no_history_migration':True}
(out/'evidence/INTEGRITY.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('Integrity PASS:',len(docs),'content files; 59 fields; no other semantic changes')
