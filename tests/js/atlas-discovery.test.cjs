const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../../static/js/atlas-language.js'), 'utf8');
function fixture({motion='balanced', reduced=false, gsap=true}={}) {
  class Element {
    constructor(text='') { this.textContent=text; this.dataset={}; this.attributes={}; this.listeners={}; this.style={}; this.hidden=false; }
    setAttribute(k,v){this.attributes[k]=v;}
    addEventListener(k,fn){this.listeners[k]=fn;}
    replaceWith(el){this.replacement=el;}
    getBoundingClientRect(){return {left:900,bottom:780,width:320,height:100};}
    focus(){this.focused=true;}
    contains(el){return el===this;}
  }
  const note=new Element('Я дома. Два слова — целая мысль.');
  const roles=['subject','be','place'].map(r=>{const el=new Element(r);el.dataset.atlasRole=r;return el;});
  const words=['I',"'m",'home'].map(t=>new Element(t));
  const card=new Element();
  card.querySelector=s=>s==='[data-atlas-explanation]'?note:words[s.includes('"T"')?0:s.includes('"D"')?1:2];
  card.querySelectorAll=()=>roles;
  card.contains=el=>el===card||words.includes(el)||roles.some(r=>r.replacement===el);
  const document=new Element();document.readyState='complete';document.documentElement=new Element();document.documentElement.dataset.motion=motion;
  document.querySelectorAll=()=>[card];document.createElement=()=>new Element();document.body={appendChild(el){document.panel=el;}};
  const calls=[];const window=new Element();Object.assign(window,{document,innerWidth:390,innerHeight:844,matchMedia:()=>({matches:reduced}),gsap:gsap?{killTweensOf(){},set(){},fromTo(...args){calls.push(args);}}:null});
  vm.runInNewContext(source,{window});
  return {card,note,words,buttons:roles.map(r=>r.replacement),panel:document.panel,document,window,calls};
}
test('word and caption discovery share state without replacing the translation',()=>{
 const f=fixture();f.buttons[0].listeners.click();assert.equal(f.panel.textContent,'I — «я»: кто говорит.');assert.equal(f.words[0].attributes['aria-expanded'],'true');
 assert.equal(f.note.textContent,'Я дома. Два слова — целая мысль.');assert.equal(f.panel.style.left,'54px');
 f.words[1].listeners.keydown({key:'Enter',preventDefault(){}});assert.match(f.panel.textContent,/am/);assert.equal(f.buttons[0].attributes['aria-expanded'],'false');assert.equal(f.buttons[1].attributes['aria-expanded'],'true');
 f.document.listeners.keydown({key:'Escape'});assert.equal(f.panel.hidden,true);assert.equal(f.words[1].focused,true);
});
test('touch toggle, outside press, focus departure and resize dismiss discovery',()=>{
 for(const dismiss of [f=>f.buttons[0].listeners.click(),f=>f.document.listeners.pointerdown({target:{}}),f=>f.document.listeners.focusin({target:{}}),f=>f.window.listeners.resize()]){
  const f=fixture();f.buttons[0].listeners.click();dismiss(f);assert.equal(f.panel.hidden,true);assert.equal(f.card.dataset.atlasFocus,undefined);
 }
});
test('pedagogical interaction works without GSAP and respects reduced motion',()=>{
 for(const options of [{motion:'balanced'},{motion:'minimal'},{motion:'full',reduced:true},{motion:'full',gsap:false}]){
  const f=fixture(options);f.words[2].listeners.keydown({key:' ',preventDefault(){}});assert.match(f.panel.textContent,/без предлога/);assert.equal(f.calls.length,0);
 }
 const f=fixture({motion:'full'});f.buttons[2].listeners.click();assert.equal(f.calls.length,1);
});

test('focus-induced mobile scroll keeps the explanation open and aligned',()=>{
 const f=fixture();f.words[0].listeners.keydown({key:'Enter',preventDefault(){}});
 f.window.listeners.scroll();assert.equal(f.panel.hidden,false);assert.equal(f.words[0].attributes['aria-expanded'],'true');
});
