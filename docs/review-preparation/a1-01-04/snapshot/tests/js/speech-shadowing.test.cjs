const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const code = fs.readFileSync(path.join(__dirname, "../../static/js/speech-shadowing.js"), "utf8");
const {chooseSource} = require("../../static/js/speech-shadowing.js");

test("only actually supplied course audio is eligible, with an optional slow version", () => {
  assert.equal(chooseSource("slow", "natural.mp3", "slow.mp3"), "slow.mp3");
  assert.equal(chooseSource("natural", "natural.mp3", "slow.mp3"), "natural.mp3");
  assert.equal(chooseSource("slow", "natural.mp3", ""), "natural.mp3");
  assert.equal(chooseSource("natural", "", "slow.mp3"), "slow.mp3");
  assert.equal(chooseSource("unlisted", "natural.mp3", "slow.mp3"), "");
  assert.equal(chooseSource("slow", "", ""), "");
});

function widget(audioExists = true, verified = false) {
  class Node {
    constructor() {this.events={};this.dataset={};this.attrs={};this.disabled=false;this.textContent="";this.paused=false;this.currentTime=4;}
    addEventListener(name, cb) {this.events[name]=cb;}
    click() {return this.events.click();}
    setAttribute(name, value) {this.attrs[name]=value;}
    querySelector(selector) {
      if (selector === "[data-reference-status]") return status;
      if (selector === "[data-reference-stop]") return stop;
      if (selector === "[data-speech-reference-player]") return audioExists? player:null;
      return null;
    }
    querySelectorAll(selector) {return selector === "[data-reference-play]"? buttons:[];}
  }
  const status = new Node(), stop = new Node(), player = new Node();
  const buttons = [new Node(), new Node()];
  buttons[0].dataset.referencePlay="slow";
  buttons[1].dataset.referencePlay="natural";
  player.dataset.referenceNatural="/static/audio/twister-natural.mp3";
  player.dataset.referenceSlow="/static/audio/twister-slow.mp3";
  player.dataset.referenceVerified = verified?"true":"false";
  const alternate = new Node(); alternate.pause=function(){this.paused=true;};
  const root = new Node();
  root.querySelector=(key)=>key==="[data-speech-reference-player]"?(audioExists?player:null):null;
  root.closest=()=>({querySelector:()=>alternate});
  const doc = {readyState:"complete",hidden:false,events:{},querySelectorAll(s) {return s === "[data-speech-reference]"?[root]:[];},
    addEventListener(name,fn) {this.events[name]=fn;}};
  const win={events:{},addEventListener(name, fn){this.events[name]=fn;}};
  let instance=null;
  class Audio {
    constructor(){instance=this;this.events={};this.paused=true;this.currentTime=0;this.attrs={};}
    addEventListener(name, cb){this.events[name]=cb;}
    async play(){this.paused=false;}
    pause(){this.paused=true;}
    removeAttribute(k){delete this[k];}
    load(){}
  }
  win.Audio=Audio;
  vm.runInNewContext(code,{window:win,document:doc,module:{exports:{}}});
  return {buttons,instance:()=>instance,status,stop,alternate,doc,win};
}

test("slow listening uses existing clip and asks for an independent echo",async()=>{
  const f=widget(true,false);
  await f.buttons[0].click();
  assert.equal(f.instance().src,"/static/audio/twister-slow.mp3");
  assert.equal(f.instance().paused,false);
  assert.equal(f.alternate.paused,true);
  assert.match(f.status.textContent,/не подтверждено экспертом/);
  assert.equal(f.buttons[0].attrs["aria-pressed"],"true");
  f.instance().events.ended();
  assert.match(f.status.textContent,/ваша очередь/);
  assert.equal(f.buttons[0].attrs["aria-pressed"],"false");
  f.stop.click();
  assert.equal(f.instance().paused,true);
});

test("verified audio is explicitly distinguished and stops on hiding tab",async()=>{
  const f=widget(true,true);
  await f.buttons[1].click();
  assert.equal(f.instance().src,"/static/audio/twister-natural.mp3");
  assert.match(f.status.textContent,/проверенный образец/);
  f.doc.hidden=true;f.doc.events.visibilitychange();
  assert.equal(f.instance().paused,true);
  f.win.events.pagehide();
  assert.equal(f.instance().src,undefined);
});

test("missing course audio does not construct a fake TTS speaker",()=>{
  const f=widget(false);
  assert.equal(f.instance(),null);
  assert.doesNotMatch(code,/SpeechSynthesisUtterance|getUserMedia|fetch\s*\(/);
  assert.match(code,/preservesPitch = true/);
});
