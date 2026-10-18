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
function fixture() {
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
  const document={readyState:'complete',querySelectorAll(){return [root];},createElement(){return new Element();}};
  const window={navigator:{},addEventListener(){}};
  vm.runInNewContext(code,{document,window,Date:{now:()=>clock},module:{exports:{}}});
  return {find,modes,clock(n){clock=n;},get current(){return find('[data-speech-current]').childNodes.map(n=>n.textContent).join('');}};
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
