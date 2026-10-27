const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../../static/js/guest-progress.js'),'utf8');
function fixture({storage=new Map(),url='',fetcher,pathname='/'}={}){
  const status={textContent:''},events={};let reloads=0;const calls=[];
  const document={readyState:'loading',cookie:'csrftoken=before',body:{dataset:{guestProgressImportUrl:url}},
    querySelector(){return status;},querySelectorAll(){return [];},addEventListener(k,f){events[k]=f;}};
  const window={document,localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v)},
    location:{pathname,reload(){reloads++;}},fetch:async(u,o)=>{calls.push({url:u,...o});return fetcher?fetcher(u,o):{ok:true,json:async()=>({acknowledged:[],imported:0})};}};
  vm.runInNewContext(code,{window});
  return {api:window.GuestProgress,document,status,storage,events,calls,reloads:()=>reloads};
}
const item=(key='exercise:1',token='signed',complete=true)=>({key,token,complete});
test('local week-one results survive page navigation and keep a completed answer',()=>{
  const app=fixture();app.api.remember(item());app.api.remember(item('exercise:1','wrong',false));
  assert.equal(app.api.read()[0].token,'signed');
  const next=fixture({storage:app.storage});assert.equal(next.api.read()[0].token,'signed');
  next.api.remember({...item('goal:1','goal-done'),choice:'done'});
  next.api.remember({...item('goal:1','goal-not-yet',false),choice:'not_yet'});
  assert.equal(next.api.read().find(x=>x.key==='goal:1').choice,'not_yet');
});
test('failed imports keep local results for the next attempt',async()=>{
  const app=fixture({url:'/api/guest-progress/import/',fetcher:async()=>({ok:false})});
  app.api.remember(item());await app.api.importPending();assert.equal(app.api.read().length,1);
});
test('acknowledgements remove only sent tokens and preserve newer answers',async()=>{
  let finish;const response=new Promise(resolve=>{finish=resolve;});
  const app=fixture({url:'/api/guest-progress/import/',fetcher:()=>response});
  app.api.remember(item());app.document.cookie='csrftoken=rotated';
  const pending=app.api.importPending();
  app.api.remember(item('exercise:1','new-signed'));
  finish({ok:true,json:async()=>({acknowledged:['signed','not-in-this-request'],imported:1})});
  await pending;
  assert.equal(app.api.read()[0].token,'new-signed');
  assert.equal(app.calls[0].headers['X-CSRFToken'],'rotated');
  assert.equal(app.calls[0].credentials,'same-origin');
});
test('after sign-in a confirmed import refreshes the dashboard once',async()=>{
  const app=fixture({url:'/api/guest-progress/import/',pathname:'/learning/',fetcher:async()=>({ok:true,json:async()=>({acknowledged:['signed'],imported:1})})});
  app.api.remember(item());await app.events.DOMContentLoaded();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(app.api.read().length,0);assert.equal(app.reloads(),1);
  await app.api.importPending();assert.equal(app.reloads(),1);
});
test('corrupt local entries cannot crash the course and the queue is bounded',()=>{
  const app=fixture();for(let n=1;n<=80;n++)app.api.remember(item('exercise:'+n,'token-'+n));
  assert.equal(app.api.read().length,64);
  assert.equal(app.api.remember({key:'unknown',token:42}),false);
  app.storage.set('ee-guest-week-one-v1','not-json');assert.equal(app.api.read().length,0);
});

test('week-one completion works locally before registration and restores its choice',async()=>{
  const storage=new Map(),events={},report={textContent:''};
  const buttons=['done','not_yet'].map(value=>({value,disabled:true,setAttribute(){},classList:{toggle(){}}}));
  const form={action:'/api/guest-progress/weeks/1/goal/',dataset:{guestGoalKey:'goal:1'},
    querySelector(){return report;},querySelectorAll(){return buttons;},addEventListener(k,f){events[k]=f;}};
  const document={readyState:'complete',cookie:'csrftoken=token',body:{dataset:{}},
    querySelector(){return {textContent:''};},querySelectorAll(){return [form];}};
  const window={document,localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v)},
    fetch:async(url,options)=>{assert.equal(options.headers['X-CSRFToken'],'token');assert.equal(options.body,'status=done');return {ok:true,json:async()=>({status:'done',guest_receipt:{...item('goal:1','signed-goal'),choice:'done'}})};}};
  vm.runInNewContext(code,{window});
  assert.equal(buttons[0].disabled,false);
  await events.submit({preventDefault(){},submitter:buttons[0]});
  assert.match(report.textContent,/Получилось/);
  assert.equal(window.GuestProgress.read()[0].choice,'done');
  report.textContent='';vm.runInNewContext(code,{window});
  assert.match(report.textContent,/Получилось/);
});
