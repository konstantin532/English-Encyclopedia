const test=require('node:test');
const assert=require('node:assert/strict');
const {stateForAudience}=require('../../scripts/browser_auth.cjs');

test('visual review uses the requested role in its own before/after database',()=>{
  const states={before:{id:'student-before'},after:{id:'student-after'},
    beforePending:{id:'pending-before'},afterPending:{id:'pending-after'},
    beforeTeacher:{id:'teacher-before'},afterTeacher:{id:'teacher-after'}};
  for(const side of ['before','after']){
    assert.equal(stateForAudience(states,'student',side),states[side]);
    assert.equal(stateForAudience(states,'pending',side),states[side+'Pending']);
    assert.equal(stateForAudience(states,'teacher',side),states[side+'Teacher']);
    assert.equal(stateForAudience(states,'guest',side),undefined);
  }
  assert.throws(()=>stateForAudience(states,'owner','before'));
  assert.throws(()=>stateForAudience(states,'student','unknown'));
  assert.throws(()=>stateForAudience({before:{}},'pending','before'));
});
