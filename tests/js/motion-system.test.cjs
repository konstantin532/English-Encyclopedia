const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const vm = require("node:vm");

const runtime = require("../../static/js/motion-system.js");

test("motion policy defaults to balanced and never overrides system reduced motion", () => {
  assert.equal(runtime.effectiveMode(null, false), "balanced");
  assert.equal(runtime.effectiveMode("bad-value", false), "balanced");
  assert.equal(runtime.effectiveMode("full", false), "full");
  assert.equal(runtime.effectiveMode("full", true), "minimal");
  assert.equal(runtime.effectiveMode("balanced", true), "minimal");
  assert.equal(runtime.shouldAnimate("minimal", "micro"), false);
  assert.equal(runtime.shouldAnimate("balanced", "signature"), false);
  assert.equal(runtime.shouldAnimate("balanced", "component"), true);
  assert.equal(runtime.shouldAnimate("full", "signature"), true);
});

function fixture(reduced, stored) {
  const options = ["full", "balanced", "minimal"].map(value => ({value, disabled:false}));
  function select() { return {value:"balanced", disabled:true, options:options.map(o=>({...o})), listeners:{},
    addEventListener(name,fn){this.listeners[name]=fn;},
    setAttribute(name,value){this[name]=value;} }; }
  const controls = [select(),select()];
  const hint = {textContent:""};
  const listeners = {};
  const mediaListeners = {};
  const storage = {value:stored, getItem(){return this.value;},setItem(key,value){this.value=value;}};
  const media = {matches:reduced,addEventListener(type,fn){mediaListeners[type]=fn;}};
  const document = {
    readyState:"complete", hidden:false, documentElement:{dataset:{}},
    querySelector(){return null;},
    querySelectorAll(selector){if(selector==="[data-motion-control]")return controls;return [];},
    getElementById(id){return id==="motion-mode-hint"?hint:null;},
    addEventListener(type,fn){listeners[type]=fn;},
  };
  const window = {document,matchMedia:()=>media,localStorage:storage,
    addEventListener(type,fn){listeners[type]=fn;}};
  const source = readFileSync(resolve(__dirname,"../../static/js/motion-system.js"),"utf8");
  vm.runInNewContext(source,{window, document, module:{exports:{}},Math,Number,Object,Array,Set,Map});
  return {window,document,storage,controls,hint,media,mediaListeners,listeners};
}

test("two responsive controls synchronize and store only explicit changes", () => {
  const f = fixture(false,"full");
  assert.equal(f.window.EnglishMotion.mode,"full");
  assert.equal(f.controls[0].value,"full");
  assert.equal(f.controls[1].value,"full");
  assert.equal(f.document.documentElement.dataset.motion,"full");
  f.controls[1].value="balanced";
  f.controls[1].listeners.change();
  assert.equal(f.storage.value,"balanced");
  assert.equal(f.controls[0].value,"balanced");
  assert.equal(f.hint.textContent.includes("Короткие"),true);
});

test("OS reduced motion enforces Minimal and never restores Full automatically", () => {
  const f = fixture(true,"full");
  assert.equal(f.window.EnglishMotion.mode,"minimal");
  assert.equal(f.storage.value,"minimal");
  assert.equal(f.controls[0].options[0].disabled,true);
  assert.equal(f.controls[0].options[1].disabled,true);
  assert.equal(f.controls[0].options[2].disabled,false);
  f.media.matches=false;
  f.mediaListeners.change();
  assert.equal(f.window.EnglishMotion.mode,"minimal");
  f.controls[0].value="full";
  f.controls[0].listeners.change();
  assert.equal(f.window.EnglishMotion.mode,"full");
});

test("motion layer doesn't hide content or require GSAP", () => {
  const f = fixture(false,null);
  assert.equal(f.window.EnglishMotion.mode,"balanced");
  assert.equal(f.document.documentElement.dataset.motion,"balanced");
  f.window.EnglishMotion.setMode("minimal");
  assert.equal(f.document.documentElement.dataset.motion,"minimal");
  assert.doesNotThrow(() => f.window.EnglishMotion.resolve({hidden:false,style:{}},"ok"));
  assert.equal(f.listeners.pagehide instanceof Function,true);
});
