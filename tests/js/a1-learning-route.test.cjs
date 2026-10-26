const {test}=require('node:test');
const assert=require('node:assert/strict');
const {init}=require('../../static/js/a1-learning-route.js');
function fixture(a1=true){
 const element=(id,hidden=true)=>({id,hidden,attrs:{'aria-hidden':'true'},style:{values:{display:'none'},removeProperty(k){delete this.values[k];}},removeAttribute(k){delete this.attrs[k];}});
 const sections=Array.from({length:7},(_,i)=>element('layer-'+(i+1)));
 sections.push(element('sound-notes'),element('contractions'));
 const answer=element('answer-1'),written=element('written-variant');
 const links=sections.slice(0,7).map(s=>({hash:'#'+s.id,attrs:{'aria-disabled':'true',tabindex:'-1'},removeAttribute(k){delete this.attrs[k];}}));
 const reader={querySelectorAll(s){assert.equal(s,'section.layer');return [...sections,answer,written];}};
 const root={querySelector(s){return s==='[data-lesson-reader]'?reader:null;},querySelectorAll(){return links;}};
 const doc={querySelector(s){return s==='[data-a1-full-lesson]'&&a1?root:null;}};
 const win={location:{hash:'#layer-6'},localStorage:{getItem(){throw Error('Reading old depth must not affect the lesson');},setItem(){throw Error('Do not change unrelated saved settings');}},addEventListener(){throw Error('Depth navigation no longer installs mode handlers');}};
 return {doc,win,sections,links,answer,written};
}
test('stale depth cannot hide any A1 layer or disable its contents link',()=>{
 const f=fixture();init(f.doc,f.win);
 assert.ok(f.sections.every(s=>!s.hidden));
 assert.ok(f.sections.every(s=>!s.style.values.display));
 assert.ok(f.sections.every(s=>!s.attrs['aria-hidden']));
 assert.ok(f.links.every(a=>!a.attrs['aria-disabled']&&!a.attrs.tabindex));
});
test('repeated initialization and old or malformed hashes keep the complete lesson',()=>{
 const f=fixture();for(const hash of ['#layer-2','#layer-6','#%E0%A4%A','#essentials','']){
  f.win.location.hash=hash;init(f.doc,f.win);assert.ok(f.sections.every(s=>!s.hidden));
 }
});
test('normalization never reveals exercise answers or independent reading variants',()=>{
 const f=fixture();init(f.doc,f.win);assert.equal(f.answer.hidden,true);assert.equal(f.written.hidden,true);
});
test('non-A1 pages are untouched',()=>{
 const f=fixture(false);init(f.doc,f.win);assert.ok(f.sections.every(s=>s.hidden));
});
