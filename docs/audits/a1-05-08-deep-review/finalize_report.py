"""Summarize only recorded outcomes; run after all verification has completed."""
import hashlib
import json
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parent
repo=root.parents[2]
results=json.loads((root/'evidence/current-main/RESULTS.json').read_text())
full=next((r for r in results if r['name']=='pytest-full'),None)
assert full is not None and full['exit_code']==0, 'Full pytest must finish successfully first'
source=json.loads((root/'evidence/TESTED_SOURCE_SHA256.json').read_text())
assert all(hashlib.sha256((repo/f).read_bytes()).hexdigest()==sha for f,sha in source.items())
status={'author':'Codex','reviewed_by':'AI editorial and behavioral checks; human pilot not performed','verification_status':'technical_review','date':'2026-10-25','source_notes':'actual frozen sources and recorded local commands',
'base':'5826785ee3f665fac765783ba9a95a5dd3b52655','original_base':'fb79cd7a9b1a35ac55c7f5d0f1cf9dde73115f7e','tested_source_tree':'c10481196d4a4abc73ae7d7d4f1b50e27f49851e',
'deep_review_A1_lessons':[5,6,7,8],'other_changes':{'lesson4_practice3':'R17 target construction specified; no answer checker expansion'},
'R17':'resolved_by_explicit_target_construction','R16':'partial; some water in main translation remains needs_review under unchanged vocabulary contract','optional_R09_R25_R32':'not implemented',
'gates':{'Correctness':'PASS in documented editorial and behavioral scope','Regression':'PASS on final source with full pytest; Django timing caveat below','Security':'N/A: no auth, endpoint, permission or business logic changes','DataIntegrity':'PASS: IDs, bindings, old answers, history behavior','UX':'BLOCKED: no installed browser','Integration':'PASS on isolated SQLite; PostgreSQL BLOCKED locally','Evidence':'PASS: before/after frozen tests and source hashes'},
'limitations':['Django full began before final R17 wording change; final 47 targeted and full pytest use final source.','Browser desktop/390px/keyboard/reduced-motion unavailable','Actual audio not listened to','No local PostgreSQL or coverage job','No human pilot or final substantive acceptance','Known broader course audit warnings retained'],
'next_A1_group':[9,10,11,12],'next_group_status':'separate worktrees; not part of this PR','merge_deploy_performed':False}
(root/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
subprocess.run(['python',str(root/'update_checks.py')],check=True)
p=root/'CHECKS.md';s=p.read_text();s+='\n## Последние уточнения и границы результата\n\n- Django: 844 tests, OK, skipped=2; started before the three final R17 wording changes.\n- Final 47 targeted tests and full pytest ran against final source, including R17.\n- Final content reload/audit and seven HTTP200 checks: FINAL_EXTRA.json.\n- CSS17, JS124, fuzz64, mutation probes4/4; mutation probes are a smoke test, not a project-wide mutation score.\n- CEFR strict validates the existing evidence format; it does not confirm all lexical levels. Audit still reports 1004 unverified units, A1+547/550, recycling44% versus70%, and old story-length warnings.\n';s+='\nRaw artifact whitespace: `git diff --cached --check` reports spaces in SOURCE.patch context and raw logs (exit2). These artifacts are preserved exactly; the same check restricted to changed source/tests/journal passes. This is not a weakened CI check.\n'
p.write_text(s)
paths=list(source)+['docs/plans/2026-10-14-situation-weeks.progress.md']+[str(p.relative_to(repo)) for p in root.rglob('*') if p.is_file() and p.name!='FILE_HASHES.json']
(root/'FILE_HASHES.json').write_text(json.dumps({f:hashlib.sha256((repo/f).read_bytes()).hexdigest() for f in sorted(set(paths))},indent=2)+'\n')
print(json.dumps({'status':'PASS','source_files':len(source),'documented_files':len(paths)},indent=2))
