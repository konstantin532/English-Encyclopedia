const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../../static/js/audio-player.js"), "utf8"
);

class FakeElement {
  constructor(dataset={}) {
    this.dataset=dataset;this.listeners=new Map();this.attributes=new Map();
    this.value="";this.textContent="";this.paused=true;this.checked=false;
    this.classes=new Set();
    this.classList={
      add:(...names)=>names.forEach(x=>this.classes.add(x)),
      remove:(...names)=>names.forEach(x=>this.classes.delete(x)),
      toggle:(name,on)=>{
        if(on)this.classes.add(name);
        else this.classes.delete(name);
      },
      contains:(name)=>this.classes.has(name),
    };
  }
  addEventListener(name,fn) {
    if(!this.listeners.has(name))this.listeners.set(name,[]);
    this.listeners.get(name).push(fn);
  }
  emit(name,event={}) {
    for(const fn of this.listeners.get(name)||[])fn(event);
  }
  setAttribute(name,value) {this.attributes.set(name,String(value));}
  getAttribute(name) {return this.attributes.get(name)||null;}
  removeAttribute(name) {this.attributes.delete(name);}
  hasAttribute(name) {return this.attributes.has(name);}
  closest() {return null;}
  click() {this.emit("click",{target:this});}
}

function fixture() {
  const controls = new Map();
  const get = selector => {
    if(!controls.has(selector))controls.set(selector,new FakeElement());
    return controls.get(selector);
  };
  get("[data-rate]").value="100";
  get("[data-voice-vol]").value="100";
  get("[data-role-mute]").value="Tom";
  const lines=[
    new FakeElement({line:"0",speaker:"Tom"}),
    new FakeElement({line:"1",speaker:"Anna"}),
  ];
  const box = new FakeElement({slow:"slow.wav",natural:"natural.wav"});
  box.querySelector=selector=>
    ["[data-amb-vol]","[data-pause-lines]","[data-music-vol]"].includes(selector)
      ? null : get(selector);
  box.querySelectorAll=()=>[];
  box.style={setProperty(){}};
  const allAudio=[];
  class FakeAudio extends FakeElement {
    constructor(src){super();this.src=src;this.currentTime=0;this.duration=10;this.volume=1;
      allAudio.push(this);}
    play(){this.paused=false;this.emit("play");return Promise.resolve();}
    pause(){this.paused=true;this.emit("pause");}
  }
  const timings=JSON.stringify([{start:0,end:2},{start:3,end:6}]);
  const document={
    querySelector(selector){
      if(selector==="[data-story-player]")return box;
      if(selector==="[data-role-mute]")return get(selector);
      return null;
    },
    querySelectorAll(selector){return selector==="[data-line]"?lines:[];},
    getElementById(){return {textContent:timings};},
  };
  const localStorage={getItem(){return null;},setItem(){}};
  vm.runInNewContext(source,{document,Audio:FakeAudio,localStorage});
  return {lines,voice:allAudio[0],get};
}

test("audio transcript lines are real keyboard-operable accessible controls",()=>{
  const {lines,voice}=fixture();
  const first=lines[0];
  assert.equal(first.tabIndex,0);
  assert.equal(first.getAttribute("role"),"button");
  assert.equal(first.getAttribute("aria-keyshortcuts"),"Enter Space");
  voice.paused=false; // already playing; line activation must seek rather than restart.
  voice.currentTime=6;
  let prevented=false;
  first.emit("keydown",{key:" ",target:first,preventDefault(){prevented=true;}});
  assert.equal(prevented,true,"Space must not scroll the page");
  assert.equal(voice.currentTime,0);
  voice.currentTime=6;
  first.emit("keydown",{key:"Enter",target:first,preventDefault(){}});
  assert.equal(voice.currentTime,0);
  voice.currentTime=6;
  first.emit("keydown",{key:" ",target:{},preventDefault(){}});
  assert.equal(voice.currentTime,6,"a nested focus target is not a transcript shortcut");
});

test("moving between transcript lines clears stale speaker and current markers",()=>{
  const {lines,voice}=fixture();
  voice.currentTime=1;
  voice.emit("timeupdate");
  assert.equal(lines[0].getAttribute("aria-current"),"true");
  assert.equal(lines[0].classList.contains("is-speaking"),true);
  assert.equal(lines[0].classList.contains("is-your-turn"),true);
  voice.currentTime=4;
  voice.emit("timeupdate");
  assert.equal(lines[0].getAttribute("aria-current"),null);
  assert.equal(lines[0].classList.contains("is-speaking"),false);
  assert.equal(lines[0].classList.contains("is-your-turn"),false);
  assert.equal(lines[1].getAttribute("aria-current"),"true");
  voice.paused=false;
  voice.emit("ended");
  assert.equal(lines[1].getAttribute("aria-current"),null);
  assert.equal(lines[1].classList.contains("is-speaking"),false);
});
