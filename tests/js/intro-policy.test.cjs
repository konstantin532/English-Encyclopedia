const {test}=require('node:test');
const assert=require('node:assert/strict');
const {claimIntro}=require('../../static/js/motion-system.js');
test('expressive entry plays once per page in a tab',()=>{
 const values=new Map(); const storage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)};
 assert.equal(claimIntro(storage,'/'),true);
 assert.equal(claimIntro(storage,'/'),false);
 assert.equal(claimIntro(storage,'/levels/a1/weeks/1/'),true);
});
test('unavailable session storage safely omits decorative entry',()=>{
 assert.equal(claimIntro(undefined,'/'),false);
 assert.equal(claimIntro({getItem(){throw Error('blocked');}},'/'),false);
});

test('blocked browser sessionStorage getter does not abort motion initialization',()=>{
 const vm=require('node:vm'); const {readFileSync}=require('node:fs'); const {resolve}=require('node:path');
 const document={readyState:'complete',documentElement:{dataset:{}},querySelector:()=>null,
 querySelectorAll:()=>[],getElementById:()=>null,addEventListener(){}};
 const window={document,localStorage:{getItem:()=> 'full'},location:{pathname:'/'},gsap:{},
 matchMedia:()=>({matches:false,addEventListener(){}}),addEventListener(){},
 get sessionStorage(){throw Error('Storage blocked');}};
 assert.doesNotThrow(()=>vm.runInNewContext(readFileSync(resolve(__dirname,'../../static/js/motion-system.js'),'utf8'),{window}));
 assert.equal(typeof window.EnglishMotion.setMode,'function');
});
