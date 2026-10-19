const {test} = require("node:test");
const assert = require("node:assert/strict");
const {init} = require("../../static/js/independent-check.js");

function fixture() {
  const listeners = {};
  const button = {disabled:false, textContent:"Отправить четыре ответа и открыть разбор"};
  const status = {textContent:""};
  const form = {
    listeners:{},
    querySelector(selector) {
      return {"[data-batch-submit]":button, "[data-batch-status]":status}[selector] || null;
    },
    addEventListener(type, fn) {this.listeners[type] = fn;}
  };
  const doc = {querySelector(selector) {return selector === "[data-blind-batch]" ? form : null;}};
  const win = {addEventListener(type,fn) {listeners[type]=fn;}};
  return {doc,win,button,status,form,listeners};
}
test("submit announces pending transfer and blocks double tap", ()=>{
  const f=fixture();
  init(f.doc,f.win);
  const e={prevented:false,preventDefault(){this.prevented=true;}};
  f.form.listeners.submit(e);
  assert.equal(e.prevented,false);
  assert.equal(f.button.disabled,true);
  assert.match(f.status.textContent,/отправляются/i);
  const second={prevented:false,preventDefault(){this.prevented=true;}};
  f.form.listeners.submit(second);
  assert.equal(second.prevented,true);
});
test("restored Android browser tab unlocks the submit button", ()=>{
  const f=fixture(); init(f.doc,f.win);
  f.form.listeners.submit({preventDefault(){}});
  f.listeners.pageshow();
  assert.equal(f.button.disabled,false);
  assert.match(f.button.textContent,/Отправить четыре ответа/);
  assert.equal(f.status.textContent,"");
});
test("no-JavaScript page stays usable, incomplete markup fails open", ()=>{
  const f=fixture();
  f.form.querySelector=()=>null;
  init(f.doc,f.win);
  assert.equal(f.button.disabled,false);
  assert.equal(f.form.listeners.submit,undefined);
});

test("server-side validation error receives keyboard/TalkBack focus", ()=>{
  const f=fixture();
  let focused=0;
  const old=f.doc.querySelector;
  f.doc.querySelector=function(selector){
    if (selector === ".independent-form-error[role='alert']")
      return {focus(){focused += 1;}};
    return old(selector);
  };
  init(f.doc,f.win);
  assert.equal(focused,1);
  assert.equal(f.button.disabled,false);
});

test("offline Android submission keeps fields editable and reports recovery steps", ()=>{
  const f=fixture();
  f.win.navigator={onLine:false};
  init(f.doc,f.win);
  const event={prevented:false,preventDefault(){this.prevented=true;}};
  f.form.listeners.submit(event);
  assert.equal(event.prevented,true);
  assert.equal(f.button.disabled,false);
  assert.match(f.status.textContent,/Нет подключения/);
  f.win.navigator.onLine=true;
  f.listeners.online();
  assert.match(f.status.textContent,/восстановлено/);
});
test("connection lost during pending submission unlocks the button", ()=>{
  const f=fixture();f.win.navigator={onLine:true};
  init(f.doc,f.win);
  f.form.listeners.submit({preventDefault(){}});
  assert.equal(f.button.disabled,true);
  f.listeners.offline();
  assert.equal(f.button.disabled,false);
  assert.match(f.status.textContent,/Соединение потеряно/);
});
test("character counter handles pasted text and restored drafts", ()=>{
  const f=fixture();
  const field={name:"answer_transfer",maxLength:400,value:"Hi",listeners:{},
    addEventListener(type,cb){this.listeners[type]=cb;}};
  const counter={textContent:""};
  f.form.querySelectorAll=()=>[field];
  f.doc.getElementById=(id)=>id==="count-transfer"?counter:null;
  init(f.doc,f.win);
  assert.equal(counter.textContent,"2 / 400 символов");
  field.value="A".repeat(400);
  field.listeners.input();
  assert.equal(counter.textContent,"400 / 400 символов");
});
