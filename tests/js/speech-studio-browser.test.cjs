const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../../static/js/speech-studio.js'), 'utf8');

class Element {
  constructor(value='') { this.textContent=value; this.dataset={}; this.hidden=false; this.disabled=false; this.listeners={}; this.attrs={}; this.childNodes=[]; this.children=[]; }
  addEventListener(type,fn) { this.listeners[type]=fn; }
  dispatch(type) { assert.equal(typeof this.listeners[type],'function'); return this.listeners[type](); }
  setAttribute(k,v) { this.attrs[k]=v; }
  removeAttribute(k) {delete this.attrs[k];}
  append(...nodes) {this.childNodes.push(...nodes);this.children.push(...nodes);}
  replaceChildren() {this.childNodes=[];this.children=[];}
  pause() {}
  load() {}
  cloneNode() {return new Element(this.textContent);}
  querySelector() {return null;}
}
function fixture(withMic=false, standalone=false, delayedMic=false, delayedStop=false) {
  const map=new Map();
  const find=(s)=>{if(!map.has(s))map.set(s,new Element());return map.get(s);};
  const modes=['see','echo','recall','transfer'].map(value=>{const x=new Element();x.dataset.speechMode=value;return x;});
  const entries=['This is my book.','This is my phone.'].map((value,i)=>{
    const source=new Element();source.childNodes=[new Element(value)];
    const accent=new Element(i?'my PHONE':'my BOOK');
    return {querySelector(selector){return selector==='[data-speech-source]'?source:selector==='[data-speech-accent]'?accent:null;}};
  });
  const root={dataset:{speechKind:'lesson'},querySelector:find,querySelectorAll(sel){
    return sel==='[data-speech-entry]'?entries:sel==='[data-speech-mode]'?modes:[];
  }};
  let clock=0;
  const events={requested:0, stopped:0, created:0, revoked:0};
  const document={readyState:'complete',querySelectorAll(selector){
    return selector==='[data-speech-studio]' ? (standalone ? [] : [root]) : selector==='[data-speech-recorder]' ? [root] : [];
  },createElement(){return new Element();}};
  const lifecycle={};
  const recorders=[], pendingStops=[];
  let allowMic;
  const permission=new Promise(resolve=>{allowMic=resolve;});
  const window={navigator:{},addEventListener(name,fn){lifecycle[name]=fn;}};
  if(withMic){
    window.navigator.mediaDevices={async getUserMedia(options){
      assert.equal(options.audio,true); assert.equal(options.video,false);
      events.requested++;
      if(delayedMic) await permission;
      return {getTracks(){return [{stop(){events.stopped++;}}];}};
    }};
    window.MediaRecorder=class {
      constructor(){this.state='inactive';this.mimeType='audio/webm';this.listeners={};recorders.push(this);}
      addEventListener(name,cb){this.listeners[name]=cb;}
      start(){this.state='recording';}
      stop(){
        this.state='inactive';
        const finish=()=>{this.listeners.dataavailable({data:{size:3}});this.listeners.stop();};
        if(delayedStop) pendingStops.push(finish); else finish();
      }
    };
  }
  const blobURL={createObjectURL(){events.created++;return 'blob:local-only';},
    revokeObjectURL(){events.revoked++;}};
  vm.runInNewContext(code,{document,window,Date:{now:()=>clock},URL:blobURL,Blob:class{},module:{exports:{}}});
  return {find,modes,events,allowMic,finishStop(){pendingStops.shift()?.();},failRecording(){const r=recorders.at(-1);r.state='inactive';r.listeners.error();r.stop();},leave(){lifecycle.pagehide?.();},clock(n){clock=n;},get current(){return find('[data-speech-current]').childNodes.map(n=>n.textContent).join('');}};
}

test('lesson voice ladder starts with a model, recall removes it from current card',()=>{
  const app=fixture();
  assert.equal(app.current,'This is my book.');
  assert.match(app.find('[data-speech-position]').textContent,/1 из 2/);
  app.modes[2].dispatch('click');
  assert.doesNotMatch(app.current,/This is my book/);
  assert.match(app.current,/памяти/);
  assert.equal(app.find('[data-speech-reveal]').hidden,false);
  app.find('[data-speech-reveal]').dispatch('click');
  assert.equal(app.current,'This is my book.');
  app.find('[data-speech-next]').dispatch('click');
  assert.doesNotMatch(app.current,/This is my phone/);
  assert.equal(app.find('[data-speech-next]').disabled,true);
});

test('transfer hides the provided line and allows a reversible personal mark',()=>{
  const app=fixture();
  app.modes[3].dispatch('click');
  assert.doesNotMatch(app.current,/book/);
  app.find('[data-speech-done]').dispatch('click');
  assert.match(app.find('[data-speech-status]').textContent,/Отмечено 1 из 2/);
  app.find('[data-speech-done]').dispatch('click');
  assert.match(app.find('[data-speech-status]').textContent,/Отмечено 0 из 2/);
  assert.equal(app.find('[data-speech-record]').disabled,true);
});

test('tap tempo is reported as tempo of taps only',()=>{
  const app=fixture();
  app.clock(0);app.find('[data-speech-tap]').dispatch('click');
  app.clock(500);app.find('[data-speech-tap]').dispatch('click');
  app.clock(1000);app.find('[data-speech-tap]').dispatch('click');
  assert.match(app.find('[data-speech-tempo]').textContent,/120 ударов/);
  assert.match(app.find('[data-speech-tempo]').textContent,/темп нажатий/);
  app.find('[data-speech-reset-beat]').dispatch('click');
  assert.equal(app.find('[data-speech-tempo]').textContent,'Ритм сброшен.');
});

test('optional microphone stays local and releases tracks after explicit deletion', async()=>{
  const app=fixture(true);
  const record=app.find('[data-speech-record]');
  const stop=app.find('[data-speech-stop]');
  const remove=app.find('[data-speech-delete]');
  assert.equal(record.disabled,false);
  await record.dispatch('click');
  assert.equal(app.events.requested,1);
  assert.equal(stop.hidden,false);
  stop.dispatch('click');
  assert.equal(app.events.stopped,1);
  assert.equal(app.events.created,1);
  assert.equal(app.find('[data-speech-playback]').src,'blob:local-only');
  assert.equal(remove.hidden,false);
  remove.dispatch('click');
  assert.equal(app.events.revoked,1);
  assert.equal(app.find('[data-speech-playback]').hidden,true);
});


test('compact week recorder works independently of speech entries and modes', async()=>{
  const app=fixture(true,true);
  assert.equal(app.events.requested,0);
  await app.find('[data-speech-record]').dispatch('click');
  assert.equal(app.events.requested,1);
  app.find('[data-speech-stop]').dispatch('click');
  assert.equal(app.events.stopped,1);
  assert.equal(app.find('[data-speech-playback]').src,'blob:local-only');
  app.leave();
  assert.equal(app.events.revoked,1);
});

test('leaving while microphone permission is pending releases the late stream', async()=>{
  const app=fixture(true,true,true);
  const pending=app.find('[data-speech-record]').dispatch('click');
  await app.find('[data-speech-record]').dispatch('click');
  assert.equal(app.events.requested,1);
  app.leave();
  app.allowMic();
  await pending;
  assert.equal(app.events.stopped,1);
  assert.equal(app.events.created,0);
});


test('recorder can be used again after returning to a preserved page', async()=>{
  const app=fixture(true,true,true);
  const pending=app.find('[data-speech-record]').dispatch('click');
  app.leave();
  app.allowMic();
  await pending;
  await app.find('[data-speech-record]').dispatch('click');
  assert.equal(app.events.requested,2);
  app.find('[data-speech-stop]').dispatch('click');
  assert.equal(app.events.stopped,2);
  assert.equal(app.events.created,1);
});


test('a late stop after recorder error does not stop a newer recording', async()=>{
  const app=fixture(true,true,false,true);
  await app.find('[data-speech-record]').dispatch('click');
  app.failRecording();
  assert.equal(app.find('[data-speech-record]').hidden,false);
  await app.find('[data-speech-record]').dispatch('click');
  app.finishStop();
  assert.equal(app.events.stopped,1);
  assert.equal(app.events.created,0);
  assert.equal(app.find('[data-speech-record]').hidden,true);
  app.find('[data-speech-stop]').dispatch('click');
  app.finishStop();
  assert.equal(app.events.stopped,2);
  assert.equal(app.events.created,1);
});
