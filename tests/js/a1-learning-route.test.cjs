const {test} = require('node:test');
const assert = require('node:assert/strict');
const {ROUTES, showSection, init} = require('../../static/js/a1-learning-route.js');

function fixture(bookpage = false) {
  const sections = Array.from({length:7}, (_,i)=>({id:'layer-'+(i+1),hidden:false}));
  sections.push({id:'sound-notes',hidden:false},{id:'contractions',hidden:false});
  const buttons = ['essentials','reasons','full'].map(mode=>({
    dataset:{a1RouteMode:mode}, attrs:{}, listener:null,
    setAttribute(key,value){this.attrs[key]=value;},
    addEventListener(event,fn){assert.equal(event,'click');this.listener=fn;},
    click(){this.listener();},
  }));
  const status={textContent:'Before initialization'};
  const guide={
    hidden:true,
    querySelectorAll(selector){assert.equal(selector,'[data-a1-route-mode]');return buttons;},
    querySelector(selector){assert.equal(selector,'[data-a1-route-status]');return status;},
  };
  const reader={
    querySelectorAll(selector){assert.equal(selector,'section.layer');return sections;},
  };
  const doc={
    querySelector(selector){
      return {'[data-a1-learning-route]':guide,'[data-lesson-reader]':reader,'[data-lesson-bookpage]':bookpage ? {} : null}[selector] || null;
    },
  };
  const listeners={};
  const win={location:{hash:''},addEventListener(event,fn){listeners[event]=fn;}};
  return {doc,win,guide,sections,buttons,status,listeners};
}
const hidden=f=>f.sections.filter(s=>s.hidden).map(s=>s.id);

test('routes only select original layers, not audio supplements',()=>{
  assert.deepEqual(ROUTES.essentials,[1,3,5,7]);
  assert.equal(showSection('essentials','layer-2'),false);
  assert.equal(showSection('essentials','layer-5'),true);
  assert.equal(showSection('reasons','layer-4'),true);
  assert.equal(showSection('reasons','layer-6'),false);
  assert.equal(showSection('full','layer-6'),true);
  assert.equal(showSection('unexpected','layer-6'),true);
  for(const mode of Object.keys(ROUTES)){
    assert.equal(showSection(mode,'sound-notes'),true);
    assert.equal(showSection(mode,'contractions'),true);
    assert.equal(showSection(mode,'other'),true);
  }
});
test('all original sections visible until explicit learner action',()=>{
  const f=fixture();
  assert.equal(f.guide.hidden,true); // no JavaScript = unchanged lesson
  assert.deepEqual(hidden(f),[]);
  init(f.doc,f.win);
  assert.equal(f.guide.hidden,false);
  assert.deepEqual(hidden(f),[]);
  assert.equal(f.buttons[2].attrs['aria-pressed'],'true');
  assert.match(f.status.textContent,/все семь шагов/);
});
test('short and reasons routes are reversible and always keep sound',()=>{
  const f=fixture();init(f.doc,f.win);
  f.buttons[0].click();
  assert.deepEqual(hidden(f),['layer-2','layer-4','layer-6']);
  assert.equal(f.buttons[0].attrs['aria-pressed'],'true');
  f.buttons[1].click();
  assert.deepEqual(hidden(f),['layer-6']);
  f.buttons[2].click();
  assert.deepEqual(hidden(f),[]);
});
test('a deep link into hidden text restores the complete lesson',()=>{
  const f=fixture();init(f.doc,f.win);
  f.buttons[0].click();
  assert.equal(f.sections[1].hidden,true);
  f.win.location.hash='#layer-2';
  f.listeners.hashchange();
  assert.deepEqual(hidden(f),[]);
  assert.equal(f.buttons[2].attrs['aria-pressed'],'true');
});
test('malformed pilot markup fails open with full lesson intact',()=>{
  const f=fixture();
  f.sections.pop();f.sections.pop();f.sections.pop(); // only six numbered layers
  init(f.doc,f.win);
  assert.equal(f.guide.hidden,true);
  assert.deepEqual(hidden(f),[]);
});


test('bookpage feedback names the exact visible layers without changing routes',()=>{
  const f=fixture(true);init(f.doc,f.win);
  assert.match(f.status.textContent,/7 из 7/);
  for (let repeat=0; repeat<2; repeat++) {
    f.buttons[0].click();
    assert.deepEqual(hidden(f),['layer-2','layer-4','layer-6']);
    assert.match(f.status.textContent,/4 из 7/);
    assert.match(f.status.textContent,/Скрыты шаги 2, 4, 6/);
    assert.match(f.status.textContent,/Краткая опора и практика не меняются/);
    f.buttons[1].click();
    assert.deepEqual(hidden(f),['layer-6']);
    assert.match(f.status.textContent,/6 из 7/);
    assert.match(f.status.textContent,/Скрыт шаг 6/);
    f.buttons[2].click();
    assert.deepEqual(hidden(f),[]);
    assert.match(f.status.textContent,/7 из 7/);
  }
});
test('bookpage deep link restores full explanation and matching feedback',()=>{
  const f=fixture(true);init(f.doc,f.win);f.buttons[0].click();
  f.win.location.hash='#layer-4';f.listeners.hashchange();
  assert.deepEqual(hidden(f),[]);
  assert.equal(f.buttons[2].attrs['aria-pressed'],'true');
  assert.match(f.status.textContent,/7 из 7/);
});
test('other lessons keep their existing reading feedback',()=>{
  const f=fixture();init(f.doc,f.win);
  f.buttons[0].click();
  assert.equal(f.status.textContent,'Суть: основные примеры, разговорные формы и самостоятельная практика. Остальные шаги доступны в режиме «Полностью».');
});
