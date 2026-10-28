const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
const code=fs.readFileSync(path.join(root,'static/js/annotations.js'),'utf8');
const base=fs.readFileSync(path.join(root,'templates/base.html'),'utf8');
const bootstrap=[...base.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m=>m[1]).find(s=>s.includes('ee-markers'));
function fixture({stored={},auth=false,mode='off',color='color',request}={}) {
  const storage=new Map(Object.entries(stored));
  const listeners={};
  const toggle={dataset:auth?{saveUrl:'/learning/markers/'}:{},attrs:{},disabled:false,
    setAttribute(k,v){this.attrs[k]=v;},addEventListener(k,f){listeners[k]=f;}};
  const status={textContent:''};
  const tip={style:{},attrs:{},offsetWidth:100,offsetHeight:30,
    setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];}};
  const marker=demo=>({dataset:{label:'Подсказка'},attrs:{},
    closest(selector){if(selector==='.mk[data-label]') return this;return demo&&selector.includes('[data-language-atlas]')?{}:null;},
    removeAttribute(k){delete this.attrs[k];},getBoundingClientRect(){return {left:100,top:100,width:50};}});
  const words=[marker(false),marker(true)];
  const docEvents={};
  const document={documentElement:{dataset:{markers:mode,markersColor:color}},cookie:'csrftoken=abc',
    querySelector(s){return s==='[data-markers-toggle]'?toggle:s==='[data-markers-status]'?status:null;},
    querySelectorAll(){return words;},createElement(){return tip;},body:{appendChild(){}},
    addEventListener(k,f){docEvents[k]=f;}};
  const window={innerWidth:1000,scrollX:0,scrollY:0,addEventListener(){}};
  const calls=[];
  const sandbox={document,window,localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v)},
    fetch:async(url,options)=>{calls.push({url,options});return request?request(url,options):{ok:true,json:async()=>({enabled:options.body==='enabled=true'})};}};
  if(!auth) vm.runInNewContext(bootstrap,sandbox);
  vm.runInNewContext(code,sandbox);
  return {document,toggle,status,tip,words,docEvents,storage,calls,click:()=>listeners.click()};
}
test('a new guest sees plain text immediately and can save an explicit choice',async()=>{
  const app=fixture();
  assert.equal(app.document.documentElement.dataset.markers,'off');
  assert.equal(app.toggle.attrs['aria-pressed'],'false');
  await app.click();
  assert.equal(app.document.documentElement.dataset.markers,'color');
  assert.equal(app.storage.get('ee-markers-enabled'),'true');
  await app.click();
  assert.equal(app.storage.get('ee-markers-enabled'),'false');
});
test('existing guest color and monochrome choices survive the upgrade',()=>{
  for(const color of ['color','mono']) {
    assert.equal(fixture({stored:{'ee-markers':color}}).document.documentElement.dataset.markers,color);
    assert.equal(fixture({stored:{'ee-markers':color,'ee-markers-enabled':'false'}}).document.documentElement.dataset.markers,'off');
  }
});
test('account visibility is independent of the preserved monochrome preference',async()=>{
  const app=fixture({auth:true,mode:'mono',color:'mono'});
  await app.click(); await app.click();
  assert.equal(app.document.documentElement.dataset.markers,'mono');
  assert.equal(app.calls[0].options.body,'enabled=false');
  assert.equal(app.calls[1].options.body,'enabled=true');
  assert.equal(app.calls[0].options.headers['X-CSRFToken'],'abc');
  assert.equal(app.calls[0].options.credentials,'same-origin');
});
test('failed account saves restore the previous visible state',async()=>{
  const app=fixture({auth:true,request:async()=>({ok:false})});
  await app.click();
  assert.equal(app.document.documentElement.dataset.markers,'off');
  assert.equal(app.toggle.disabled,false);
  assert.match(app.status.textContent,/Не удалось сохранить/);
});
test('a second click while saving cannot race the first request',async()=>{
  let finish;
  const response=new Promise(resolve=>{finish=resolve;});
  const app=fixture({auth:true,request:()=>response});
  const first=app.click(); await app.click();
  assert.equal(app.calls.length,1);
  finish({ok:true,json:async()=>({enabled:true})}); await first;
  assert.equal(app.toggle.disabled,false);
});
test('disabled markers keep the homepage example discoverable without extra word stops',()=>{
  const app=fixture();
  assert.equal(app.words[0].tabIndex,undefined);
  app.docEvents.pointerover({target:app.words[0]});
  assert.equal(app.tip.attrs['data-show'],undefined);
  app.docEvents.pointerover({target:app.words[1]});
  assert.equal(app.tip.textContent,'Подсказка');
  assert.equal(app.tip.attrs['data-show'],'');
});
